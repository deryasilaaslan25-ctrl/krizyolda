"""Kaynak durumu ve kurumun kendi hesaplarına ait API bağlantıları (YouTube, X, Instagram)."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.collectors import instagram, x, youtube
from app.collectors.base import KaynakHatasi
from app.core import crypto
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import DenetimKaydi, KaynakBaglanti, KaynakKapsam, KaynakSaglik, Kullanici
from app.services import kaynaklar
from app.services.tarama import simdi_utc

router = APIRouter(prefix="/api/kaynaklar", tags=["kaynak"])

ALANLAR = {"youtube": ("api_anahtari", "YouTube Data API anahtarı", "Kanal kimliği (UC ile başlar)"),
           "x": ("bearer_token", "X taşıyıcı (bearer) token", "Hesap kullanıcı adı (@marka)"),
           "instagram": ("erisim_belirteci", "Instagram Graph API erişim belirteci", "Instagram işletme hesabı kimliği")}


class BaglantiIstegi(BaseModel):
    hesap_ref: str = Field(min_length=1, max_length=255)
    gizli: Optional[str] = Field(default=None, min_length=8, max_length=2000)   # boşsa mevcut kimlik bilgisi korunur


def _ozet(b: KaynakBaglanti) -> dict:
    alan = ALANLAR[b.platform]
    return {"platform": b.platform, "hesap_ref": b.hesap_ref, "durum": b.durum, "gizli_alan": alan[1],
            "maske": (b.kapsam or {}).get("maske", ""), "son_test": b.son_test.isoformat() if b.son_test else None,
            "son_basari": b.son_basari.isoformat() if b.son_basari else None, "son_hata": b.son_hata or "",
            "kapsam": {k: v for k, v in (b.kapsam or {}).items() if k != "maske"}}


@router.get("")
def durum(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    bas, bit = kaynaklar.aralik_coz(k)
    baglantilar = {b.platform: _ozet(b) for b in db.query(KaynakBaglanti).filter_by(kurum_id=k.id).all()}
    return {"aralik": {"bas": bas.isoformat(), "bit": bit.isoformat(), "tur": k.aralik_turu},
            "acik_kaynak": bool(k.acik_kaynak), "kaynaklar": kaynaklar.kaynak_ozeti(db, k, bas, bit),
            "baglantilar": baglantilar,
            "platformlar": [{"platform": p, "gizli_alan": a[1], "hesap_alan": a[2]} for p, a in ALANLAR.items()]}


@router.get("/saglik")
def saglik_gecmisi(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    satirlar = (db.query(KaynakSaglik).filter(KaynakSaglik.kurum_id == k.id).order_by(KaynakSaglik.id.desc()).limit(100).all())
    return [{"kaynak": s.kaynak, "zaman": s.zaman.isoformat(), "durum": s.durum, "adet": s.adet, "mesaj": s.mesaj,
             "istenen_bas": s.istenen_bas.isoformat() if s.istenen_bas else None,
             "ulasilan_bas": s.ulasilan_bas.isoformat() if s.ulasilan_bas else None, "is_id": s.is_id} for s in satirlar]


async def _test(platform: str, gizli: str, hesap: str) -> dict:
    if platform == "youtube":
        return await youtube.baglanti_test(gizli, hesap)
    if platform == "x":
        return await x.baglanti_test(gizli)
    return await instagram.baglanti_test(gizli, hesap)


async def _test_et(b: KaynakBaglanti, db: Session) -> dict:
    alan = ALANLAR[b.platform][0]
    try:
        gizli = crypto.coz(b.sifreli)[alan]
        kapsam = await _test(b.platform, gizli, b.hesap_ref)
        b.durum, b.son_hata, b.son_basari = "bagli", "", simdi_utc()
        b.kapsam = {**kapsam, "maske": crypto.maskele(gizli)}
        sonuc = {"basarili": True, **kapsam}
    except KaynakHatasi as e:
        b.durum = "yetki_yok" if e.kod == "yetki" else "hata"
        b.son_hata = str(e)[:500]
        sonuc = {"basarili": False, "neden": e.kod, "mesaj": str(e)[:500]}
    except ValueError as e:
        b.durum, b.son_hata = "hata", str(e)
        sonuc = {"basarili": False, "neden": "kimlik", "mesaj": str(e)}
    b.son_test = simdi_utc()
    db.commit()
    return sonuc


@router.put("/baglanti/{platform}")
async def baglan(platform: Literal["youtube", "x", "instagram"], g: BaglantiIstegi,
                 k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    alan = ALANLAR[platform][0]
    b = db.query(KaynakBaglanti).filter_by(kurum_id=k.id, platform=platform).first()
    if g.gizli is None and b is None:
        raise HTTPException(422, f"{ALANLAR[platform][1]} gerekli")
    sifreli = crypto.sifrele({alan: g.gizli}) if g.gizli else b.sifreli
    if b is None:
        b = KaynakBaglanti(kurum_id=k.id, platform=platform, hesap_ref=g.hesap_ref.strip(), sifreli=sifreli)
        db.add(b)
    else:
        b.hesap_ref, b.sifreli = g.hesap_ref.strip(), sifreli
    db.add(DenetimKaydi(kurum_id=k.id, islem="kaynak_baglandi", ayrinti={"platform": platform}))
    db.commit()
    sonuc = await _test_et(b, db)
    k.sonraki_tarama, k.tek_seferlik_yapildi = None, False    # yeni kaynak: eksik aralık hemen taranır
    db.commit()
    return {"baglanti": _ozet(b), "test": sonuc}


@router.post("/baglanti/{platform}/test")
async def test(platform: Literal["youtube", "x", "instagram"], k: Kullanici = Depends(gecerli_kullanici_al),
               db: Session = Depends(get_db)):
    b = db.query(KaynakBaglanti).filter_by(kurum_id=k.id, platform=platform).first()
    if b is None:
        raise HTTPException(404, "Bu platform için bağlantı yok")
    sonuc = await _test_et(b, db)
    return {"baglanti": _ozet(b), "test": sonuc}


@router.delete("/baglanti/{platform}")
def sil(platform: Literal["youtube", "x", "instagram"], k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    b = db.query(KaynakBaglanti).filter_by(kurum_id=k.id, platform=platform).first()
    if b is None:
        raise HTTPException(404, "Bu platform için bağlantı yok")
    db.delete(b)
    db.query(KaynakKapsam).filter_by(kurum_id=k.id, kaynak=platform).delete()
    db.add(DenetimKaydi(kurum_id=k.id, islem="kaynak_kaldirildi", ayrinti={"platform": platform}))
    db.commit()
    return {"durum": "silindi"}
