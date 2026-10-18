"""Kalıcı tarama iş kuyruğu, zamanlanmış taramalar ve haftalık brif zamanlaması."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.orm import BildirimKuyrugu, Kullanici, TaramaIsi
from app.services import bildirim, kaynaklar, tarama

log = logging.getLogger(__name__)
_TR = timezone(timedelta(hours=3))          # Türkiye kalıcı UTC+3
AKTIF = ("bekliyor", "calisiyor")


def is_olustur(db: Session, k: Kullanici, tur: str, tetikleyen: str) -> TaramaIsi:
    """Kurum için etkin iş varsa onu döndürür (tekrar tıklama mükerrer iş üretmez)."""
    var = db.query(TaramaIsi).filter(TaramaIsi.kurum_id == k.id, TaramaIsi.durum.in_(AKTIF)).first()
    if var:
        return var
    bas, bit = kaynaklar.aralik_coz(k)
    is_ = TaramaIsi(kurum_id=k.id, tur=tur, bas=bas, bit=bit, tetikleyen=tetikleyen)
    db.add(is_)
    db.commit()
    return is_


def siradaki_is_al(db: Session) -> Optional[TaramaIsi]:
    """Atomik sahiplenme: aynı işi iki işçi alamaz."""
    for aday in db.query(TaramaIsi).filter(TaramaIsi.durum == "bekliyor").order_by(TaramaIsi.tetikleyen == "sistem", TaramaIsi.id).limit(5).all():
        n = (db.query(TaramaIsi).filter(TaramaIsi.id == aday.id, TaramaIsi.durum == "bekliyor")
             .update({"durum": "calisiyor", "baslama": tarama.simdi_utc()}))
        db.commit()
        if n == 1:
            db.refresh(aday)
            return aday
    return None


async def isi_calistir(db: Session, is_: TaramaIsi) -> None:
    k = db.get(Kullanici, is_.kurum_id)
    try:
        if k is None:
            raise LookupError("Kurum bulunamadı")
        sonuc = await tarama.kurum_tara(db, k, is_)
        is_.kaynaklar = sonuc.get("kaynak_durumlari", [])
        is_.yeni_icerik = sonuc.get("yeni_icerik", 0)
        durumlar = [d["durum"] for d in is_.kaynaklar if d["durum"] != "atlandi"]
        is_.durum = ("hata" if durumlar and all(d == "hata" for d in durumlar) else
                     "tamam" if all(d == "tamam" for d in durumlar) else "kismi")
        is_.mesaj = ""
    except Exception as e:
        log.exception("Tarama işi %s başarısız", is_.id)
        db.rollback()
        is_ = db.get(TaramaIsi, is_.id)
        is_.durum, is_.mesaj = "hata", f"{type(e).__name__}: {str(e)[:400]}"
    is_.bitis = tarama.simdi_utc()
    db.commit()


def zamanlanmis_isleri_olustur(db: Session, simdi: Optional[datetime] = None) -> int:
    simdi = simdi or tarama.simdi_utc()
    olusan = 0
    for k in db.query(Kullanici).all():
        if db.query(TaramaIsi.id).filter(TaramaIsi.kurum_id == k.id, TaramaIsi.durum.in_(AKTIF)).first():
            continue
        if k.tekrar_plani == "tek_seferlik":
            gerek = not k.tek_seferlik_yapildi
        else:
            gerek = k.sonraki_tarama is None or k.sonraki_tarama <= simdi
        if not gerek:
            continue
        try:
            bas, bit = kaynaklar.aralik_coz(k)
        except kaynaklar.AralikHatasi:
            continue
        kapsam = kaynaklar.kapsam_oku(db, k)
        ilk = any(a not in kapsam for a in kaynaklar.etkin_kaynaklar(db, k))
        is_olustur(db, k, "gecmis" if ilk else "rutin", "sistem")
        olusan += 1
    return olusan


def donem_anahtari(simdi_tr: datetime) -> str:
    y, h, _ = simdi_tr.isocalendar()
    return f"{y}-W{h:02d}"


def haftalik_brifleri_kuyruga(db: Session, simdi: Optional[datetime] = None) -> int:
    """Kurumun seçtiği gün ve saatte (Türkiye saati) haftalık brifi kuyruğa yazar. Dönem anahtarı (ISO yıl-hafta) aynı
    haftanın ikinci kez gönderilmesini engeller; hesabı bir haftadan yeni kurumlara brif gönderilmez."""
    from app.pr import brif
    simdi = simdi or tarama.simdi_utc()
    yerel = simdi.replace(tzinfo=timezone.utc).astimezone(_TR)
    eklenen = 0
    for k in db.query(Kullanici).filter(Kullanici.bildirim_haftalik.is_(True)).all():
        if yerel.weekday() != (k.rapor_gunu or 0) or yerel.hour < (k.rapor_saati if k.rapor_saati is not None else 9):
            continue
        if k.olusturma and simdi - k.olusturma < timedelta(days=7):
            continue
        anahtar = f"haftalik:{k.id}:{donem_anahtari(yerel)}"
        if db.query(BildirimKuyrugu.id).filter(BildirimKuyrugu.anahtar == anahtar).first():
            continue
        konu, metin = brif.haftalik_metin(k, brif.brif_uret(db, k))
        eklenen += bildirim.haftalik_kuyruga_ekle(db, k, konu, metin, donem_anahtari(yerel))
        k.son_haftalik_brif = simdi
    db.commit()
    return eklenen


def takili_isleri_kapat(db: Session, simdi: Optional[datetime] = None) -> int:
    """İki saatten uzun 'calisiyor' kalan işler (işçi çökmüş) hataya alınır."""
    simdi = simdi or tarama.simdi_utc()
    n = 0
    for j in db.query(TaramaIsi).filter(TaramaIsi.durum == "calisiyor", TaramaIsi.baslama < simdi - timedelta(hours=2)).all():
        j.durum, j.bitis, j.mesaj = "hata", simdi, "İşçi yanıt vermedi; iş yeniden planlanacak"
        n += 1
    db.commit()
    return n
