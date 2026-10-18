"""
Alarm (kriz kaydı) yaşam döngüsü, e-posta bildirimi kararı ve geri bildirimle öğrenme.

* olcum_alarm_isle: saatlik ölçümlerden alarm dönemi (nihai seviye ≥ Yüksek; ≤6 saatlik boşluk birleşir) — karar 37.
* bildirimleri_degerlendir: açık alarm için tek e-posta, yükselmede güncelleme — karar 38.
* geri_bildirim_isle: gerçek kriz / önemsiz; önemsiz işaretli aynı kriz bir daha e-posta üretmez — karar 39–40.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.literatur import (ALARM_BIRLESTIRME_SAAT, ALARM_MIN_SEVIYE, GERI_BILDIRIM_DEGERLERI,
                           RISK_SEVIYE_ETIKETLERI, gosterge)
from app.models.orm import Alarm, DenetimKaydi, Kullanici, RiskOlcumu
from app.nlp import anahtar
from app.nlp.sentiment import kurum_sozcukleri

log = logging.getLogger(__name__)


def _simdi() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Alarm dönemi durum makinesi
# ---------------------------------------------------------------------------
def olcum_alarm_isle(db: Session, k: Kullanici, satir: RiskOlcumu, pencere: dict, satirlar: Sequence[RiskOlcumu],
                     alarmlar: dict[int, Alarm], durum: dict) -> None:
    saat_sonu = satir.saat + timedelta(hours=1)
    acik: Optional[Alarm] = durum.get("acik")
    if (satir.nihai_seviye or 0) >= ALARM_MIN_SEVIYE:
        if acik is None:
            onceki = durum.get("son_kapanan")
            if onceki is not None and satir.saat - onceki.bitis <= timedelta(hours=ALARM_BIRLESTIRME_SAAT):
                acik = onceki                                 # aynı kriz: yeniden aç (Tasarım kararı 37)
                acik.acik = True
                for s in satirlar:                            # boşluk saatlerini alarma bağla
                    if onceki.bitis <= s.saat < satir.saat and s.alarm_id is None:
                        s.alarm_id = acik.id
                durum["son_kapanan"] = None
            else:
                acik = Alarm(kurum_id=k.id, baslangic=satir.saat, bitis=saat_sonu, acik=True,
                             max_seviye=satir.nihai_seviye, bildirim_durumu="yok")
                db.add(acik)
                db.flush()
                alarmlar[acik.id] = acik
            durum["acik"] = acik
        acik.bitis = max(acik.bitis or saat_sonu, saat_sonu)
        acik.max_seviye = max(acik.max_seviye or 0, satir.nihai_seviye)
        zler = [v for v in (acik.max_z, satir.z) if v is not None]
        acik.max_z = max(zler) if zler else None
        acik.max_risk = max(v for v in (acik.max_risk, satir.risk) if v is not None)
        kur = set(acik.kurallar or []) | set(pencere.get("kurallar") or [])
        acik.kurallar = sorted(kur)
        if pencere.get("baskin_kume"):
            acik.baskin_kume, acik.tehdit = pencere.get("baskin_kume"), pencere.get("tehdit")
        acik.saat_sayisi = int(((acik.bitis - acik.baslangic).total_seconds()) // 3600)
        satir.alarm_id = acik.id
    elif acik is not None:                                    # nihai seviye < Yüksek: dönem kapanır
        acik.acik = False
        if acik.bildirim_durumu in ("yok", None):
            acik.bildirim_durumu = "gecmis"                   # geçmişte kalan dönem bildirim üretmez
        durum["son_kapanan"], durum["acik"] = acik, None


# ---------------------------------------------------------------------------
# Parmak izi
# ---------------------------------------------------------------------------
def parmak_izi_uret(k: Kullanici, alarm: Alarm, icerikler: Sequence, ) -> dict:
    """Alarm süresindeki negatif/kriz içeriklerinden {tip, kume, govdeler, icerik_sayisi}."""
    aralik = [i for i in icerikler if alarm.baslangic <= i.tarih < (alarm.bitis or _simdi())]
    secili = [i for i in aralik if i.duygu_etiketi == "olumsuz" or i.scct_seviye > 0] or aralik
    tipler = Counter(i.scct_tip for i in secili if i.scct_tip)
    tip = tipler.most_common(1)[0][0] if tipler else None
    haric = kurum_sozcukleri(k.kurum, k.izleme_terimleri or [])
    govdeler = anahtar.anahtar_govdeler([f"{i.metin}" for i in secili], [i.metin for i in icerikler], haric)
    return {"tip": tip, "kume": alarm.baskin_kume, "govdeler": govdeler, "icerik_sayisi": len(secili)}


def benzer_onemsiz_alarmlar(db: Session, alarm: Alarm) -> list[tuple[Alarm, float]]:
    """Aynı kurumda daha önce ÖNEMSİZ işaretlenmiş ve bu alarma benzeyen alarmlar."""
    sonuc = []
    for a in db.query(Alarm).filter(Alarm.kurum_id == alarm.kurum_id, Alarm.id != alarm.id,
                                    Alarm.geri_bildirim == "yanlis_alarm").all():
        ayni, j = anahtar.ayni_kriz_mi(alarm.parmak_izi, a.parmak_izi)
        if ayni:
            sonuc.append((a, j))
    return sorted(sonuc, key=lambda t: -t[1])


def benzer_gercek_alarmlar(db: Session, alarm: Alarm) -> list[tuple[Alarm, float]]:
    sonuc = []
    for a in db.query(Alarm).filter(Alarm.kurum_id == alarm.kurum_id, Alarm.id != alarm.id,
                                    Alarm.geri_bildirim == "gercek_kriz").all():
        ayni, j = anahtar.ayni_kriz_mi(alarm.parmak_izi, a.parmak_izi)
        if ayni:
            sonuc.append((a, j))
    return sorted(sonuc, key=lambda t: -t[1])


# ---------------------------------------------------------------------------
# Bildirim kararı (Tasarım kararı 38–40)
# ---------------------------------------------------------------------------
def bildirim_karari(db: Session, k: Kullanici, alarm: Alarm) -> tuple[str, str, Optional[Alarm]]:
    """Dönüş: (karar, neden, benzer_alarm). karar: gonder | bastir | bekle."""
    if alarm.max_seviye < (k.bildirim_min_seviye or ALARM_MIN_SEVIYE):
        return "bekle", "en düşük bildirim seviyesinin altında", None
    yeni = (alarm.bildirim_seviye or 0) == 0
    yukseldi = (alarm.bildirim_seviye or 0) > 0 and alarm.max_seviye > alarm.bildirim_seviye
    if yukseldi and alarm.max_seviye < 3 and alarm.bildirim_son_zaman is not None:
        bekleme = timedelta(hours=k.bildirim_bekleme_saat if k.bildirim_bekleme_saat is not None else 6)
        if _simdi() - alarm.bildirim_son_zaman < bekleme:
            return "bekle", "bildirim bekleme süresi dolmadı (Kritik'e çıkış hariç)", None
    if alarm.geri_bildirim == "yanlis_alarm":
        esik = alarm.geri_bildirim_seviye or 0
        if alarm.max_seviye > esik and (yeni or yukseldi):
            return "gonder", "önemsiz işaretlenen alarm daha yüksek seviyeye çıktı", None
        return "bastir", "bu alarm önemsiz olarak işaretlendi", None
    if not yeni and not yukseldi:
        return "bekle", "bu seviye için bildirim zaten gönderildi", None
    if alarm.geri_bildirim != "gercek_kriz" and yeni:
        benzerler = benzer_onemsiz_alarmlar(db, alarm)
        if benzerler:
            en_yuksek = max((b.geri_bildirim_seviye or b.max_seviye) for b, _ in benzerler)
            if alarm.max_seviye <= en_yuksek:
                return "bastir", "daha önce önemsiz işaretlediğiniz benzer bir krizle eşleşti", benzerler[0][0]
    return "gonder", "eşik aşıldı" if yeni else "seviye yükseldi", None


def bildirimleri_degerlendir(db: Session, k: Kullanici, sonuc: dict, icerikler: Sequence) -> list[dict]:
    """Açık alarmlar için parmak izini günceller ve e-posta/Slack bildirimini kararlaştırır/gönderir."""
    from app.services import bildirim
    yapilan: list[dict] = []
    for alarm in db.query(Alarm).filter(Alarm.kurum_id == k.id, Alarm.acik.is_(True)).all():
        alarm.parmak_izi = parmak_izi_uret(k, alarm, icerikler)
        karar, neden, benzer = bildirim_karari(db, k, alarm)
        if karar == "bekle":
            continue
        if karar == "bastir":
            alarm.bildirim_durumu, alarm.bastirma_nedeni = "bastirildi", neden
            alarm.benzer_alarm_id = benzer.id if benzer else alarm.benzer_alarm_id
            db.add(DenetimKaydi(kurum_id=k.id, islem="bildirim_bastirildi",
                                ayrinti={"alarm": alarm.id, "neden": neden, "benzer": benzer.id if benzer else None}))
            yapilan.append({"alarm": alarm.id, "karar": "bastirildi", "neden": neden})
            continue
        if not (k.bildirim_email or k.bildirim_slack):
            alarm.bildirim_durumu = "kapali"
            continue
        kanallar = bildirim.alarm_bildir(db, k, alarm, sonuc, icerikler, guncelleme=(alarm.bildirim_seviye or 0) > 0,
                                         benzer_gercek=benzer_gercek_alarmlar(db, alarm))
        if kanallar:
            alarm.bildirildi, alarm.bildirim_seviye, alarm.bildirim_durumu = True, alarm.max_seviye, "kuyruga_alindi"
            alarm.bildirim_son_zaman = _simdi()
            alarm.bastirma_nedeni = ""
        else:
            alarm.bildirim_durumu = "alici_yok" if (alarm.bildirim_seviye or 0) == 0 else alarm.bildirim_durumu
        db.add(DenetimKaydi(kurum_id=k.id, islem="bildirim", ayrinti={"alarm": alarm.id, "kanallar": kanallar,
                                                                     "neden": neden, "seviye": alarm.max_seviye}))
        yapilan.append({"alarm": alarm.id, "karar": "kuyruga_alindi" if kanallar else "gonderilemedi", "kanallar": kanallar})
    return yapilan


# ---------------------------------------------------------------------------
# Geri bildirim
# ---------------------------------------------------------------------------
def normalize_geri_bildirim(deger: Optional[str]) -> Optional[str]:
    if deger in (None, ""):
        return None
    if deger == "onemsiz":
        deger = "yanlis_alarm"
    if deger not in GERI_BILDIRIM_DEGERLERI:
        raise ValueError("geri_bildirim: gercek_kriz | yanlis_alarm (onemsiz)")
    return deger


def geri_bildirim_isle(db: Session, alarm: Alarm, deger: Optional[str], not_metni: str = "", kaynak: str = "panel") -> dict:
    """Etiketi kaydeder. 'Önemsiz' → aynı alarm için e-posta durur, benzer krizler bastırılır; etiketler eşik
    hesabında kirlenme kuralları ve maliyet-duyarlı düzeltmeye girer (Metodoloji Bölüm 3.3 ve 6)."""
    onceki = alarm.geri_bildirim
    alarm.geri_bildirim = deger
    alarm.geri_bildirim_zamani = _simdi() if deger else None
    alarm.geri_bildirim_seviye = alarm.max_seviye if deger else None
    if not_metni:
        alarm.not_metni = not_metni[:2000]
    if deger == "yanlis_alarm" and alarm.bildirim_durumu in ("yok", "smtp_yok"):
        alarm.bildirim_durumu, alarm.bastirma_nedeni = "bastirildi", "bu alarm önemsiz olarak işaretlendi"
    if deger == "gercek_kriz" and alarm.bildirim_durumu == "bastirildi" and (alarm.bildirim_seviye or 0) == 0:
        alarm.bildirim_durumu, alarm.bastirma_nedeni = "yok", ""    # kullanıcı gerçek dedi: bastırma kalkar
    db.add(DenetimKaydi(kurum_id=alarm.kurum_id, islem="geri_bildirim",
                        ayrinti={"alarm": alarm.id, "onceki": onceki, "yeni": deger, "kaynak": kaynak}))
    db.flush()
    benzer = benzer_onemsiz_alarmlar(db, alarm) if deger == "yanlis_alarm" else []
    return {"alarm": alarm.id, "geri_bildirim": deger, "benzer_onemsiz_sayisi": len(benzer)}


def alarm_ozeti(a: Alarm, kuyruk: Optional[dict] = None) -> dict:
    return {
        "ilk_yanit_zamani": a.ilk_yanit_zamani.isoformat() if a.ilk_yanit_zamani else None,
        "cozum_zamani": a.cozum_zamani.isoformat() if a.cozum_zamani else None,
        "bildirim_kuyrugu": kuyruk or {},
        "id": a.id, "baslangic": a.baslangic.isoformat(), "bitis": a.bitis.isoformat(), "acik": a.acik,
        "max_seviye": a.max_seviye, "max_etiket": RISK_SEVIYE_ETIKETLERI[a.max_seviye], "kurallar": a.kurallar or [],
        "baskin_kume": a.baskin_kume, "tehdit": a.tehdit, "max_z": a.max_z, "max_risk": a.max_risk,
        "saat_sayisi": a.saat_sayisi, "geri_bildirim": a.geri_bildirim, "not_metni": a.not_metni or "",
        "bildirim_durumu": a.bildirim_durumu, "bildirim_seviye": a.bildirim_seviye,
        "bastirma_nedeni": a.bastirma_nedeni or "", "benzer_alarm_id": a.benzer_alarm_id,
        "terimler": (a.parmak_izi or {}).get("govdeler", []), "tip": (a.parmak_izi or {}).get("tip"),
    }
