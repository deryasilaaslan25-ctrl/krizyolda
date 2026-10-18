"""Kurum profili: marka tanımı, veri kapsamı, tekrarlama planı, bildirim tercihleri."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.api.routes_auth import kullanici_ozeti
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import DenetimKaydi, Kullanici
from app.nlp.scct import KRIZ_TIPLERI
from app.services import bildirim, kaynaklar
from app.services.tarama import simdi_utc

router = APIRouter(prefix="/api/kurum", tags=["kurum"])


class ResmiHesap(BaseModel):
    platform: Literal["x", "instagram", "youtube", "tiktok", "linkedin", "facebook", "web"]
    hesap: str = Field(min_length=1, max_length=255)


class ProfilGuncelle(BaseModel):
    kurum: Optional[str] = Field(default=None, min_length=2, max_length=255)
    sektor: Optional[str] = None
    web_sitesi: Optional[str] = Field(default=None, max_length=255)
    izleme_terimleri: Optional[list[str]] = None
    haric_terimler: Optional[list[str]] = None
    resmi_hesaplar: Optional[list[ResmiHesap]] = Field(default=None, max_length=20)
    ek_rss: Optional[list[str]] = Field(default=None, max_length=10)
    kriz_gecmisi: Optional[list[str]] = None
    onceki_itibar: Optional[Literal["olumlu", "notr", "olumsuz", "otomatik"]] = None
    acik_kaynak: Optional[bool] = None
    aralik_turu: Optional[Literal["7", "30", "90", "180", "ozel"]] = None
    ozel_baslangic: Optional[date] = None
    ozel_bitis: Optional[date] = None
    tekrar_plani: Optional[Literal["periyodik", "tek_seferlik"]] = None
    tarama_min_dk: Optional[int] = Field(default=None, ge=15, le=360)
    tarama_max_dk: Optional[int] = Field(default=None, ge=15, le=360)
    bildirim_email: Optional[bool] = None
    bildirim_slack: Optional[bool] = None
    bildirim_min_seviye: Optional[int] = Field(default=None, ge=1, le=3)
    bildirim_haftalik: Optional[bool] = None
    bildirim_bekleme_saat: Optional[int] = Field(default=None, ge=0, le=72)
    bildirim_ek_epostalar: Optional[list[EmailStr]] = Field(default=None, max_length=5)
    rapor_gunu: Optional[int] = Field(default=None, ge=0, le=6)
    rapor_saati: Optional[int] = Field(default=None, ge=0, le=23)

    @field_validator("ek_rss")
    @classmethod
    def _rss(cls, v):
        if v is None:
            return v
        for a in v:
            if not a.startswith(("http://", "https://")):
                raise ValueError(f"RSS adresi http(s) ile başlamalı: {a}")
        return v


def _temiz(liste: list[str], sinir: int = 20) -> list[str]:
    return list(dict.fromkeys(t.strip() for t in liste if t.strip()))[:sinir]


@router.get("/profil")
def profil(k: Kullanici = Depends(gecerli_kullanici_al)):
    return {**kullanici_ozeti(k),
            "kriz_tipleri": [{"anahtar": a, "ad": t["ad"], "kume": t["kume"]} for a, t in KRIZ_TIPLERI.items()]}


@router.put("/profil")
def guncelle(g: ProfilGuncelle, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    kapsam_degisti = False
    if g.kriz_gecmisi is not None:
        bilinmeyen = [t for t in g.kriz_gecmisi if t not in KRIZ_TIPLERI]
        if bilinmeyen:
            raise HTTPException(422, f"Bilinmeyen kriz tipi: {', '.join(bilinmeyen)}")
        k.kriz_gecmisi = list(dict.fromkeys(g.kriz_gecmisi))
    for alan in ("izleme_terimleri", "haric_terimler"):
        v = getattr(g, alan)
        if v is not None:
            if _temiz(v) != (getattr(k, alan) or []):
                kapsam_degisti = True
            setattr(k, alan, _temiz(v))
    if g.ek_rss is not None:
        kapsam_degisti |= _temiz(g.ek_rss, 10) != (k.ek_rss or [])
        k.ek_rss = _temiz(g.ek_rss, 10)
    if g.resmi_hesaplar is not None:
        k.resmi_hesaplar = [h.model_dump() for h in g.resmi_hesaplar]
    if g.onceki_itibar is not None:
        k.onceki_itibar = None if g.onceki_itibar == "otomatik" else g.onceki_itibar
    if g.bildirim_ek_epostalar is not None:
        k.bildirim_ek_epostalar = list(dict.fromkeys(e.lower() for e in g.bildirim_ek_epostalar))
    if g.acik_kaynak is not None and g.acik_kaynak != bool(k.acik_kaynak):
        k.acik_kaynak, kapsam_degisti = g.acik_kaynak, True
    if g.aralik_turu is not None:
        if g.aralik_turu != k.aralik_turu:
            kapsam_degisti = True
        k.aralik_turu = g.aralik_turu
    if (g.ozel_baslangic is not None or g.ozel_bitis is not None) and g.aralik_turu is None:
        k.aralik_turu, kapsam_degisti = "ozel", True                # tarih verilince özel aralık seçilmiş sayılır
    if g.ozel_baslangic is not None:
        k.ozel_baslangic, kapsam_degisti = datetime.combine(g.ozel_baslangic, datetime.min.time()), True
    if g.ozel_bitis is not None:
        k.ozel_bitis, kapsam_degisti = datetime.combine(g.ozel_bitis, datetime.min.time()), True
    if g.tekrar_plani is not None:
        if g.tekrar_plani != k.tekrar_plani:
            k.tek_seferlik_yapildi = False
            k.sonraki_tarama = None
        k.tekrar_plani = g.tekrar_plani
    alt = g.tarama_min_dk if g.tarama_min_dk is not None else (k.tarama_min_dk or 15)
    ust = g.tarama_max_dk if g.tarama_max_dk is not None else (k.tarama_max_dk or 360)
    if alt > ust:
        raise HTTPException(422, "En kısa tarama aralığı en uzundan büyük olamaz")
    k.tarama_min_dk, k.tarama_max_dk = alt, ust
    for alan in ("kurum", "sektor", "web_sitesi", "bildirim_email", "bildirim_slack", "bildirim_min_seviye",
                 "bildirim_haftalik", "bildirim_bekleme_saat", "rapor_gunu", "rapor_saati"):
        v = getattr(g, alan)
        if v is not None:
            if alan == "kurum" and v != k.kurum:
                kapsam_degisti = True
            setattr(k, alan, v)
    if k.aralik_turu == "ozel":
        try:
            kaynaklar.aralik_coz(k)
        except kaynaklar.AralikHatasi as e:
            db.rollback()
            raise HTTPException(422, str(e))
        if k.ozel_bitis and k.ozel_bitis.date() > simdi_utc().date():
            db.rollback()
            raise HTTPException(422, "Özel aralığın bitişi bugünden sonra olamaz")
    if kapsam_degisti:                                    # kapsam değişince eksik aralık hemen taranır
        k.sonraki_tarama, k.tek_seferlik_yapildi = None, False
    db.add(DenetimKaydi(kurum_id=k.id, islem="profil_guncelle", ayrinti={"alanlar": sorted(g.model_fields_set)}))
    db.commit()
    return kullanici_ozeti(k)


@router.post("/test-eposta")
def test_eposta(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Deneme e-postasını kuyruğa yazar; sonuç /api/kurum/bildirimler'de görünür. SMTP kabulü gelen kutusu teslimi değildir."""
    if not bildirim.smtp_yapilandirildi():
        raise HTTPException(503, "SMTP yapılandırılmamış (SMTP_HOST ve SMTP_FROM)")
    alicilar = bildirim.eposta_alicilari(k)
    anahtar = f"test:{k.id}:{int(simdi_utc().timestamp())}"
    bildirim.kuyruga_ekle(db, kurum_id=k.id, tur="test", anahtar=anahtar, alicilar=alicilar,
                          konu=f"[Krizyolda] {k.kurum}: deneme e-postası",
                          metin="Bu bir deneme e-postasıdır. Kriz uyarıları ve haftalık raporlar bu adreslere gönderilecektir.")
    db.commit()
    ozet = bildirim.kuyrugu_isle(db)
    return {"alicilar": alicilar, **ozet}


@router.get("/bildirimler")
def bildirimler(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    from app.models.orm import BildirimKuyrugu
    satirlar = (db.query(BildirimKuyrugu).filter(BildirimKuyrugu.kurum_id == k.id)
                .order_by(BildirimKuyrugu.id.desc()).limit(50).all())
    return {"ozet": bildirim.kuyruk_durumu(db, k.id),
            "smtp_hazir": bildirim.smtp_yapilandirildi(),
            "kayitlar": [{"id": b.id, "tur": b.tur, "alici": b.alici, "konu": b.konu, "durum": b.durum, "deneme": b.deneme,
                          "son_hata": b.son_hata, "olusturma": b.olusturma.isoformat(),
                          "gonderim": b.gonderim.isoformat() if b.gonderim else None,
                          "sonraki_deneme": b.sonraki_deneme.isoformat() if b.durum == "tekrar_bekliyor" else None,
                          "alarm_id": b.alarm_id} for b in satirlar]}


__all__ = ["router"]
