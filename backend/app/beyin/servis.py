"""2. beyin veritabanı katmanı: form sürümü, uzman puanları ve etkin ağırlıklar."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.beyin import uzman as U
from app.models.orm import UzmanForm, UzmanPuani


def aktif_form(db: Session) -> Optional[UzmanForm]:
    return db.query(UzmanForm).filter(UzmanForm.aktif.is_(True)).order_by(UzmanForm.id.desc()).first()


def puanlar(db: Session, form: UzmanForm) -> dict[str, dict[str, float]]:
    sonuc: dict[str, dict[str, float]] = {}
    for p in db.query(UzmanPuani).filter(UzmanPuani.form_id == form.id).all():
        sonuc.setdefault(p.uzman_kodu, {})[p.gosterge] = p.puan
    return sonuc


def durum(db: Session) -> dict:
    """Panelde gösterilen 2. beyin durumu. Etkin değilse nedeni açıkça söylenir."""
    form = aktif_form(db)
    if form is None:
        return {"etkin": False, "neden": "uzman_formu_yok",
                "aciklama": "Etkin bir uzman formu yok; uzman puanları girilene kadar 2. beyin hesaplanmaz."}
    p = puanlar(db, form)
    tam = U.tam_uzmanlar(p)
    bilgi = {"form": form.surum, "soru": form.soru, "olcek": [form.olcek_min, form.olcek_max],
             "birlestirme": form.birlestirme, "gerekli_uzman": form.min_uzman, "tam_uzman": len(tam),
             "girilen_uzman": len(p)}
    if len(tam) < form.min_uzman:
        return {"etkin": False, "neden": "uzman_verisi_bekleniyor",
                "aciklama": f"{len(tam)}/{form.min_uzman} uzmanın 13 gösterge puanı girildi; 2. beyin bekliyor.", **bilgi}
    sonuc = U.agirliklari_hesapla(p, form.birlestirme)
    return {"etkin": True, **bilgi, **sonuc}


def etkin_agirliklar(db: Session) -> Optional[dict[str, float]]:
    d = durum(db)
    return d["agirliklar"] if d.get("etkin") else None
