"""Kimlik doğrulama: kayıt, giriş, e-posta doğrulama, şifre sıfırlama."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import GIRIS_LIMITI, limiter
from app.core.security import gecerli_kullanici_al, sifre_dogrula, sifre_hashle, token_olustur
from app.database import get_db
from app.models.orm import DenetimKaydi, Kullanici
from app.services import bildirim

router = APIRouter(prefix="/api/auth", tags=["kimlik"])


class KayitIstegi(BaseModel):
    email: EmailStr
    sifre: str = Field(min_length=8, max_length=72)
    sifre_tekrar: str
    kurum: str = Field(min_length=2, max_length=255)
    sektor: str = ""
    bildirim_ek_epostalar: list[EmailStr] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def _eslesme(self):
        if self.sifre != self.sifre_tekrar:
            raise ValueError("Şifreler eşleşmiyor")
        return self


class SifreDegistir(BaseModel):
    mevcut_sifre: str
    yeni_sifre: str = Field(min_length=8, max_length=72)


class EmailDegistir(BaseModel):
    yeni_email: EmailStr
    sifre: str


class SifreSifirlaIste(BaseModel):
    email: EmailStr


class SifreSifirla(BaseModel):
    token: str
    yeni_sifre: str = Field(min_length=8, max_length=72)


class TokenIstegi(BaseModel):
    token: str


def kullanici_ozeti(k: Kullanici) -> dict:
    return {"id": k.id, "email": k.email, "kurum": k.kurum, "sektor": k.sektor, "rol": k.rol,
            "eposta_dogrulandi": bool(k.eposta_dogrulandi), "eposta_gonderimi_hazir": bildirim.smtp_yapilandirildi(),
            "izleme_terimleri": k.izleme_terimleri or [], "kriz_gecmisi": k.kriz_gecmisi or [],
            "onceki_itibar": k.onceki_itibar,
            "web_sitesi": k.web_sitesi or "", "resmi_hesaplar": k.resmi_hesaplar or [], "haric_terimler": k.haric_terimler or [],
            "ek_rss": k.ek_rss or [], "acik_kaynak": bool(k.acik_kaynak),
            "aralik_turu": k.aralik_turu or "30",
            "ozel_baslangic": k.ozel_baslangic.date().isoformat() if k.ozel_baslangic else None,
            "ozel_bitis": k.ozel_bitis.date().isoformat() if k.ozel_bitis else None,
            "tekrar_plani": k.tekrar_plani or "periyodik", "tarama_min_dk": k.tarama_min_dk or 15,
            "tarama_max_dk": k.tarama_max_dk or 360, "tarama_aralik_dk": k.tarama_aralik_dk,
            "sonraki_tarama": k.sonraki_tarama.isoformat() if k.sonraki_tarama else None,
            "bildirim_email": bool(k.bildirim_email), "bildirim_slack": bool(k.bildirim_slack),
            "bildirim_min_seviye": k.bildirim_min_seviye or 2, "bildirim_ek_epostalar": k.bildirim_ek_epostalar or [],
            "bildirim_haftalik": bool(k.bildirim_haftalik), "bildirim_bekleme_saat": k.bildirim_bekleme_saat if k.bildirim_bekleme_saat is not None else 6,
            "rapor_gunu": k.rapor_gunu or 0, "rapor_saati": k.rapor_saati if k.rapor_saati is not None else 9,
            "en_fazla_analiz_gun": settings.EN_FAZLA_ANALIZ_GUN}


def _giris_yaniti(k: Kullanici) -> dict:
    return {"access_token": token_olustur({"sub": k.email}), "token_type": "bearer", "kullanici": kullanici_ozeti(k)}


@router.post("/kayit", status_code=201)
@limiter.limit(GIRIS_LIMITI)
def kayit(request: Request, istek: KayitIstegi, db: Session = Depends(get_db)):
    email = istek.email.lower()
    if db.query(Kullanici).filter(Kullanici.email == email).first():
        raise HTTPException(409, "Bu e-posta ile kayıtlı bir hesap var")
    k = Kullanici(email=email, hashed_password=sifre_hashle(istek.sifre), kurum=istek.kurum.strip(), sektor=istek.sektor,
                  rol="yonetici" if email in settings.yonetici_listesi else "kurum",
                  izleme_terimleri=[], kriz_gecmisi=[], bildirim_email=True,
                  bildirim_ek_epostalar=list(dict.fromkeys(e.lower() for e in istek.bildirim_ek_epostalar)),
                  bildirim_min_seviye=2, bildirim_haftalik=True)
    db.add(k)
    db.commit()
    db.refresh(k)
    bildirim.dogrulama_gonder(db, k)
    db.add(DenetimKaydi(kurum_id=k.id, islem="kayit"))
    db.commit()
    return _giris_yaniti(k)


@router.post("/giris")
@limiter.limit(GIRIS_LIMITI)
def giris(request: Request, form: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm), db: Session = Depends(get_db)):
    k = db.query(Kullanici).filter(Kullanici.email == form.username.lower()).first()
    if not k or not sifre_dogrula(form.password, k.hashed_password):
        raise HTTPException(401, "E-posta veya şifre hatalı")
    return _giris_yaniti(k)


@router.get("/ben")
def ben(k: Kullanici = Depends(gecerli_kullanici_al)):
    return kullanici_ozeti(k)


@router.post("/sifre-degistir")
def sifre_degistir(istek: SifreDegistir, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    if not sifre_dogrula(istek.mevcut_sifre, k.hashed_password):
        raise HTTPException(400, "Mevcut şifre hatalı")
    k.hashed_password = sifre_hashle(istek.yeni_sifre)
    db.add(DenetimKaydi(kurum_id=k.id, islem="sifre_degistir"))
    db.commit()
    return {"durum": "tamam"}


@router.post("/email-degistir")
def email_degistir(istek: EmailDegistir, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    if not sifre_dogrula(istek.sifre, k.hashed_password):
        raise HTTPException(400, "Şifre hatalı")
    yeni = istek.yeni_email.lower()
    if db.query(Kullanici).filter(Kullanici.email == yeni, Kullanici.id != k.id).first():
        raise HTTPException(409, "Bu e-posta kullanımda")
    k.email, k.eposta_dogrulandi = yeni, False
    db.add(DenetimKaydi(kurum_id=k.id, islem="email_degistir"))
    db.commit()
    bildirim.dogrulama_gonder(db, k)
    db.commit()
    return _giris_yaniti(k)


def _token(token: str, amac: str) -> dict:
    try:
        p = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(400, "Bağlantı geçersiz ya da süresi dolmuş")
    if p.get("amac") != amac:
        raise HTTPException(400, "Bağlantı geçersiz")
    return p


@router.post("/dogrulama-gonder")
@limiter.limit(GIRIS_LIMITI)
def dogrulama_gonder(request: Request, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    if k.eposta_dogrulandi:
        return {"durum": "zaten_dogrulandi"}
    bildirim.dogrulama_gonder(db, k)
    db.commit()
    return {"durum": "kuyruga_alindi"}


@router.post("/eposta-dogrula")
@limiter.limit(GIRIS_LIMITI)
def eposta_dogrula(request: Request, g: TokenIstegi, db: Session = Depends(get_db)):
    p = _token(g.token, "eposta_dogrula")
    k = db.get(Kullanici, p.get("kurum"))
    if k is None or k.email != p.get("email"):
        raise HTTPException(400, "Bağlantı geçersiz")
    k.eposta_dogrulandi = True
    db.add(DenetimKaydi(kurum_id=k.id, islem="eposta_dogrulandi"))
    db.commit()
    return {"durum": "dogrulandi"}


@router.post("/sifre-sifirla-iste")
@limiter.limit(GIRIS_LIMITI)
def sifre_sifirla_iste(request: Request, g: SifreSifirlaIste, db: Session = Depends(get_db)):
    """Hesap var ya da yok aynı yanıt döner (hesap varlığı sızdırılmaz)."""
    k = db.query(Kullanici).filter(Kullanici.email == g.email.lower()).first()
    if k:
        bildirim.sifre_sifirlama_gonder(db, k)
        db.commit()
    return {"durum": "istek_alindi"}


@router.post("/sifre-sifirla")
@limiter.limit(GIRIS_LIMITI)
def sifre_sifirla(request: Request, g: SifreSifirla, db: Session = Depends(get_db)):
    p = _token(g.token, "sifre_sifirla")
    k = db.get(Kullanici, p.get("kurum"))
    if k is None or k.hashed_password[-8:] != p.get("h"):          # şifre değiştiyse bağlantı tek kullanımlık sayılır
        raise HTTPException(400, "Bağlantı geçersiz ya da daha önce kullanılmış")
    k.hashed_password = sifre_hashle(g.yeni_sifre)
    db.add(DenetimKaydi(kurum_id=k.id, islem="sifre_sifirlandi"))
    db.commit()
    return {"durum": "tamam"}
