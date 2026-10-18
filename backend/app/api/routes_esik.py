"""Kuruma özgü eşik: güncel durum, ölçüm geçmişi ve hesaplama ayrıntısı (Metodoloji Bölüm 12)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.literatur import (ESIK_P, RISK_SEVIYE_ETIKETLERI, RISK_SEVIYE_EYLEMI, RISK_Z_TAVAN)
from app.models.orm import Alarm, Kullanici, RiskOlcumu
from app.services.kurum_esik_servisi import etiket_puanlari, olcum_ozeti

router = APIRouter(prefix="/api/esik", tags=["esik"])


@router.get("/durum")
def durum(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    son = db.query(RiskOlcumu).filter(RiskOlcumu.kurum_id == k.id).order_by(RiskOlcumu.saat.desc()).first()
    alarmlar = db.query(Alarm).filter(Alarm.kurum_id == k.id).all()
    gercek, siradan = etiket_puanlari(alarmlar)
    return {
        "son": olcum_ozeti(son) if son else None,
        "p": ESIK_P, "donus_saatleri": {a: 1 / p for a, p in ESIK_P.items()}, "z_tavan": RISK_Z_TAVAN,
        "seviyeler": [{"seviye": s, "etiket": e, "eylem": RISK_SEVIYE_EYLEMI[s]} for s, e in RISK_SEVIYE_ETIKETLERI.items()],
        "etiketler": {"gercek": len(gercek), "onemsiz": len(siradan),
                      "duzeltme_icin_gerekli": "toplam ≥ 20 ve sınıf başına ≥ 5"},
        "olcum_sayisi": db.query(RiskOlcumu).filter(RiskOlcumu.kurum_id == k.id).count(),
    }


@router.get("/olcumler")
def olcumler(gun: int = 7, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    bas = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=min(max(gun, 1), 90))
    satirlar = db.query(RiskOlcumu).filter(RiskOlcumu.kurum_id == k.id, RiskOlcumu.saat >= bas).order_by(RiskOlcumu.saat).all()
    return [{"saat": s.saat.isoformat(), "risk": s.risk, "ham": s.ham_seviye, "nihai": s.nihai_seviye, "esikler": s.esikler,
             "hacim_z": s.hacim_z, "alarm_id": s.alarm_id} for s in satirlar]
