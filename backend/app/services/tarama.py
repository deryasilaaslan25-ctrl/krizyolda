"""
Tarama ve analiz servisi: topla → NLP → sakla → analiz (KRE/Z, iki beyin) → kuruma özgü eşik → alarm → bildirim kuyruğu.

Toplama yalnız kaynağın kapsamadığı aralığı çeker (ilk tarama = geçmiş tarama, sonrakiler = fark). Pencere sıfırı ancak
kaynak o pencereyi başarıyla taramışsa gerçek sıfırdır; aksi halde gösterge eksiktir (kaynak_kapsami).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.beyin import karsilastirma
from app.beyin import servis as beyin_servisi
from app.collectors.base import KaynakDurumu, Toplanan
from app.config import settings
from app.indicators.analysis import analiz_et
from app.literatur import RISK_SEVIYE_ETIKETLERI
from app.models.orm import Alarm, Analiz, DenetimKaydi, Icerik, Kullanici, TaramaIsi, TrendDegeri
from app.nlp import language
from app.nlp.lexicon import sozluk_al
from app.reputation import servis as itibar_servisi
from app.services import alarm_servisi, kaynaklar, kurum_esik_servisi, zamanlayici
from app.services.nlp_hatti import duygu_motoru_var, icerige_uygula, islenmis, yeniden_isle_gerekli

log = logging.getLogger(__name__)
SAKLANAN_ANALIZ = 48   # depolama sınırı; her analiz seçilen aralığın pencere dizisini içerir


def simdi_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def kaydet(db: Session, k: Kullanici, ogeler: list[Toplanan], trends: dict[datetime, float]) -> int:
    """Yeni içerikleri NLP'den geçirip saklar. Var olan içerikte yalnız etkileşim sayıları ve toplama zamanı güncellenir
    (metin ve tarih kaynakta sonradan değişse de korunur; Tasarım kararı 10)."""
    yeni = 0
    for o in ogeler:
        metin = o.metin or o.baslik
        if language.filtre_acik() and not language.turkce_mi(metin):
            continue
        mevcut = db.query(Icerik).filter_by(kurum_id=k.id, platform=o.platform, dis_id=o.dis_id).first()
        if mevcut:
            mevcut.begeni, mevcut.yorum, mevcut.paylasim = o.begeni, o.yorum, o.paylasim
            mevcut.toplama_zamani = simdi_utc()
            continue
        ic = Icerik(kurum_id=k.id, platform=o.platform, tur=o.tur, dis_id=o.dis_id, yazar=o.yazar, baslik=o.baslik,
                    metin=metin, url=o.url, tarih=o.tarih, begeni=o.begeni, yorum=o.yorum, paylasim=o.paylasim,
                    erisim=o.erisim, icerik_turu=o.icerik_turu)
        icerige_uygula(ic, k.kurum)
        db.add(ic)
        yeni += 1
    for z, v in trends.items():
        m = db.query(TrendDegeri).filter_by(kurum_id=k.id, zaman=z).first()
        if m:
            m.deger, m.kaynak = v, "pytrends"
        else:
            db.add(TrendDegeri(kurum_id=k.id, zaman=z, deger=v, kaynak="pytrends"))
    db.commit()
    return yeni


def onceki_itibar_coz(db: Session, k: Kullanici) -> tuple[Optional[str], str, Optional[dict]]:
    """K13: kullanıcı seçimi > en son geçerli L-PTİ (K5) > ısınma Janis–Fadner (None döner)."""
    if k.onceki_itibar in ("olumlu", "notr", "olumsuz"):
        return k.onceki_itibar, "kullanici", None
    etiket, ayrinti = itibar_servisi.onceki_itibar_etiketi(db, k)
    if etiket:
        return etiket, "lpti", ayrinti
    return None, "kullanici", None


def analiz_calistir(db: Session, k: Kullanici, simdi: Optional[datetime] = None) -> dict:
    bas, bit = kaynaklar.aralik_coz(k, simdi)
    canli = kaynaklar.canli_aralik(k, bit)
    kayitlar = db.query(Icerik).filter(Icerik.kurum_id == k.id, Icerik.tarih >= bas, Icerik.tarih < bit).all()
    degisti = False
    for ic in kayitlar:
        if yeniden_isle_gerekli(ic):
            icerige_uygula(ic, k.kurum)
            degisti = True
    if degisti:
        db.commit()
    icerikler = [islenmis(i) for i in kayitlar]
    trends = {t.zaman: t.deger for t in db.query(TrendDegeri).filter(TrendDegeri.kurum_id == k.id, TrendDegeri.zaman >= bas).all()}
    etiket, etiket_kaynak, lpti_ayrinti = onceki_itibar_coz(db, k)
    etkin = kaynaklar.etkin_kaynaklar(db, k)
    kapsam = kaynaklar.kapsam_oku(db, k, etkin)
    uzman_w = beyin_servisi.etkin_agirliklar(db)
    sonuc = analiz_et(
        icerikler, bit, trends=trends, kriz_gecmisi=k.kriz_gecmisi or [], onceki_itibar=etiket,
        onceki_itibar_kaynak=etiket_kaynak, duygu_var=duygu_motoru_var(), uyarilmislik_var=sozluk_al() is not None,
        z_yontemi=os.environ.get("ERKIS_Z_YONTEMI", settings.ERKIS_Z_YONTEMI),
        analiz_gun=(bit - bas).total_seconds() / 86400, kapsam=kapsam, uzman_agirliklari=uzman_w,
    )
    if lpti_ayrinti:
        sonuc["onceki_itibar"]["lpti"] = lpti_ayrinti
    sonuc["kurum"] = k.kurum
    sonuc["aralik"] = {"tur": k.aralik_turu, "bas": bas.isoformat(), "bit": bit.isoformat(), "canli": canli}
    sonuc["yontem"] = {
        "duygu_motoru": os.environ.get("ERKIS_DUYGU_MOTORU", settings.ERKIS_DUYGU_MOTORU),
        "scct_motoru": os.environ.get("ERKIS_SCCT_MOTORU", settings.ERKIS_SCCT_MOTORU),
        "z_yontemi": os.environ.get("ERKIS_Z_YONTEMI", settings.ERKIS_Z_YONTEMI),
        "nrc_yuklu": sozluk_al() is not None,
    }
    son = sonuc["son"]
    son["weco_seviye"] = son.get("seviye", 0)                       # WECO: açıklayıcı sinyal
    hacim_sok = False
    if canli:
        esik = kurum_esik_servisi.olcumleri_isle(db, k, sonuc)
        son["risk"] = esik["son"]
        son["seviye"] = (esik["son"] or {}).get("nihai_seviye", 0)  # karar: 1. beyin + kuruma özgü eşik
        hacim_sok = bool(((esik["son"] or {}).get("histerezis") or {}).get("hacim_sok"))
        sonuc["esik"] = {"durum": esik["durum"], "islenen_olcum": esik["islenen"]}
        sonuc["weco_donemleri"] = sonuc["alarm_donemleri"]
        sonuc["bildirimler"] = alarm_servisi.bildirimleri_degerlendir(db, k, sonuc, icerikler)
        alarmlar = db.query(Alarm).filter(Alarm.kurum_id == k.id, Alarm.baslangic >= bas).order_by(Alarm.baslangic).all()
        sonuc["alarm_donemleri"] = [{"id": a.id, "baslangic": a.baslangic.isoformat(), "bitis": a.bitis.isoformat(), "acik": a.acik,
                                     "max_seviye": a.max_seviye, "max_etiket": RISK_SEVIYE_ETIKETLERI[a.max_seviye],
                                     "kurallar": a.kurallar or []} for a in alarmlar]
    else:                                                           # geriye dönük inceleme: karar, alarm ve bildirim üretmez
        esik = {"durum": "gecmis_inceleme", "son": None, "islenen": 0}
        son["risk"] = None
        son["seviye"] = 0
        sonuc["esik"] = {"durum": "gecmis_inceleme", "islenen_olcum": 0}
        sonuc["bildirimler"] = []
    # 2. beyin: etkin değilse nedeniyle birlikte pasif raporlanır
    if uzman_w:
        ham = ((esik["son"] or {}).get("ham_seviye")) if canli else None
        sonuc["beyin"] = karsilastirma.karsilastir(sonuc, ham, uzman_w)
        sonuc["beyin"]["form"] = beyin_servisi.aktif_form(db).surum
    else:
        sonuc["beyin"] = {"etkin": False, **{k_: v for k_, v in beyin_servisi.durum(db).items()
                                              if k_ in ("neden", "aciklama", "form", "gerekli_uzman", "tam_uzman", "girilen_uzman")}}
    sonuc["kaynak_ozeti"] = kaynaklar.kaynak_ozeti(db, k, bas, bit)
    db.add(Analiz(kurum_id=k.id, zaman=bit, seviye=son["seviye"], z=son.get("z"), sonuc=sonuc))
    if canli:
        k.sonraki_tarama = zamanlayici.sonraki_tarama(k, simdi_utc(), son["seviye"], hacim_sok)
    db.flush()
    eski = (db.query(Analiz.id).filter(Analiz.kurum_id == k.id).order_by(Analiz.zaman.desc(), Analiz.id.desc())
            .offset(SAKLANAN_ANALIZ).all())
    if eski:
        db.query(Analiz).filter(Analiz.id.in_([e.id for e in eski])).delete(synchronize_session=False)
    db.commit()
    return sonuc


def is_durumu(durumlar: list[KaynakDurumu]) -> str:
    gercek = [d for d in durumlar if d.durum != "atlandi"]
    if not gercek:
        return "hata"
    if all(d.durum == "hata" for d in gercek):
        return "hata"
    return "tamam" if all(d.durum == "tamam" for d in gercek) else "kismi"


async def kurum_tara(db: Session, k: Kullanici, is_: Optional[TaramaIsi] = None) -> dict:
    bas, bit = kaynaklar.aralik_coz(k)
    ogeler, trends, durumlar = await kaynaklar.topla_hepsi(db, k, bas, bit)
    yeni = kaydet(db, k, ogeler, trends)
    kaynaklar.durumlari_kaydet(db, k, durumlar, is_.id if is_ else None)
    db.commit()
    sonuc = analiz_calistir(db, k)
    sonuc["kaynak_durumlari"] = [{"kaynak": d.kaynak, "durum": d.durum, "adet": d.adet, "mesaj": d.mesaj} for d in durumlar]
    sonuc["yeni_icerik"] = yeni
    if is_durumu(durumlar) == "hata":                 # hiçbir kaynak okunamadı: sonucu bekletmeden yeniden dene
        if k.tekrar_plani == "periyodik":
            k.sonraki_tarama = simdi_utc() + timedelta(minutes=min(60, max(zamanlayici.sinirlar(k)[0] * 2, 30)))
    elif k.tekrar_plani == "tek_seferlik":
        k.tek_seferlik_yapildi = True
    db.add(DenetimKaydi(kurum_id=k.id, islem="tarama", ayrinti={"yeni": yeni, "durum": is_durumu(durumlar)}))
    db.commit()
    return sonuc


__all__ = ["kurum_tara", "analiz_calistir", "kaydet", "onceki_itibar_coz", "is_durumu"]
