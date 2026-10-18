"""PR danışmanlık merkezi: sürekli brif, kriz anı stratejisi, haftalık brif (Tasarım kararı 46–54)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import Alarm, Kullanici, PRKontrol
from app.pr import brif as brif_modulu
from app.pr import katalog as K
from app.pr import kontrol_listesi as KL
from app.pr.strateji import kriz_stratejisi
from app.services import bildirim

router = APIRouter(prefix="/api/pr", tags=["pr"])


@router.get("/brif")
def brif(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Verinin kendisinden üretilen güncel PR danışmanlık brifi (kriz olsun olmasın)."""
    return brif_modulu.brif_uret(db, k)


@router.get("/strateji")
def strateji(alarm_id: Optional[int] = None, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Bir alarm için (verilmezse açık alarm için) Coombs (2007) SCCT strateji önerisi."""
    q = db.query(Alarm).filter(Alarm.kurum_id == k.id)
    a = q.filter(Alarm.id == alarm_id).first() if alarm_id else q.filter(Alarm.acik.is_(True)).order_by(Alarm.baslangic.desc()).first()
    if a is None:
        raise HTTPException(404, "Alarm bulunamadı" if alarm_id else "Açık alarm yok; hazırlık stratejisi için /api/pr/brif")
    from app.services.tarama import onceki_itibar_coz
    etiket, _, _ = onceki_itibar_coz(db, k)
    olumsuz = etiket == "olumsuz"
    pi = a.parmak_izi or {}
    return {"alarm_id": a.id,
            **kriz_stratejisi(efektif_kume=a.baskin_kume, tip=pi.get("tip"), kriz_gecmisi=k.kriz_gecmisi or [],
                              onceki_itibar_olumsuz=olumsuz, alarm_acik=bool(a.acik))}


@router.get("/katalog")
def katalog():
    """Strateji kataloğu, kılavuz kuralları ve evreler (kaynaklarıyla)."""
    return {"evreler": K.EVRELER, "temel_yanit": K.TEMEL_YANIT, "stratejiler": K.STRATEJILER, "duruslar": K.DURUSLAR,
            "kurallar": K.KURALLAR, "zamanlama": K.ZAMANLAMA, "kanal": K.KANAL, "kaynak": "COOMBS2007"}


@router.post("/haftalik-gonder")
def haftalik_gonder(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Haftalık PR brifini şimdi kuyruğa yazar (deneme). Aynı dakika içinde ikinci istek ikinci e-posta üretmez."""
    if not bildirim.smtp_yapilandirildi():
        raise HTTPException(503, "SMTP yapılandırılmamış")
    b = brif_modulu.brif_uret(db, k)
    konu, metin = brif_modulu.haftalik_metin(k, b)
    anahtar = f"deneme-{int(datetime.now(timezone.utc).timestamp() // 60)}"
    bildirim.haftalik_kuyruga_ekle(db, k, konu, metin, anahtar)
    db.commit()
    bildirim.kuyrugu_isle(db)
    return {"alicilar": bildirim.eposta_alicilari(k)}


@router.get("/kontrol-listesi")
def kontrol_listesi(alarm_id: int = 0, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """alarm_id=0: genel hazırlık; alarm_id verilirse o alarmın işaretleri."""
    if alarm_id and not db.query(Alarm.id).filter_by(id=alarm_id, kurum_id=k.id).first():
        raise HTTPException(404, "Alarm bulunamadı")
    isaretli = {p.madde for p in db.query(PRKontrol).filter_by(kurum_id=k.id, alarm_id=alarm_id, tamam=True).all()}
    return {**KL.katalog(), "alarm_id": alarm_id, "tamamlanan": sorted(isaretli)}


class Isaret(BaseModel):
    madde: str
    tamam: bool
    alarm_id: int = 0


@router.put("/kontrol-listesi")
def kontrol_isaretle(g: Isaret, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    if g.madde not in KL.KODLAR:
        raise HTTPException(422, "Bilinmeyen madde")
    if g.alarm_id and not db.query(Alarm.id).filter_by(id=g.alarm_id, kurum_id=k.id).first():
        raise HTTPException(404, "Alarm bulunamadı")
    p = db.query(PRKontrol).filter_by(kurum_id=k.id, alarm_id=g.alarm_id, madde=g.madde).first()
    if p is None:
        p = PRKontrol(kurum_id=k.id, alarm_id=g.alarm_id, madde=g.madde)
        db.add(p)
    p.tamam, p.zaman = g.tamam, datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"madde": g.madde, "tamam": g.tamam}


@router.get("/olcutler")
def olcutler(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Kapanmış ve açık alarmlar için sistemin ölçebildiği süreç metrikleri. Girilmemiş zamanlar eksik sayılır."""
    from app.models.orm import Icerik
    sonuc = []
    for a in db.query(Alarm).filter(Alarm.kurum_id == k.id, Alarm.max_seviye >= 2).order_by(Alarm.baslangic.desc()).limit(50).all():
        icr = db.query(Icerik).filter(Icerik.kurum_id == k.id, Icerik.tarih >= a.baslangic, Icerik.tarih < a.bitis,
                                      Icerik.tur == "sosyal").all()
        olumsuz = sum(1 for i in icr if i.duygu_etiketi == "olumsuz")
        sonuc.append({"alarm_id": a.id, "baslangic": a.baslangic.isoformat(), "acik": a.acik, "max_seviye": a.max_seviye,
                      "ilk_yanit_dk": ((a.ilk_yanit_zamani - a.baslangic).total_seconds() / 60) if a.ilk_yanit_zamani else None,
                      "cozum_dk": ((a.cozum_zamani - a.baslangic).total_seconds() / 60) if a.cozum_zamani else None,
                      "sosyal_icerik": len(icr), "olumsuz_oran": (olumsuz / len(icr)) if icr else None})
    def medyan(anahtar: str):
        v = sorted(x[anahtar] for x in sonuc if x[anahtar] is not None)
        return (v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2) if v else None
    return {"alarmlar": sonuc, "ozet": {"alarm_sayisi": len(sonuc), "ilk_yanit_medyan_dk": medyan("ilk_yanit_dk"),
                                        "cozum_medyan_dk": medyan("cozum_dk")}}
