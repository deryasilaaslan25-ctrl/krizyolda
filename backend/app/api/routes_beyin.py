"""İki beyin görünümü (tüm kurumlar): eşit ağırlıklı 1. beyin, uzman ağırlıklı 2. beyin ve karşılaştırma."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.beyin import servis as beyin
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.literatur import BOYUT_ADLARI, gosterge, tam_veri_agirliklari
from app.models.orm import Analiz, Kullanici

router = APIRouter(prefix="/api/beyin", tags=["beyin"])


@router.get("")
def beyinler(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    w1 = tam_veri_agirliklari()
    d = beyin.durum(db)
    w2 = d.get("agirliklar") if d.get("etkin") else None
    gostergeler = []
    for i in range(1, 14):
        kod = f"G{i}"
        g = gosterge(kod)
        gostergeler.append({"kod": kod, "ad": g["ad"], "boyut": BOYUT_ADLARI.get(g["boyut"], g["boyut"]),
                            "agirlik1": 100 * w1[kod], "agirlik2": 100 * w2[kod] if w2 else None,
                            "uzman_puani": d.get("birlesik_puan", {}).get(kod) if w2 else None,
                            "yayilim": d.get("yayilim", {}).get(kod) if w2 else None})
    a = db.query(Analiz).filter(Analiz.kurum_id == k.id).order_by(Analiz.zaman.desc(), Analiz.id.desc()).first()
    return {"beyin1": {"aciklama": "13 göstergenin tamamı eşit ağırlıkta (100/13 puan). Karar ve alarmlar bu beyinle verilir.",
                       "toplam": 100 * sum(w1.values())},
            "beyin2": {k_: v for k_, v in d.items() if k_ not in ("agirliklar", "birlesik_puan", "yayilim")},
            "gostergeler": gostergeler,
            "karsilastirma": (a.sonuc.get("beyin") if a else None)}
