"""Literatür kataloğu ve sağlık kontrolü."""
from fastapi import APIRouter

from app import literatur
from app.config import settings
from app.nlp.lexicon import sozluk_al

router = APIRouter(prefix="/api", tags=["bilgi"])


@router.get("/literatur")
def literatur_katalogu():
    return literatur.katalog_json()


@router.get("/saglik")
def saglik():
    s = sozluk_al()
    return {"durum": "ayakta", "servis": settings.APP_NAME, "katalog_hatalari": literatur.dogrula_katalog(),
            "nrc_sozlugu": {"etkin": s is not None, "girdi_sayisi": len(s) if s else 0}}
