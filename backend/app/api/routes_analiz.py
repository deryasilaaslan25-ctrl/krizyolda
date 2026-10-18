"""Analiz uçları."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import Analiz, Kullanici
from app.services import kaynaklar, tarama

router = APIRouter(prefix="/api/analiz", tags=["analiz"])


@router.get("/son")
def son_analiz(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    a = db.query(Analiz).filter(Analiz.kurum_id == k.id).order_by(Analiz.zaman.desc(), Analiz.id.desc()).first()
    if a is None:
        return {"durum": "analiz_yok"}
    return {"durum": "tamam", "zaman": a.zaman.isoformat(), **a.sonuc}


@router.post("/yeniden-hesapla")
def yeniden_hesapla(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Toplama yapmadan, kayıtlı veri üzerinde analizi yeniden çalıştırır (ör. uzman ağırlıkları ya da aralık değişince)."""
    try:
        return tarama.analiz_calistir(db, k)
    except kaynaklar.AralikHatasi as e:
        raise HTTPException(422, str(e))
