"""Alarm (kriz kaydı) listesi, geri bildirim ('gerçek kriz' / 'önemsiz') ve değerlendirme."""

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from scipy.stats import beta
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import GIRIS_LIMITI, limiter
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.literatur import RISK_SEVIYE_ETIKETLERI
from app.models.orm import Alarm, Kullanici
from app.services import alarm_servisi

router = APIRouter(prefix="/api/alarmlar", tags=["alarm"])
acik_router = APIRouter(prefix="/api/geri-bildirim", tags=["alarm"])


class GeriBildirim(BaseModel):
    geri_bildirim: Optional[Literal["gercek_kriz", "yanlis_alarm", "onemsiz"]] = None
    not_metni: str = ""


def _kuyruk(db: Session, alarm_id: int) -> dict:
    from sqlalchemy import func
    from app.models.orm import BildirimKuyrugu
    return dict(db.query(BildirimKuyrugu.durum, func.count(BildirimKuyrugu.id))
                .filter(BildirimKuyrugu.alarm_id == alarm_id).group_by(BildirimKuyrugu.durum).all())


@router.get("")
def liste(min_seviye: int = 2, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    q = db.query(Alarm).filter(Alarm.kurum_id == k.id, Alarm.max_seviye >= min_seviye).order_by(Alarm.baslangic.desc())
    return [alarm_servisi.alarm_ozeti(a, _kuyruk(db, a.id)) for a in q.limit(500).all()]


class Yanit(BaseModel):
    ilk_yanit_zamani: Optional[datetime] = None
    cozum_zamani: Optional[datetime] = None


@router.put("/{alarm_id}/yanit")
def yanit_zamani(alarm_id: int, g: Yanit, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Kurumun ilk kamuya yanıt ve çözüm zamanı (UTC); PR ölçütlerinde kullanılır."""
    a = db.query(Alarm).filter(Alarm.id == alarm_id, Alarm.kurum_id == k.id).first()
    if a is None:
        raise HTTPException(404, "Alarm bulunamadı")
    def utc(t):
        return t.astimezone(timezone.utc).replace(tzinfo=None) if t and t.tzinfo else t
    ilk, coz = utc(g.ilk_yanit_zamani), utc(g.cozum_zamani)
    if ilk and ilk < a.baslangic:
        raise HTTPException(422, "İlk yanıt zamanı alarm başlangıcından önce olamaz")
    if coz and ilk and coz < ilk:
        raise HTTPException(422, "Çözüm zamanı ilk yanıttan önce olamaz")
    a.ilk_yanit_zamani, a.cozum_zamani = ilk, coz
    db.commit()
    return alarm_servisi.alarm_ozeti(a, _kuyruk(db, a.id))


@router.post("/{alarm_id}/geri-bildirim")
def geri_bildirim(alarm_id: int, g: GeriBildirim, k: Kullanici = Depends(gecerli_kullanici_al),
                  db: Session = Depends(get_db)):
    """'gercek_kriz' | 'onemsiz' (= yanlis_alarm). Önemsiz: aynı ve benzer krizler için e-posta gönderilmez."""
    a = db.query(Alarm).filter(Alarm.id == alarm_id, Alarm.kurum_id == k.id).first()
    if a is None:
        raise HTTPException(404, "Alarm bulunamadı")
    try:
        deger = alarm_servisi.normalize_geri_bildirim(g.geri_bildirim)
    except ValueError as e:
        raise HTTPException(422, str(e))
    ozet = alarm_servisi.geri_bildirim_isle(db, a, deger, g.not_metni)
    db.commit()
    return {**alarm_servisi.alarm_ozeti(a, _kuyruk(db, a.id)), "benzer_onemsiz_sayisi": ozet["benzer_onemsiz_sayisi"]}


@router.get("/degerlendirme")
def degerlendirme(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Kullanıcı etiketli alarm dönemleri üzerinden kesinlik (precision) = TP / (TP + FP)
    [FAWCETT2006], %95 Clopper–Pearson aralığıyla [CLOPPER_PEARSON1934].
    Kaçırılan krizler (FN) sistemce bilinemediği için duyarlılık hesaplanmaz."""
    sonuc = []
    for seviye in (2, 3):
        q = db.query(Alarm).filter(Alarm.kurum_id == k.id, Alarm.max_seviye >= seviye, Alarm.geri_bildirim.isnot(None))
        tp = q.filter(Alarm.geri_bildirim == "gercek_kriz").count()
        fp = q.filter(Alarm.geri_bildirim == "yanlis_alarm").count()
        n = tp + fp
        if n:
            alt = 0.0 if tp == 0 else float(beta.ppf(0.025, tp, n - tp + 1))
            ust = 1.0 if tp == n else float(beta.ppf(0.975, tp + 1, n - tp))
        sonuc.append({"min_seviye": seviye, "etiket": RISK_SEVIYE_ETIKETLERI[seviye], "dogru_alarm": tp, "yanlis_alarm": fp,
                      "kesinlik": tp / n if n else None, "guven_araligi_95": [alt, ust] if n else None})
    return {"seviyeler": sonuc, "kaynaklar": ["FAWCETT2006", "CLOPPER_PEARSON1934"]}


# ---------------------------------------------------------------------------
# E-postadaki bağlantıdan geri bildirim (oturumsuz; imzalı ve süreli belirteç)
# ---------------------------------------------------------------------------
def _token_coz(token: str, db: Session) -> Alarm:
    try:
        p = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(400, "Bağlantı geçersiz ya da süresi dolmuş")
    if p.get("amac") != "geri_bildirim":
        raise HTTPException(400, "Bağlantı geçersiz")
    a = db.query(Alarm).filter(Alarm.id == p.get("alarm"), Alarm.kurum_id == p.get("kurum")).first()
    if a is None:
        raise HTTPException(404, "Alarm bulunamadı")
    return a


class EpostaGeriBildirim(BaseModel):
    token: str = Field(min_length=10)
    karar: Literal["gercek_kriz", "onemsiz"]
    not_metni: str = ""


@acik_router.get("/onizle")
@limiter.limit(GIRIS_LIMITI)
def onizle(request: Request, token: str, db: Session = Depends(get_db)):
    """Onay sayfası için alarm özeti (etiketi değiştirmez)."""
    a = _token_coz(token, db)
    k = db.get(Kullanici, a.kurum_id)
    return {"kurum": k.kurum, **alarm_servisi.alarm_ozeti(a)}


@acik_router.post("/e-posta")
@limiter.limit(GIRIS_LIMITI)
def eposta_ile(request: Request, g: EpostaGeriBildirim, db: Session = Depends(get_db)):
    a = _token_coz(g.token, db)
    deger = alarm_servisi.normalize_geri_bildirim(g.karar)
    ozet = alarm_servisi.geri_bildirim_isle(db, a, deger, g.not_metni, kaynak="eposta")
    db.commit()
    return {"kurum": db.get(Kullanici, a.kurum_id).kurum, **alarm_servisi.alarm_ozeti(a),
            "benzer_onemsiz_sayisi": ozet["benzer_onemsiz_sayisi"]}
