"""
Sürekli PR danışmanlığı brifi — kriz olsun olmasın her gün verinin kendisinden üretilir.

Çerçeve: Pearson & Mitroff (1993) beş evre [PEARSON_MITROFF1993]; sinyal tespiti için Fink (1986) prodromal evre ve
Western Electric bölgeleri; kriz anı stratejileri Coombs (2007) SCCT kılavuzu [COOMBS2007]; itibar için L-PTİ.
Hangi verinin hangi cümleyi ürettiği her bölümde 'kanit' alanında verilir. Literatür dışı kurallar Tasarım kararı 46–54'tedir.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.literatur import BOYUT_ADLARI, RISK_SEVIYE_ETIKETLERI, gosterge
from app.models.orm import Alarm, Analiz, Icerik, ItibarDalga, ItibarKosu, Kullanici, RiskOlcumu
from app.nlp.scct import KRIZ_TIPLERI, KUME_ADLARI
from app.pr import katalog as K
from app.pr.strateji import kriz_stratejisi
from app.reputation.servis import SURUCU_ADLARI

ZAYIF_SINYAL_PENCERE = 24
ZAYIF_SINYAL_MIN = 3
TOPARLANMA_GUN = 14

# Fombrun, Ponzi & Newburry (2015) Tablo 1 — sürücülerin özellikleri (L-PTİ raporu Bölüm 3.2 özeti)
SURUCU_OZELLIKLERI = {
    "products_services": "yüksek kalite, fiyatına değer, ürün/hizmetinin arkasında durma, müşteri ihtiyacını karşılama",
    "innovation": "yenilikçi olma, pazara ilk çıkma, değişime hızlı uyum",
    "workplace": "çalışanı adil ödüllendirme, sağlık ve refaha önem, fırsat eşitliği",
    "conduct": "açıklık ve şeffaflık, etik davranış, iş yapışta adalet",
    "citizenship": "çevreyi koruma, iyi amaçları destekleme, topluma olumlu etki",
    "leadership": "güçlü lider, net vizyon, iyi organize olma, yetkin yöneticiler",
    "performance": "kârlılık, beklentiyi aşan sonuç, güçlü büyüme beklentisi",
}


def _simdi() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _son_analiz(db: Session, k: Kullanici) -> Optional[dict]:
    a = db.query(Analiz).filter(Analiz.kurum_id == k.id).order_by(Analiz.zaman.desc(), Analiz.id.desc()).first()
    return a.sonuc if a else None


def _evre(acik: Optional[Alarm], son_kapanan: Optional[Alarm], etiketsiz: int, simdi: datetime) -> dict:
    if acik is not None:
        kod, neden = "hasar_sinirlama", "Açık bir kriz kaydı var (nihai seviye ≥ Yüksek)."
    elif son_kapanan is not None and simdi - son_kapanan.bitis <= timedelta(days=TOPARLANMA_GUN):
        kod, neden = "toparlanma", f"Son {TOPARLANMA_GUN} gün içinde kapanmış bir kriz kaydı var."
    elif etiketsiz > 0:
        kod, neden = "ogrenme", f"{etiketsiz} kapanmış alarm henüz 'gerçek kriz / önemsiz' olarak etiketlenmedi."
    else:
        kod, neden = "sinyal_tespiti", "Açık ya da yakın tarihli kriz kaydı yok: sinyal tespiti ve yoklama/önleme evresi."
    e = next(x for x in K.EVRELER if x["kod"] == kod)
    return {**e, "neden": neden, "tum_evreler": [{"kod": x["kod"], "no": x["no"], "ad": x["ad"]} for x in K.EVRELER]}


def zayif_sinyaller(pencereler: list[dict]) -> list[dict]:
    """Son 24 pencerenin en az 3'ünde s > +1σ olan göstergeler (Tasarım kararı 48)."""
    son = pencereler[-ZAYIF_SINYAL_PENCERE:]
    sonuc = []
    kodlar = sorted({k for p in son for k in (p.get("skorlar") or {})}, key=lambda c: int(c[1:]))
    for kod in kodlar:
        seri = [(p.get("skorlar") or {}).get(kod) for p in son]
        adet = sum(1 for s in seri if s is not None and s > 1.0)
        if adet >= ZAYIF_SINYAL_MIN:
            g = gosterge(kod)
            sonuc.append({"kod": kod, "ad": g["ad"], "boyut": BOYUT_ADLARI.get(g.get("boyut"), g.get("boyut")),
                          "pencere_sayisi": adet, "son_skor": seri[-1], "kaynaklar": g["kaynaklar"]})
    return sorted(sonuc, key=lambda s: -s["pencere_sayisi"])


def _hafta_karsilastirma(pencereler: list[dict]) -> Optional[dict]:
    if len(pencereler) < 336:
        return None
    bu, onceki = pencereler[-168:], pencereler[-336:-168]

    def ort(seri):
        v = [x for x in seri if x is not None]
        return sum(v) / len(v) if v else None
    return {
        "icerik": {"bu_hafta": sum(p["icerik_sayisi"] for p in bu), "onceki_hafta": sum(p["icerik_sayisi"] for p in onceki)},
        "olumsuzluk_G6": {"bu_hafta": ort([p["gostergeler"].get("G6") for p in bu]),
                          "onceki_hafta": ort([p["gostergeler"].get("G6") for p in onceki])},
        "haber_olumsuzlugu_G7": {"bu_hafta": ort([p["gostergeler"].get("G7") for p in bu]),
                                 "onceki_hafta": ort([p["gostergeler"].get("G7") for p in onceki])},
        "kanit": "Son 7 gün ile önceki 7 günün betimsel karşılaştırması (yorum içermez).",
    }


def _itibar(db: Session, k: Kullanici) -> dict:
    for dalga in db.query(ItibarDalga).filter(ItibarDalga.kurum_id == k.id).order_by(ItibarDalga.id.desc()).all():
        kosu = db.query(ItibarKosu).filter_by(wave_id=dalga.id).order_by(ItibarKosu.id.desc()).first()
        if not kosu or not kosu.sonuc:
            continue
        s = kosu.sonuc
        surucu = [d for d in s.get("drivers", []) if d.get("status") == "ok" and d.get("estimate") is not None]
        en_zayif = None
        if surucu:
            d = min(surucu, key=lambda x: x["estimate"])
            en_zayif = {"surucu": d["driver"], "ad": SURUCU_ADLARI.get(d["driver"], d["driver"]), "grup": d["group"],
                        "skor": d["estimate"], "ci95": d["ci95"], "ozellikler": SURUCU_OZELLIKLERI.get(d["driver"], ""),
                        "oneri": (f"İletişim odağı: {SURUCU_ADLARI.get(d['driver'], d['driver'])} "
                                  f"({SURUCU_OZELLIKLERI.get(d['driver'], '')}). Bu odak bir hipotezdir; sürücü önem ağırlıkları "
                                  "paydaşa ve pazara göre değişir (Tasarım kararı 53).")}
        return {"durum": "var", "dalga": dalga.id, "dalga_adi": dalga.name, "kosu": kosu.id,
                "genel_skor": s.get("overall_score"), "genel": s.get("overall"),
                "gruplar": s.get("stakeholder_scores", []), "surucular": s.get("drivers", []), "en_zayif_surucu": en_zayif,
                "degisim": s.get("comparison"), "kalite": s.get("quality"),
                "kaynaklar": ["PONZI2011", "FOMBRUN2015", "REPTRAK2026"]}
    return {"durum": "yok",
            "mesaj": ("Henüz anket tabanlı itibar ölçümü (L-PTİ) yok. Dijital sinyaller itibar skoru yerine geçmez; "
                      "itibar düzeyi için paydaş anketi gerekir."),
            "kaynaklar": ["PONZI2011", "WALKER2010"]}


def brif_uret(db: Session, k: Kullanici) -> dict:
    """Kurumun güncel PR danışmanlık brifi (kriz olsun olmasın)."""
    simdi = _simdi()
    sonuc = _son_analiz(db, k)
    alarmlar = db.query(Alarm).filter(Alarm.kurum_id == k.id).order_by(Alarm.baslangic.desc()).all()
    acik = next((a for a in alarmlar if a.acik), None)
    kapanan = [a for a in alarmlar if not a.acik]
    son_kapanan = kapanan[0] if kapanan else None
    etiketsiz = sum(1 for a in kapanan if a.geri_bildirim is None)
    evre = _evre(acik, son_kapanan, etiketsiz, simdi)
    b: dict = {"zaman": simdi.isoformat(), "kurum": k.kurum, "evre": evre, "analiz_var": sonuc is not None}

    # --- Ölçüm yoksa yalnızca yapılandırma önerileri
    yapilacaklar: list[dict] = []
    if not (k.kriz_gecmisi or []):
        yapilacaklar.append({"oncelik": 2, "baslik": "Kriz geçmişini girin",
                             "gerekce": "Benzer kriz geçmişi SCCT yoğunlaştırıcısıdır: sorumluluk atfını bir kademe artırır ve önerilen duruşu değiştirir. Girilmemişse G13 ve strateji önerisi eksik hesaplanır.",
                             "kaynaklar": ["COOMBS2007", "COOMBS2004"]})
    if not k.izleme_terimleri:
        yapilacaklar.append({"oncelik": 3, "baslik": "Ek izleme terimleri tanımlayın",
                             "gerekce": "Marka, ürün ve kısaltmalar izlenmezse sinyal kaçabilir (sinyal tespiti evresi).", "kaynaklar": ["PEARSON_MITROFF1993"]})
    if not sonuc:
        b["yapilacaklar"] = yapilacaklar
        b["mesaj"] = "Henüz analiz yok. Panelden 'Topla ve analiz et' ile ilk ölçümü başlatın."
        return b

    son = sonuc["son"]
    pencereler = sonuc["pencereler"]
    risk = son.get("risk")
    sa = {}
    # --- Sinyal radarı
    satirlar = db.query(RiskOlcumu).filter(RiskOlcumu.kurum_id == k.id, RiskOlcumu.saat >= simdi - timedelta(days=7)).all()
    sa["risk"] = None
    if risk:
        e = risk["esikler"]
        sa["risk"] = {"puan": risk["puan"], "etiket": risk["etiket"], "esikler": e, "esige_oran": risk.get("esige_oran"),
                      "donus_metni": risk.get("donus_metni"), "kaynak": risk.get("kaynak"), "guvenilirlik_z": risk.get("guvenilirlik_z"),
                      "n_blok": risk.get("n_blok"),
                      "son7_orta_ve_uzeri_saat": sum(1 for s in satirlar if (s.nihai_seviye or 0) >= 1),
                      "son7_yuksek_saat": sum(1 for s in satirlar if (s.nihai_seviye or 0) >= 2),
                      "olculen_saat_son7": len(satirlar),
                      "kaynaklar": ["THAYER2025", "WMO2023", "IEC62682_2022"]}
    sa["zayif_sinyaller"] = zayif_sinyaller(pencereler)
    sa["weco"] = {"kurallar": son.get("kurallar") or [], "sessiz_birikim": bool(son.get("sessiz_birikim")),
                  "etiket": son.get("etiket"), "kaynaklar": ["WECO1956", "FINK1986"]}
    sa["hafta"] = _hafta_karsilastirma(pencereler)
    sa["sinyal_kaynak"] = sorted(son.get("boyut_katkilari", {}).items(), key=lambda kv: -(kv[1] or -9))[:3]
    sa["sinyal_kaynak"] = [{"boyut": BOYUT_ADLARI.get(b_, b_), "katki": v} for b_, v in sa["sinyal_kaynak"] if v is not None]
    b["sinyal_radari"] = sa

    # --- SCCT kırılganlık
    icerikler = db.query(Icerik).filter(Icerik.kurum_id == k.id, Icerik.tarih >= simdi - timedelta(days=30)).all()
    tipler = Counter((i.scct or {}).get("tip") for i in icerikler if (i.scct or {}).get("baslangic_seviye"))
    tip_liste = [{"tip": t, "ad": KRIZ_TIPLERI[t]["ad"], "kume": KRIZ_TIPLERI[t]["kume"], "kume_adi": KUME_ADLARI[KRIZ_TIPLERI[t]["kume"]],
                  "adet": n} for t, n in tipler.most_common(5) if t in KRIZ_TIPLERI]
    onceki = sonuc.get("onceki_itibar") or {}
    olumsuz = onceki.get("deger") == "olumsuz"
    baskin_tip = tip_liste[0]["tip"] if tip_liste else None
    baskin_kume = None
    kume_sayim = Counter(p.get("baskin_kume") for p in pencereler[-720:] if p.get("baskin_kume"))
    if kume_sayim:
        baskin_kume = kume_sayim.most_common(1)[0][0]
    g11 = ((son.get("gostergeler") or {}).get("G11") or 0) >= 0.5
    hazirlik = kriz_stratejisi(efektif_kume=baskin_kume, tip=baskin_tip, kriz_gecmisi=k.kriz_gecmisi or [],
                               onceki_itibar_olumsuz=olumsuz, g11_yuksek=g11, alarm_acik=False)
    b["kirilganlik"] = {
        "yogunlastiricilar": {"kriz_gecmisi": k.kriz_gecmisi or [], "onceki_itibar": onceki.get("deger"),
                              "onceki_itibar_kaynak": onceki.get("kaynak"),
                              "aciklama": "Kriz geçmişi ve olumsuz önceki itibar, sorumluluk atfını bir kademe artıran SCCT yoğunlaştırıcılarıdır."},
        "son30_kriz_tipleri": tip_liste, "kume_dagilimi": dict(kume_sayim), "hazirlik_stratejisi": hazirlik,
        "kaynaklar": ["COOMBS2007", "COOMBS2004", "COOMBS_HOLLADAY2001"],
    }
    if olumsuz:
        yapilacaklar.append({"oncelik": 1, "baslik": "Önceki itibar olumsuz görünüyor: itibar onarımına öncelik verin",
                             "gerekce": "Olumsuz önceki ilişki itibarı SCCT'de sorumluluk atfını artırır; olası bir krizde daha kapsamlı yanıt gerektirir.",
                             "kaynaklar": ["COOMBS2007", "COOMBS_HOLLADAY2001"]})

    # --- İtibar (L-PTİ)
    b["itibar"] = _itibar(db, k)
    if b["itibar"]["durum"] == "yok":
        yapilacaklar.append({"oncelik": 2, "baslik": "Paydaş itibar anketi (L-PTİ) başlatın",
                             "gerekce": "Önceki itibar SCCT'de yoğunlaştırıcıdır ve şu an ısınma dönemi haber tonundan tahmin ediliyor; doğrulanmış ölçüm daha güvenilirdir.",
                             "kaynaklar": ["COOMBS2007", "MA_ZHAN2016", "PONZI2011"]})
    elif b["itibar"].get("en_zayif_surucu"):
        d = b["itibar"]["en_zayif_surucu"]
        yapilacaklar.append({"oncelik": 3, "baslik": f"İletişim odağı: {d['ad']}", "gerekce": d["oneri"], "kaynaklar": ["FOMBRUN2015", "REPTRAK2026"]})

    # --- Öğrenme
    gercek = sum(1 for a in alarmlar if a.geri_bildirim == "gercek_kriz")
    onemsiz = sum(1 for a in alarmlar if a.geri_bildirim == "yanlis_alarm")
    b["ogrenme"] = {
        "alarm_sayisi": len(alarmlar), "gercek": gercek, "onemsiz": onemsiz, "etiketsiz": etiketsiz,
        "bastirilan_bildirim": sum(1 for a in alarmlar if a.bildirim_durumu == "bastirildi"),
        "esik_etiket_duzeltmesi": bool(risk and risk.get("etiket_duzeltme")),
        "kesinlik": (gercek / (gercek + onemsiz)) if (gercek + onemsiz) else None,
        "mesaj": "Etiketleriniz eşiği yeniden ayarlar ve önemsiz işaretlenen kriz tipleri için e-posta gönderimini durdurur.",
        "kaynaklar": ["PEARSON_MITROFF1993", "YOUDEN1950"],
    }
    if etiketsiz:
        yapilacaklar.append({"oncelik": 1, "baslik": f"{etiketsiz} alarmı etiketleyin (gerçek kriz / önemsiz)",
                             "gerekce": "Öğrenme evresi: etiketler eşiği ve bildirimleri bu kuruma göre ayarlar.", "kaynaklar": ["PEARSON_MITROFF1993"]})

    # --- Kriz anı stratejisi
    if acik is not None:
        pi = acik.parmak_izi or {}
        b["kriz_stratejisi"] = kriz_stratejisi(efektif_kume=acik.baskin_kume, tip=pi.get("tip"), kriz_gecmisi=k.kriz_gecmisi or [],
                                               onceki_itibar_olumsuz=olumsuz, g11_yuksek=g11, alarm_acik=True)
        b["kriz_stratejisi"]["alarm_id"] = acik.id
        yapilacaklar.append({"oncelik": 0, "baslik": "Açık kriz kaydı: yanıt stratejisini uygulayın",
                             "gerekce": b["kriz_stratejisi"]["aciklama"], "kaynaklar": ["COOMBS2007", "ARPAN2005"]})
    else:
        b["kriz_stratejisi"] = None
    if not (sa["zayif_sinyaller"] or sa["weco"]["sessiz_birikim"]) and acik is None:
        b["mesaj"] = "Kriz sinyali yok; sistem izlemeyi sürdürüyor. Aşağıdaki bölümler hazırlık ve öğrenme içindir."
    else:
        b["mesaj"] = "İzlenmesi gereken zayıf sinyaller var; ayrıntılar sinyal radarında."
    if sa["weco"]["sessiz_birikim"]:
        yapilacaklar.append({"oncelik": 1, "baslik": "Sessiz birikim (WECO Kural 4): 8 ardışık pozitif sapma",
                             "gerekce": "Fink'in prodromal evresi: akut evreden önceki uyarı dönemi. İçerik akışını manuel gözden geçirin ve hazır yanıt iskeletini güncelleyin.",
                             "kaynaklar": ["FINK1986", "WECO1956"]})
    b["yapilacaklar"] = sorted(yapilacaklar, key=lambda y: y["oncelik"])
    b["kaynaklar"] = ["PEARSON_MITROFF1993", "COOMBS2007"]
    return b


def haftalik_metin(k: Kullanici, b: dict) -> tuple[str, str]:
    """Haftalık PR brifi e-postası (düz metin)."""
    sa = b.get("sinyal_radari") or {}
    r = sa.get("risk") or {}
    s = [f"{k.kurum} — haftalık PR danışmanlık brifi", "",
         f"Evre (Pearson & Mitroff 1993): {b['evre']['no']}. {b['evre']['ad']} — {b['evre']['neden']}", "", b.get("mesaj", "")]
    if r:
        s += ["", f"Risk puanı {r['puan']:.1f}/100 ({r['etiket']}); Yüksek eşik {r['esikler']['yuksek']:.1f}.",
              f"Son 7 günde {r['son7_orta_ve_uzeri_saat']} saat Orta ve üzeri, {r['son7_yuksek_saat']} saat Yüksek seviyede geçti "
              f"({r['olculen_saat_son7']} saat ölçüldü)."]
    if sa.get("zayif_sinyaller"):
        s += ["", "İzlenecek zayıf sinyaller:"] + [f"  • {z['kod']} {z['ad']} (son 24 pencerenin {z['pencere_sayisi']}'inde > +1σ)" for z in sa["zayif_sinyaller"][:5]]
    h = sa.get("hafta")
    if h:
        s += ["", f"İçerik hacmi: bu hafta {h['icerik']['bu_hafta']}, önceki hafta {h['icerik']['onceki_hafta']}."]
    it = b.get("itibar") or {}
    if it.get("durum") == "var" and it.get("genel_skor") is not None:
        s += ["", f"L-PTİ kurum geneli itibar skoru: {it['genel_skor']}"]
    elif it.get("durum") == "yok":
        s += ["", it["mesaj"]]
    if b.get("yapilacaklar"):
        s += ["", "Bu hafta yapılacaklar:"] + [f"  {i + 1}. {y['baslik']}" for i, y in enumerate(b["yapilacaklar"][:5])]
    o = b.get("ogrenme") or {}
    if o.get("alarm_sayisi"):
        s += ["", f"Alarm geçmişi: {o['alarm_sayisi']} kayıt; {o['gercek']} gerçek, {o['onemsiz']} önemsiz, {o['etiketsiz']} etiketsiz."]
    s += ["", "Ayrıntı ve strateji önerileri için panelde 'PR Danışmanlık' sekmesini açın."]
    return f"[ERKİS] {k.kurum}: haftalık PR brifi", "\n".join(s)
