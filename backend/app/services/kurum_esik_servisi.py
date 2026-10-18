"""
Kuruma özgü kriz eşiği — veritabanı katmanı ("Kuruma Özgü Kriz Eşiği Metodolojisi" Bölüm 3, 5, 10).

Matematik app/detection/esik_kalibrasyonu.py içindedir. Bu modül:
  * normal dönem verisini hazırlar: son 90 gün, kirlenmeden arındırma (Bölüm 3.3),
  * önsel zincirini kurar: sektör havuzu → platform havuzu → uzman önseli (Bölüm 5),
  * analist etiketlerini toplar (Bölüm 6),
  * her tamamlanmış saatlik pencere için ölçüm kaydı üretir (Bölüm 10, 12) ve alarm dönemini yürütür.

Kirlenmeden arındırma kuralları (Bölüm 3.3):
  1. Analistin GERÇEK KRİZ işaretlediği alarma bağlı ölçümler her zaman dışlanır.
  2. Nihai seviyesi Yüksek/Kritik olan ölçümler dışlanır — ancak etiketsiz olanlar yalnızca son 14 gün
     (Tasarım kararı 45: tırmanma çarkını önleyen karantina; eski etiketsiz alarm ölçümleri geri döner).
  3. Analistin ÖNEMSİZ (yanlış alarm) işaretlediği alarma bağlı ölçümler geri alınır.
"""
from __future__ import annotations

import bisect
from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.detection import esik_kalibrasyonu as E
from app.literatur import (ESIK_HAVUZ_MIN_BLOK, ESIK_KARANTINA_GUN, ESIK_HAVUZ_MIN_KURUM, ESIK_PENCERE_GUN, HISTEREZIS_K_OFF,
                           ISINMA_PENCERE, RISK_SEVIYE_ETIKETLERI, RISK_Z_TAVAN)
from app.models.orm import Alarm, Kullanici, RiskOlcumu
from app.services import alarm_servisi


def normal_donem_bloklari(satirlar: Sequence[RiskOlcumu], alarm_fb: dict[int, Optional[str]],
                          bas: datetime, bitis: datetime, karantina_gun: float = ESIK_KARANTINA_GUN) -> list[float]:
    """[bas, bitis) aralığındaki normal dönem R değerleri (kirlenmeden arındırılmış)."""
    sonuc: list[float] = []
    for s in satirlar:
        if not (bas <= s.saat < bitis):
            continue
        fb = alarm_fb.get(s.alarm_id) if s.alarm_id else None
        if fb == "gercek_kriz":            # kural 1
            continue
        if fb == "yanlis_alarm":           # kural 3: geri al
            sonuc.append(s.risk)
            continue
        if (s.nihai_seviye or 0) >= 2 and (bitis - s.saat) <= timedelta(days=karantina_gun):   # kural 2 (+ karar 45)
            continue
        sonuc.append(s.risk)
    return sonuc


def etiket_puanlari(alarmlar: Sequence[Alarm]) -> tuple[list[float], list[float]]:
    """Etiketli kriz kayıtlarının R değerleri (dönemdeki en yüksek R; Tasarım kararı 41)."""
    gercek = [a.max_risk for a in alarmlar if a.geri_bildirim == "gercek_kriz" and a.max_risk is not None]
    siradan = [a.max_risk for a in alarmlar if a.geri_bildirim == "yanlis_alarm" and a.max_risk is not None]
    return gercek, siradan


def _havuz(db: Session, k: Kullanici, bas: datetime, bitis: datetime, ayni_sektor: bool) -> tuple[list[float], int]:
    q = db.query(Kullanici).filter(Kullanici.id != k.id)
    if ayni_sektor:
        sek = (k.sektor or "").strip().lower()
        if not sek:
            return [], 0
        diger = [d for d in q.all() if (d.sektor or "").strip().lower() == sek]
    else:
        diger = q.all()
    if len(diger) < ESIK_HAVUZ_MIN_KURUM:
        return [], len(diger)
    ids = [d.id for d in diger]
    satirlar = db.query(RiskOlcumu).filter(RiskOlcumu.kurum_id.in_(ids), RiskOlcumu.saat >= bas,
                                           RiskOlcumu.saat < bitis).all()
    fb = {a.id: a.geri_bildirim for a in db.query(Alarm).filter(Alarm.kurum_id.in_(ids)).all()}
    bloklar: list[float] = []
    kurumlar = set()
    for kid in ids:
        kur = [s for s in satirlar if s.kurum_id == kid]
        b = normal_donem_bloklari(kur, fb, bas, bitis)
        if b:
            kurumlar.add(kid)
            bloklar += b
    if len(kurumlar) < ESIK_HAVUZ_MIN_KURUM or len(bloklar) < ESIK_HAVUZ_MIN_BLOK:
        return [], len(kurumlar)
    return bloklar, len(kurumlar)


def onsel_hesapla(db: Session, k: Kullanici, bitis: datetime) -> tuple[tuple[float, float, float], str, dict]:
    """Önsel zinciri: sektör havuzu → platform havuzu → uzman (50/75/95). Kurumun kendi verisi havuza alınmaz."""
    bas = bitis - timedelta(days=ESIK_PENCERE_GUN)
    for ad, sektor in (("sektor", True), ("platform", False)):
        bloklar, kurum_sayisi = _havuz(db, k, bas, bitis, sektor)
        if bloklar:
            t, kaynak = E.onsel_olustur(bloklar, ad)
            return t, kaynak, {"havuz_kurum": kurum_sayisi, "havuz_blok": len(bloklar)}
    t, kaynak = E.onsel_olustur(None, "uzman")
    return t, kaynak, {"havuz_kurum": 0, "havuz_blok": 0}


def _durum_yukle(db: Session, kurum_id: int) -> dict:
    acik = db.query(Alarm).filter(Alarm.kurum_id == kurum_id, Alarm.acik.is_(True)).order_by(Alarm.baslangic.desc()).first()
    son_kapanan = (db.query(Alarm).filter(Alarm.kurum_id == kurum_id, Alarm.acik.is_(False))
                   .order_by(Alarm.bitis.desc()).first())
    return {"acik": acik, "son_kapanan": son_kapanan}


def olcumleri_isle(db: Session, k: Kullanici, sonuc: dict) -> dict:
    """analiz_et çıktısındaki tamamlanmış pencerelerden ölçüm kaydı üretir.

    Kaydı olmayan pencereler (ve son pencere — blok maksimumu için) kronolojik sırayla, o ana kadarki
    veriyle hesaplanır (Tasarım kararı 36). Dönüş: son ölçümün ayrıntısı ve özet."""
    pen = sonuc["pencereler"]
    if len(pen) <= ISINMA_PENCERE:
        return {"durum": "isinmada", "son": None, "islenen": 0}
    bas_list = [datetime.fromisoformat(p["bas"]) for p in pen]
    hacimler = [float(p["icerik_sayisi"]) for p in pen]
    son_idx = len(pen) - 1
    pencere_bitis = bas_list[-1] + timedelta(hours=sonuc["bin_saat"])
    tarih_bas = bas_list[ISINMA_PENCERE] - timedelta(days=ESIK_PENCERE_GUN)

    satirlar: list[RiskOlcumu] = (db.query(RiskOlcumu).filter(RiskOlcumu.kurum_id == k.id, RiskOlcumu.saat >= tarih_bas)
                                  .order_by(RiskOlcumu.saat).all())
    zamanlar = [s.saat for s in satirlar]
    var = {s.saat: s for s in satirlar}
    alarmlar = {a.id: a for a in db.query(Alarm).filter(Alarm.kurum_id == k.id).all()}
    onsel, onsel_kaynak, onsel_ayrinti = onsel_hesapla(db, k, pencere_bitis)
    durum = _durum_yukle(db, k.id)
    islenen = 0
    son_satir: Optional[RiskOlcumu] = None
    fb = {aid: a.geri_bildirim for aid, a in alarmlar.items()}          # döngü boyunca değişmez
    gercek, siradan = etiket_puanlari(list(alarmlar.values()))

    for i in range(ISINMA_PENCERE, len(pen)):
        p = pen[i]
        saat = bas_list[i]
        mevcut = var.get(saat)
        if p["z"] is None:
            continue
        if mevcut is not None and i != son_idx:
            continue
        idx = bisect.bisect_left(zamanlar, saat)
        onceki = satirlar[:idx]
        x = normal_donem_bloklari(onceki, fb, saat - timedelta(days=ESIK_PENCERE_GUN), saat)
        esik = E.esik_hesapla(x, onsel, onsel_kaynak, etiket_gercek=gercek, etiket_siradan=siradan)

        r_yeni = E.risk_puani(p["z"])
        r = max(mevcut.risk, r_yeni) if mevcut is not None else r_yeni       # blok maksimumu (karar 31)
        ham = E.seviye_ham(r, esik.esikler)
        son_k = onceki[-(HISTEREZIS_K_OFF - 1):] if HISTEREZIS_K_OFF > 1 else []
        r_dizi = [s.risk for s in son_k] + [r]
        ham_dizi = [s.ham_seviye for s in son_k] + [ham]
        onceki_nihai = onceki[-1].nihai_seviye if onceki else 0
        hz = E.hacim_z_skoru(hacimler[max(0, i - 24):i], hacimler[i]) if i >= 24 else None
        h = E.histerezis(r_dizi=r_dizi, ham_dizi=ham_dizi, onceki_nihai=onceki_nihai, esikler=esik.esikler,
                         olcek_s=esik.olcek_s, hacim_z=hz)
        gpd = E.GPDUyum(**esik.gpd) if esik.gpd else None
        p_hat = E.asim_olasiligi(r, x, gpd)
        donus = E.donus_suresi_saat(p_hat)
        aciklama = E.aciklama_metni(r=r, nihai=h.nihai, ham=ham, esik=esik, p_hat=p_hat, donus_saat=donus, hist=h)
        ayrinti = {"gpd": esik.gpd, "onsel": list(esik.onsel), "onsel_kaynak": onsel_kaynak, **onsel_ayrinti,
                   "kurum_tahmini": list(esik.kurum_tahmini), "medyan": esik.medyan,
                   "etiket_duzeltme": esik.etiket_duzeltme, "k_kural": p.get("kurallar"), "weco_seviye": p.get("seviye")}
        if mevcut is None:
            satir = RiskOlcumu(kurum_id=k.id, saat=saat, gecmis=(i != son_idx))
            db.add(satir)
            j = bisect.bisect_left(zamanlar, saat)
            satirlar.insert(j, satir)
            zamanlar.insert(j, saat)
            var[saat] = satir
        else:
            satir = mevcut
        satir.risk, satir.z, satir.kre = r, p["z"], p.get("kre")
        satir.z_uzman, satir.risk_uzman = p.get("z_uzman"), p.get("risk_uzman")
        satir.hacim_z = hz
        satir.ham_seviye, satir.nihai_seviye = ham, h.nihai
        satir.esikler = list(esik.esikler)
        satir.esik_kaynagi = esik.kaynak
        satir.yontemler = dict(zip(E.KADEMELER, esik.yontemler))
        satir.guvenilirlik_z, satir.n_blok, satir.olcek_s = esik.guvenilirlik_z, esik.n, esik.olcek_s
        satir.p_asim, satir.donus_saat = p_hat, donus
        satir.korkuluk, satir.histerezis, satir.ayrinti = esik.korkuluk, h.sozluk(), ayrinti
        satir.aciklama = aciklama
        alarm_servisi.olcum_alarm_isle(db, k, satir, p, satirlar, alarmlar, durum)
        islenen += 1
        son_satir = satir

    db.flush()
    son = var.get(bas_list[-1])
    _pencereleri_zenginlestir(sonuc, var, bas_list)
    return {"durum": "tamam" if son else "olcum_yok", "islenen": islenen,
            "son": olcum_ozeti(son) if son else None}


def olcum_ozeti(s: RiskOlcumu) -> dict:
    """API/panel için tek ölçümün özeti."""
    e = s.esikler or [None, None, None]
    ay = s.ayrinti or {}
    return {
        "saat": s.saat.isoformat(), "puan": s.risk, "z": s.z, "z_tavan": RISK_Z_TAVAN, "hacim_z": s.hacim_z,
        "ham_seviye": s.ham_seviye, "nihai_seviye": s.nihai_seviye, "etiket": RISK_SEVIYE_ETIKETLERI[s.nihai_seviye or 0],
        "ham_etiket": RISK_SEVIYE_ETIKETLERI[s.ham_seviye or 0],
        "esikler": dict(zip(E.KADEMELER, e)), "kaynak": s.esik_kaynagi, "yontemler": s.yontemler,
        "guvenilirlik_z": s.guvenilirlik_z, "n_blok": s.n_blok, "olcek_s": s.olcek_s,
        "p": s.p_asim, "donus_saat": s.donus_saat, "donus_metni": E.donus_metni(s.donus_saat) if s.donus_saat else None,
        "korkuluk": s.korkuluk or [], "histerezis": s.histerezis or {}, "aciklama": s.aciklama,
        "gpd": ay.get("gpd"), "onsel": ay.get("onsel"), "onsel_kaynak": ay.get("onsel_kaynak"),
        "kurum_tahmini": ay.get("kurum_tahmini"), "etiket_duzeltme": ay.get("etiket_duzeltme"),
        "esige_oran": (s.risk / e[1]) if e and e[1] else None, "alarm_id": s.alarm_id, "gecmis": bool(s.gecmis),
    }


def _pencereleri_zenginlestir(sonuc: dict, var: dict[datetime, RiskOlcumu], bas_list: list[datetime]) -> None:
    for p, bas in zip(sonuc["pencereler"], bas_list):
        s = var.get(bas)
        if s is not None:
            p["risk_puani"], p["risk_ham"], p["risk_seviye"] = s.risk, s.ham_seviye, s.nihai_seviye
            p["risk_esik_yuksek"] = (s.esikler or [None, None, None])[1]
        else:
            p["risk_puani"] = p["risk_ham"] = p["risk_seviye"] = p["risk_esik_yuksek"] = None
