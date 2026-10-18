"""2. beyin yönetimi (yalnız yönetici): uzman formu sürümleri ve uzman puanları."""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.beyin import servis as beyin
from app.beyin import uzman as U
from app.core.security import rol_gerekli
from app.database import get_db
from app.literatur import gosterge
from app.models.orm import DenetimKaydi, Kullanici, UzmanForm, UzmanPuani

router = APIRouter(prefix="/api/uzman", tags=["uzman"], dependencies=[Depends(rol_gerekli("yonetici"))])
KOD = re.compile(r"^U\d{2}$")


class FormIstegi(BaseModel):
    surum: str = Field(min_length=1, max_length=20)
    soru: str = Field(min_length=10, max_length=1000)
    olcek_min: float
    olcek_max: float
    birlestirme: Literal["ortalama", "medyan"] = "ortalama"
    min_uzman: int = Field(default=12, ge=1, le=99)


class UzmanPuanlari(BaseModel):
    puanlar: dict[str, float]
    gerekceler: dict[str, str] = Field(default_factory=dict)


def _form_ozeti(db: Session, f: UzmanForm) -> dict:
    p = beyin.puanlar(db, f)
    return {"id": f.id, "surum": f.surum, "soru": f.soru, "olcek_min": f.olcek_min, "olcek_max": f.olcek_max,
            "birlestirme": f.birlestirme, "min_uzman": f.min_uzman, "aktif": f.aktif,
            "uzman_sayisi": len(p), "tam_uzman": len(U.tam_uzmanlar(p)), "olusturma": f.olusturma.isoformat()}


@router.get("/durum")
def durum(db: Session = Depends(get_db)):
    return beyin.durum(db)


@router.get("/gostergeler")
def gostergeler():
    return [{"kod": f"G{i}", "ad": gosterge(f"G{i}")["ad"], "olcum": gosterge(f"G{i}")["olcum"]} for i in range(1, 14)]


@router.get("/formlar")
def formlar(db: Session = Depends(get_db)):
    return [_form_ozeti(db, f) for f in db.query(UzmanForm).order_by(UzmanForm.id.desc()).all()]


@router.post("/formlar", status_code=201)
def form_olustur(g: FormIstegi, y: Kullanici = Depends(rol_gerekli("yonetici")), db: Session = Depends(get_db)):
    if g.olcek_max <= g.olcek_min:
        raise HTTPException(422, "Ölçek üst sınırı alt sınırdan büyük olmalı")
    if db.query(UzmanForm).filter_by(surum=g.surum).first():
        raise HTTPException(409, "Bu sürüm adı kullanılıyor")
    f = UzmanForm(surum=g.surum, soru=g.soru, olcek_min=g.olcek_min, olcek_max=g.olcek_max, birlestirme=g.birlestirme,
                  min_uzman=g.min_uzman, aktif=False)
    db.add(f)
    db.add(DenetimKaydi(kurum_id=y.id, islem="uzman_form_olustur", ayrinti={"surum": g.surum}))
    db.commit()
    return _form_ozeti(db, f)


def _form(db: Session, form_id: int) -> UzmanForm:
    f = db.get(UzmanForm, form_id)
    if f is None:
        raise HTTPException(404, "Form bulunamadı")
    return f


@router.post("/formlar/{form_id}/aktif")
def aktiflestir(form_id: int, y: Kullanici = Depends(rol_gerekli("yonetici")), db: Session = Depends(get_db)):
    f = _form(db, form_id)
    for d in db.query(UzmanForm).filter(UzmanForm.aktif.is_(True)).all():
        d.aktif = False
    f.aktif = True
    db.add(DenetimKaydi(kurum_id=y.id, islem="uzman_form_aktif", ayrinti={"surum": f.surum}))
    db.commit()
    return beyin.durum(db)


@router.post("/formlar/{form_id}/pasif")
def pasiflestir(form_id: int, y: Kullanici = Depends(rol_gerekli("yonetici")), db: Session = Depends(get_db)):
    f = _form(db, form_id)
    f.aktif = False
    db.add(DenetimKaydi(kurum_id=y.id, islem="uzman_form_pasif", ayrinti={"surum": f.surum}))
    db.commit()
    return beyin.durum(db)


@router.get("/formlar/{form_id}/puanlar")
def puanlar(form_id: int, db: Session = Depends(get_db)):
    f = _form(db, form_id)
    satirlar = db.query(UzmanPuani).filter_by(form_id=f.id).all()
    matris: dict[str, dict] = {}
    for s in satirlar:
        matris.setdefault(s.uzman_kodu, {"puanlar": {}, "gerekceler": {}})
        matris[s.uzman_kodu]["puanlar"][s.gosterge] = s.puan
        if s.gerekce:
            matris[s.uzman_kodu]["gerekceler"][s.gosterge] = s.gerekce
    return {"form": _form_ozeti(db, f), "uzmanlar": dict(sorted(matris.items()))}


@router.put("/formlar/{form_id}/uzmanlar/{kod}")
def uzman_puanla(form_id: int, kod: str, g: UzmanPuanlari, y: Kullanici = Depends(rol_gerekli("yonetici")),
                 db: Session = Depends(get_db)):
    """Uzman kodu U01–U99; ad/soyad saklanmaz. Eksik gösterge boş bırakılabilir, sıfır sayılmaz."""
    f = _form(db, form_id)
    if not KOD.match(kod):
        raise HTTPException(422, "Uzman kodu U01 … U99 biçiminde olmalı")
    try:
        U.dogrula({kod: g.puanlar}, f.olcek_min, f.olcek_max)
    except U.UzmanVerisiHatasi as e:
        raise HTTPException(422, str(e))
    for gos, p in g.puanlar.items():
        s = db.query(UzmanPuani).filter_by(form_id=f.id, uzman_kodu=kod, gosterge=gos).first()
        if s is None:
            db.add(UzmanPuani(form_id=f.id, uzman_kodu=kod, gosterge=gos, puan=p, gerekce=g.gerekceler.get(gos, "")))
        else:
            s.puan, s.gerekce = p, g.gerekceler.get(gos, s.gerekce)
    db.add(DenetimKaydi(kurum_id=y.id, islem="uzman_puan", ayrinti={"form": f.surum, "uzman": kod, "gosterge_sayisi": len(g.puanlar)}))
    db.commit()
    return {"form": _form_ozeti(db, f), "durum": beyin.durum(db) if f.aktif else None}


@router.delete("/formlar/{form_id}/uzmanlar/{kod}")
def uzman_sil(form_id: int, kod: str, y: Kullanici = Depends(rol_gerekli("yonetici")), db: Session = Depends(get_db)):
    f = _form(db, form_id)
    n = db.query(UzmanPuani).filter_by(form_id=f.id, uzman_kodu=kod).delete()
    if not n:
        raise HTTPException(404, "Uzman bulunamadı")
    db.add(DenetimKaydi(kurum_id=y.id, islem="uzman_sil", ayrinti={"form": f.surum, "uzman": kod}))
    db.commit()
    return _form_ozeti(db, f)


__all__ = ["router"]
