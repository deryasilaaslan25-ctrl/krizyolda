"""
Uçtan uca analiz (Rapor Bölüm 3 ve 3.9).

Adımlar:
  1) Zaman 1 saatlik pencerelere bölünür [MARCUS2011]; yalnız tamamlanmış
     pencereler analiz edilir (Tasarım kararı 26). Analiz dönemi varsayılan
     30 gün (Tasarım kararı 9).
  2) Önceki itibar: kullanıcı belirtmediyse ısınma penceresindeki haberlerin
     Janis-Fadner katsayısı negatifse "olumsuz" [DEEPHOUSE2000; COOMBS2007].
  3) SCCT yoğunlaştırıcıları uygulanır (mağdur→kaza, kaza→önlenebilir) [COOMBS2007].
  4) Her pencerede G1–G13, Q1 (indicators/compute.py).
  5) Her gösterge için TwitInfo akış z-skoru (detection/twitinfo.py).
  6) Kırpma, eşit ağırlık, KRE, ağırlıklı Stouffer Z (detection/composite.py).
  7) WECO seviyeleri, ısınma = 28 pencere (detection/western_electric.py).
  8) SCCT itibar tehdidi: baskın küme ve Hafif/Orta/Şiddetli [COOMBS2007].
  9) Stouffer kalibrasyon tanısı ve ham birim eşikleri (detection/kurum_esik.py) — açıklayıcı.
 10) KARAR (v5.1): risk puanı R = 100·min(max(Z,0),6)/6 üzerinde kuruma özgü eşik metodolojisi
     (detection/esik_kalibrasyonu.py, services/kurum_esik_servisi.py). WECO seviyeleri açıklayıcı sinyaldir.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Optional, Sequence

from app.collectors.base import KAYNAK_TURU
from app.detection import composite, esik_kalibrasyonu as E, kurum_esik, twitinfo, western_electric
from app.indicators.compute import Baglam, IslenmisIcerik, janis_fadner, pencere_olc
from app.literatur import (ANALIZ_GUN, BIN_SAAT, BOYUTLAR, ISINMA_PENCERE,
                           SEVIYE_ETIKETLERI, secilen_gostergeler)
from app.nlp.scct import KUME_SEVIYE, KUME_TEHDIT, SEVIYE_KUME

SECILEN_KODLAR = [g["kod"] for g in secilen_gostergeler()]


def saate_yuvarla(t: datetime, bin_saat: int = BIN_SAAT) -> datetime:
    t = t.replace(minute=0, second=0, microsecond=0)
    return t - timedelta(hours=t.hour % bin_saat)


def yogunlastir(baslangic: int, tip: Optional[str], kriz_gecmisi: Iterable[str], onceki_olumsuz: bool) -> int:
    """[COOMBS2007] Yoğunlaştırıcı varsa mağdur(1)→kaza(2), kaza(2)→önlenebilir(3)."""
    if baslangic in (1, 2) and (onceki_olumsuz or (tip is not None and tip in set(kriz_gecmisi))):
        return baslangic + 1
    return baslangic


def baskin_kume(seviyeler: Sequence[int]) -> Optional[str]:
    """Tasarım kararı 3: en sık küme; eşitlikte yüksek sorumluluk."""
    say = Counter(s for s in seviyeler if s > 0)
    if not say:
        return None
    en_cok = max(say.values())
    return SEVIYE_KUME[max(s for s, c in say.items() if c == en_cok)]


def alarm_donemleri(pencere_baslari: Sequence[datetime], seviye_listesi: Sequence[dict],
                    bin_saat: int = BIN_SAAT) -> list[dict]:
    """Tasarım kararı 18: seviye ≥ 1 olan ardışık pencereler tek dönem."""
    donemler: list[dict] = []
    aktif: Optional[dict] = None
    for bas, s in zip(pencere_baslari, seviye_listesi):
        if s["seviye"] >= 1:
            if aktif is None:
                aktif = {"baslangic": bas, "bitis": bas + timedelta(hours=bin_saat), "max_seviye": s["seviye"],
                         "kurallar": set(s["kurallar"]), "acik": True}
            else:
                aktif["bitis"] = bas + timedelta(hours=bin_saat)
                aktif["max_seviye"] = max(aktif["max_seviye"], s["seviye"])
                aktif["kurallar"].update(s["kurallar"])
        elif aktif is not None:
            aktif["acik"] = False
            donemler.append(aktif)
            aktif = None
    if aktif is not None:
        donemler.append(aktif)
    for d in donemler:
        d["kurallar"] = sorted(d["kurallar"])
        d["max_etiket"] = SEVIYE_ETIKETLERI[d["max_seviye"]]
    return donemler


Aralik = tuple[datetime, datetime]


def kapsayan_kumeler(kapsam: Mapping[str, Sequence[Aralik]], baslar: Sequence[datetime], bin_saat: int) -> list[frozenset]:
    """Her pencereyi tümüyle kapsayan başarılı tarama aralığına sahip kaynaklar."""
    sonuc = []
    for bas in baslar:
        son = bas + timedelta(hours=bin_saat)
        sonuc.append(frozenset(p for p, aralik in kapsam.items() if any(a <= bas and b >= son for a, b in aralik)))
    return sonuc


def kapsam_ozeti(kumeler: Sequence[frozenset], baslar: Sequence[datetime], kapsam: Mapping[str, Sequence[Aralik]]) -> dict:
    n = len(baslar)
    ozet = {}
    for p in kapsam:
        var = [i for i, k in enumerate(kumeler) if p in k]
        ozet[p] = {"kapsanan_pencere": len(var), "oran": len(var) / n if n else 0.0,
                   "ilk": baslar[var[0]].isoformat() if var else None,
                   "son": (baslar[var[-1]] + timedelta(hours=1)).isoformat() if var else None}
    degisim = []
    for i in range(1, n):
        if kumeler[i] != kumeler[i - 1]:
            degisim.append({"bas": baslar[i].isoformat(), "eklenen": sorted(kumeler[i] - kumeler[i - 1]),
                            "cikan": sorted(kumeler[i - 1] - kumeler[i])})
    return {"kaynaklar": ozet, "degisimler": degisim[:50]}


def analiz_et(
    icerikler: Sequence[IslenmisIcerik],
    simdi: datetime,
    *,
    trends: Mapping[datetime, float] | None = None,
    kriz_gecmisi: Iterable[str] = (),
    onceki_itibar: Optional[str] = None,          # "olumlu" | "notr" | "olumsuz" | None
    sosyal_kaynak_var: bool = True,
    haber_kaynak_var: bool = True,
    duygu_var: bool = True,
    uyarilmislik_var: bool = True,
    analiz_gun: int = ANALIZ_GUN,
    bin_saat: int = BIN_SAAT,
    z_yontemi: str = "stouffer",                  # "stouffer" | "strube" (Tasarım kararı 20)
    trends_var: bool | None = None,
    onceki_itibar_kaynak: str = "kullanici",      # "kullanici" | "lpti" (L-PTİ K5/K13)
    kapsam: Optional[Mapping[str, Sequence[Aralik]]] = None,   # kaynak → başarıyla taranmış aralıklar
    uzman_agirliklari: Optional[Mapping[str, float]] = None,   # 2. beyin; None = pasif
) -> dict:
    kriz_gecmisi = list(kriz_gecmisi)
    trends = dict(trends or {})
    bitis = saate_yuvarla(simdi, bin_saat)                       # son tamamlanmış pencerenin sonu
    n_pencere = int(analiz_gun * 24 / bin_saat)
    baslangic = bitis - timedelta(hours=bin_saat * n_pencere)
    baslar = [baslangic + timedelta(hours=bin_saat * k) for k in range(n_pencere)]

    kovalar: dict[int, list[IslenmisIcerik]] = defaultdict(list)
    for ic in icerikler:
        if baslangic <= ic.tarih < bitis:
            k = int((ic.tarih - baslangic).total_seconds() // (3600 * bin_saat))
            kovalar[k].append(ic)

    # --- 2) Önceki itibar
    jf_isinma = None
    if onceki_itibar in ("olumlu", "notr", "olumsuz"):
        itibar = {"deger": onceki_itibar, "kaynak": onceki_itibar_kaynak, "jf": None}
    else:
        haber = [i for k in range(min(ISINMA_PENCERE, n_pencere)) for i in kovalar.get(k, []) if i.tur == "haber"]
        if duygu_var and haber:
            f = sum(1 for i in haber if i.duygu_etiketi == "olumlu")
            u = sum(1 for i in haber if i.duygu_etiketi == "olumsuz")
            jf_isinma = janis_fadner(f, u, len(haber))
        if jf_isinma is None:
            itibar = {"deger": None, "kaynak": "bilinmiyor", "jf": None}
        else:
            itibar = {"deger": "olumsuz" if jf_isinma < 0 else "olumsuz_degil",
                      "kaynak": "isinma_janis_fadner", "jf": jf_isinma}
    onceki_olumsuz = itibar["deger"] == "olumsuz"

    # --- 3) SCCT yoğunlaştırıcıları
    for k, liste in kovalar.items():
        yeni = []
        for i in liste:
            s = yogunlastir(i.scct_seviye, i.scct_tip, kriz_gecmisi, onceki_olumsuz)
            yeni.append(replace(i, scct_seviye=s, scct_kume=SEVIYE_KUME[s]) if s != i.scct_seviye else i)
        kovalar[k] = yeni

    # --- 4) Gösterge ölçümü
    if trends_var is None:
        trends_var = bool(trends)
    kapsam_verildi = kapsam is not None
    if kapsam_verildi:
        kumeler = kapsayan_kumeler(kapsam, baslar, bin_saat)
    else:                                         # kapsam bilgisi yok: dönemde görülen platformlar tüm dönemi kapsar kabul edilir
        gorulen = frozenset(i.platform for i in icerikler)
        kapsam = {p: [(baslangic, bitis)] for p in gorulen}
        kumeler = [gorulen] * n_pencere
    ham: list[dict] = []
    for k, bas in enumerate(baslar):
        tv = trends.get(bas) if trends_var else None
        kume = kumeler[k]
        if kapsam_verildi:
            sosyal_var = any(KAYNAK_TURU.get(p) == "sosyal" for p in kume)
            haber_var = any(KAYNAK_TURU.get(p) == "haber" for p in kume)
        else:
            sosyal_var, haber_var = sosyal_kaynak_var, haber_kaynak_var
        b = Baglam(sosyal_var, haber_var, duygu_var, uyarilmislik_var, kume)
        ham.append(pencere_olc(kovalar.get(k, []), tv, b))

    # --- 5) Akış z-skorları
    norm = {kod: twitinfo.AkisNormallestirici() for kod in SECILEN_KODLAR}
    skorlar: list[dict] = []
    for k in range(n_pencere):
        skorlar.append({kod: norm[kod].adim(ham[k][kod]) for kod in SECILEN_KODLAR})

    # --- 6) Birleştirme (isteğe bağlı Strube korelasyonu ısınma sonrası skorlardan)
    korelasyon = None
    if z_yontemi == "strube":
        seriler = {kod: [None if s[kod] is None else composite.kirp(s[kod]) for s in skorlar[ISINMA_PENCERE:]]
                   for kod in SECILEN_KODLAR}
        korelasyon = kurum_esik.korelasyon_kestir(seriler)
    birlesik = [composite.birlestir(s, korelasyon) for s in skorlar]
    z_serisi = [b["z"] for b in birlesik]
    birlesik2 = [composite.birlestir(s, korelasyon, uzman_agirliklari) for s in skorlar] if uzman_agirliklari else None

    # --- 7) WECO
    sev = western_electric.seviyeler(z_serisi)

    # --- 8) SCCT tehdidi ve pencere özetleri
    pencereler = []
    for k, bas in enumerate(baslar):
        liste = kovalar.get(k, [])
        kume = baskin_kume([i.scct_seviye for i in liste])
        b = birlesik[k]
        pencereler.append({
            "bas": bas.isoformat(),
            "icerik_sayisi": len(liste),
            "sosyal_sayisi": sum(1 for i in liste if i.tur == "sosyal"),
            "haber_sayisi": sum(1 for i in liste if i.tur == "haber"),
            "gostergeler": ham[k],
            "skorlar": skorlar[k],
            "kre": b["kre"], "z": b["z"], "yuzdelik": b["yuzdelik"], "z_yontemi": b["yontem"],
            "kre_uzman": birlesik2[k]["kre"] if birlesik2 else None,
            "z_uzman": birlesik2[k]["z"] if birlesik2 else None,
            "risk_uzman": E.risk_puani(birlesik2[k]["z"]) if birlesik2 else None,
            "risk_ham_puan": E.risk_puani(b["z"]),
            **sev[k],
            "baskin_kume": kume,
            "tehdit": KUME_TEHDIT.get(kume) if kume else "Yok",
        })

    # --- 9) Kuruma özgü eşik istatistikleri (son pencere; karar dışı)
    gecmis_z = [z for z in z_serisi[ISINMA_PENCERE:-1] if z is not None]
    son = pencereler[-1] if pencereler else None
    son_b = birlesik[-1] if birlesik else {}
    boyut_katki = {}
    for boyut, kodlar in BOYUTLAR.items():
        katk = [son_b.get("katkilar", {}).get(k) for k in kodlar if k in son_b.get("katkilar", {})]
        boyut_katki[boyut] = sum(katk) if katk else None
    ham_esikler = {kod: {f"+{k}σ": norm[kod].esik_karsiligi(k) for k in (1, 2, 3)} for kod in SECILEN_KODLAR}

    g1 = [p["gostergeler"]["G1"] for p in pencereler]
    zirveler = []
    if all(v is not None for v in g1):
        zirveler = [{"bas": baslar[a].isoformat(), "son": baslar[b].isoformat()}
                    for a, b in twitinfo.zirve_pencereleri(g1)]

    eksik = sorted({kod for kod in SECILEN_KODLAR if all(h[kod] is None for h in ham)},
                   key=SECILEN_KODLAR.index)
    uyarilar = []
    if not duygu_var:
        uyarilar.append("Duygu motoru yok (NRC sözlüğü yüklü değil, TurkishBERTweet seçili değil): G6, G7 ve G11 eksik sayıldı.")
    if not uyarilmislik_var:
        uyarilar.append("NRC EmoLex Türkçe sözlüğü yüklü değil: G8, G9 ve G10 eksik sayıldı. "
                        "scripts/indir_nrc.py ile indirin [NRC_EMOLEX].")
    if son and son["gostergeler"].get("Q1") is not None and son["gostergeler"]["Q1"] > 0:
        uyarilar.append("Q1 > 0: son pencerede farklı yazarlarca paylaşılan aynı metin var; "
                        "sinyal kısmen koordineli/yapay olabilir [PACHECO2021].")

    return {
        "baslangic": baslangic.isoformat(),
        "bitis": bitis.isoformat(),
        "bin_saat": bin_saat,
        "pencere_sayisi": n_pencere,
        "isinma_pencere": ISINMA_PENCERE,
        "isinmada": n_pencere <= ISINMA_PENCERE,
        "onceki_itibar": itibar,
        "kriz_gecmisi": kriz_gecmisi,
        "pencereler": pencereler,
        "son": {
            **(son or {}),
            "agirliklar": son_b.get("agirliklar", {}),
            "uzman_agirliklar": (birlesik2[-1]["agirliklar"] if birlesik2 and birlesik2[-1].get("agirliklar") else {}),
            "uzman_katkilar": (birlesik2[-1]["katkilar"] if birlesik2 and birlesik2[-1].get("katkilar") else {}),
            "katkilar": son_b.get("katkilar", {}),
            "kirpilmis": son_b.get("kirpilmis", {}),
            "boyut_katkilari": boyut_katki,
            "ham_esikler": ham_esikler,
            "asim": kurum_esik.ampirik_asim_olasiligi(son["z"] if son else None, gecmis_z),
            "kalibrasyon": kurum_esik.kalibrasyon_tanisi(gecmis_z),
        },
        "g1_zirveleri": zirveler,
        "eksik_gostergeler": eksik,
        "kaynak_kapsami": kapsam_ozeti(kumeler, baslar, kapsam),
        "uzman_beyin": bool(uzman_agirliklari),
        "uyarilar": uyarilar,
        "alarm_donemleri": [
            {**d, "baslangic": d["baslangic"].isoformat(), "bitis": d["bitis"].isoformat()}
            for d in alarm_donemleri(baslar, sev, bin_saat)
        ],
    }


__all__ = ["analiz_et", "yogunlastir", "baskin_kume", "alarm_donemleri", "saate_yuvarla", "KUME_SEVIYE"]
