"""İçerik listesi ve Google Trends CSV içe aktarma."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.collectors.google_trends import csv_ayristir
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import Icerik, Kullanici, TrendDegeri
from app.nlp.scct import KRIZ_TIPLERI

router = APIRouter(prefix="/api", tags=["icerik"])


@router.get("/icerikler")
def icerikler(tur: Optional[str] = None, platform: Optional[str] = None, duygu: Optional[str] = None,
              icerik_turu: Optional[str] = None, arama: Optional[str] = None,
              sadece_kriz: bool = False, sayfa: int = 1, boyut: int = 50,
              k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    boyut = max(1, min(boyut, 200))
    q = db.query(Icerik).filter(Icerik.kurum_id == k.id)
    if tur:
        q = q.filter(Icerik.tur == tur)
    if platform:
        q = q.filter(Icerik.platform == platform)
    if duygu:
        q = q.filter(Icerik.duygu_etiketi == duygu)
    if icerik_turu:
        q = q.filter(Icerik.icerik_turu == icerik_turu)
    if arama:
        q = q.filter(Icerik.metin.ilike(f"%{arama}%"))
    toplam = q.count()
    kayitlar = q.order_by(Icerik.tarih.desc()).offset((max(sayfa, 1) - 1) * boyut).limit(boyut * (4 if sadece_kriz else 1)).all()
    ogeler = []
    for i in kayitlar:
        s = i.scct or {}
        if sadece_kriz and not s.get("baslangic_seviye"):
            continue
        ogeler.append({
            "id": i.id, "platform": i.platform, "tur": i.tur, "erisim": i.erisim, "icerik_turu": i.icerik_turu, "yazar": i.yazar, "baslik": i.baslik, "metin": i.metin,
            "url": i.url, "tarih": i.tarih.isoformat(), "begeni": i.begeni, "yorum": i.yorum, "paylasim": i.paylasim,
            "duygu_etiketi": i.duygu_etiketi, "duygu": i.duygu, "niyet": i.niyet or [],
            "scct": {**s, "tip_adi": KRIZ_TIPLERI[s["tip"]]["ad"] if s.get("tip") else None},
        })
        if len(ogeler) >= boyut:
            break
    return {"toplam": toplam, "sayfa": sayfa, "boyut": boyut, "ogeler": ogeler}


@router.post("/trends/csv")
async def trends_csv(dosya: UploadFile = File(...), utc_farki_saat: float = Form(3.0),
                     k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Google Trends CSV içe aktarma (Rapor Bölüm 6; Tasarım kararı 28)."""
    ham = await dosya.read()
    if len(ham) > 2_000_000:
        raise HTTPException(413, "Dosya çok büyük")
    try:
        degerler = csv_ayristir(ham.decode("utf-8", errors="replace"), utc_farki_saat)
    except ValueError as e:
        raise HTTPException(422, f"CSV okunamadı: {e}")
    if not degerler:
        raise HTTPException(422, "Saatlik veri satırı bulunamadı (Google Trends 'Son 7 gün' dışa aktarımı gerekir)")
    for z, v in degerler.items():
        m = db.query(TrendDegeri).filter_by(kurum_id=k.id, zaman=z).first()
        if m:
            m.deger, m.kaynak = v, "csv"
        else:
            db.add(TrendDegeri(kurum_id=k.id, zaman=z, deger=v, kaynak="csv"))
    db.commit()
    return {"aktarilan": len(degerler), "ilk": min(degerler).isoformat(), "son": max(degerler).isoformat()}
