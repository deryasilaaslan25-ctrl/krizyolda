"""Tarama işleri: kalıcı kuyruk, durum, iptal."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import TARAMA_TETIKLE_LIMITI, limiter
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import Kullanici, TaramaIsi
from app.services import isler, kaynaklar
from app.services.tarama import simdi_utc

router = APIRouter(prefix="/api/tarama", tags=["tarama"])


def is_ozeti(j: TaramaIsi) -> dict:
    return {"id": j.id, "tur": j.tur, "durum": j.durum, "bas": j.bas.isoformat(), "bit": j.bit.isoformat(),
            "olusturma": j.olusturma.isoformat(), "baslama": j.baslama.isoformat() if j.baslama else None,
            "bitis": j.bitis.isoformat() if j.bitis else None, "yeni_icerik": j.yeni_icerik, "kaynaklar": j.kaynaklar or [],
            "mesaj": j.mesaj or "", "tetikleyen": j.tetikleyen}


@router.post("", status_code=202)
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def baslat(request: Request, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Taramayı kuyruğa alır; işçi çalıştırır. Etkin iş varsa o döner (mükerrer iş oluşmaz)."""
    try:
        j = isler.is_olustur(db, k, "elle", "kullanici")
    except kaynaklar.AralikHatasi as e:
        raise HTTPException(422, str(e))
    return is_ozeti(j)


@router.get("")
def liste(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    isler_ = db.query(TaramaIsi).filter(TaramaIsi.kurum_id == k.id).order_by(TaramaIsi.id.desc()).limit(30).all()
    return {"isler": [is_ozeti(j) for j in isler_],
            "plan": {"tekrar_plani": k.tekrar_plani, "aralik_dk": k.tarama_aralik_dk,
                     "sonraki": k.sonraki_tarama.isoformat() if k.sonraki_tarama else None,
                     "tek_seferlik_yapildi": bool(k.tek_seferlik_yapildi)}}


@router.get("/{is_id}")
def durum(is_id: int, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    j = db.query(TaramaIsi).filter_by(id=is_id, kurum_id=k.id).first()
    if j is None:
        raise HTTPException(404, "İş bulunamadı")
    return is_ozeti(j)


@router.post("/{is_id}/iptal")
def iptal(is_id: int, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    j = db.query(TaramaIsi).filter_by(id=is_id, kurum_id=k.id).first()
    if j is None:
        raise HTTPException(404, "İş bulunamadı")
    if j.durum != "bekliyor":
        raise HTTPException(409, "Yalnız bekleyen iş iptal edilebilir")
    j.durum, j.bitis, j.mesaj = "iptal", simdi_utc(), "Kullanıcı iptal etti"
    db.commit()
    return is_ozeti(j)
