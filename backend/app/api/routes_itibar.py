"""L-PTİ itibar skoru uçları (Rapor Bölüm 10.3 + yönetim uçları). Veri yoksa skor yoktur (null)."""
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.katalog.lpti import LPTI_KARARLARI
from app.models.orm import (ItibarArac, ItibarDalga, ItibarDogrulama, ItibarKosu, Kullanici, NufusMarji, PaydasYaniti)
from app.reputation import servis

router = APIRouter(prefix="/api/reputation", tags=["itibar"])


class MaddeGirdi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    item_code: str = Field(min_length=1, max_length=40)
    yapi: Literal["pulse", "driver"] = Field(alias="construct")     # API adı 'construct' (Rapor 10.1)
    driver: Optional[str] = None
    wording: str = ""
    reverse: bool = False
    scale_min: float
    scale_max: float


class AracGirdi(BaseModel):
    name: str
    version: str
    language: str = "tr"
    license_status: Literal["dogrulanmadi", "lisansli", "serbest"] = "dogrulanmadi"
    source_citations: list[str] = Field(default_factory=list)
    aciklama: str = ""
    maddeler: list[MaddeGirdi]


class DogrulamaGirdi(BaseModel):
    cfa_supports_one_factor: bool
    stakeholder_group: Optional[str] = None
    estimator: str = ""
    omega: Optional[float] = None
    cfa_fit: dict[str, Any] = Field(default_factory=dict)
    dfi_cutoffs: dict[str, Any] = Field(default_factory=dict)
    invariance_level: Optional[Literal["configural", "metric", "scalar", "partial_scalar", "strict"]] = None
    not_metni: str = ""


class DalgaGirdi(BaseModel):
    instrument_id: int
    name: str = ""
    sampling_frame: str = ""
    mode: str = ""
    familiarity_min: Optional[int] = None
    status: Literal["taslak", "acik", "kapali"] = "acik"


class YanitGirdi(BaseModel):
    respondent_id: str
    group: str
    language: str = "tr"
    familiarity: Optional[float] = None
    familiarity_eligible: Optional[bool] = None
    design_weight: float = 1.0
    nonresponse_weight: float = 1.0
    final_weight: Optional[float] = None
    strata: dict[str, str] = Field(default_factory=dict)
    answers: dict[str, Any]


class MarjGirdi(BaseModel):
    stakeholder_group: str
    stratum: str = Field(pattern=r"^[^=]+=[^=]+$")
    population_share: float = Field(gt=0, le=1)
    source: str = ""


class KosuGirdi(BaseModel):
    min_items: int = Field(default=3, ge=1)                    # K2
    precision_target: float = Field(default=5.0, gt=0)         # K3: hedef GA yarı genişliği E
    pilot_sd: Optional[float] = Field(default=None, gt=0)      # K3: pilot σ (0–100)
    pi: Optional[dict[str, float]] = None                      # K4
    dogrulama_zorunlu: bool = True                             # K9
    agirlik_kirpma: Optional[tuple[float, float]] = None       # K6/K14


def _arac(db: Session, k: Kullanici, aid: int) -> ItibarArac:
    a = db.query(ItibarArac).filter_by(id=aid, kurum_id=k.id).first()
    if a is None:
        raise HTTPException(404, "Araç bulunamadı")
    return a


def _dalga(db: Session, k: Kullanici, wid: int) -> ItibarDalga:
    d = db.query(ItibarDalga).filter_by(id=wid, kurum_id=k.id).first()
    if d is None:
        raise HTTPException(404, "Dalga bulunamadı")
    return d


def _son_kosu(db: Session, wid: int) -> ItibarKosu:
    r = db.query(ItibarKosu).filter_by(wave_id=wid).order_by(ItibarKosu.id.desc()).first()
    if r is None:
        raise HTTPException(404, "Bu dalga için puanlama çalıştırılmadı (POST /waves/{id}/score-runs)")
    return r


def _arac_ozet(a: ItibarArac) -> dict:
    return {"id": a.id, "name": a.name, "version": a.version, "language": a.language, "license_status": a.license_status,
            "source_citations": a.source_citations, "scoring_spec_hash": a.scoring_spec_hash, "aciklama": a.aciklama,
            "maddeler": [{"item_code": m.item_code, "construct": m.construct, "driver": m.driver, "wording": m.wording,
                          "reverse": m.reverse, "scale_min": m.scale_min, "scale_max": m.scale_max} for m in a.maddeler]}


@router.get("/kararlar")
def kararlar():
    return LPTI_KARARLARI


@router.get("/instruments")
def araclar(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    return [_arac_ozet(a) for a in db.query(ItibarArac).filter_by(kurum_id=k.id).order_by(ItibarArac.id.desc()).all()]


@router.post("/instruments", status_code=201)
def arac_ekle(g: AracGirdi, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    try:
        a = servis.arac_olustur(db, k.id, name=g.name, version=g.version, language=g.language, license_status=g.license_status,
                                source_citations=g.source_citations, aciklama=g.aciklama,
                                maddeler=[m.model_dump(by_alias=True) for m in g.maddeler])
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return _arac_ozet(a)


@router.post("/instruments/{aid}/validations", status_code=201)
def dogrulama(aid: int, g: DogrulamaGirdi, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    """Harici CFA/ω/değişmezlik sonucunu araç sürümünün GÜNCEL puanlama özetiyle kaydeder (K9–K11)."""
    a = _arac(db, k, aid)
    d = servis.dogrulama_ekle(db, a, **g.model_dump(), kaynak="harici")
    db.commit()
    return {"id": d.id, "scoring_spec_hash": d.scoring_spec_hash, "cfa_supports_one_factor": d.cfa_supports_one_factor}


@router.get("/waves")
def dalgalar(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    sonuc = []
    for d in db.query(ItibarDalga).filter_by(kurum_id=k.id).order_by(ItibarDalga.id.desc()).all():
        kosu = db.query(ItibarKosu).filter_by(wave_id=d.id).order_by(ItibarKosu.id.desc()).first()
        sonuc.append({"id": d.id, "name": d.name, "instrument_id": d.instrument_id, "status": d.status,
                      "start_at": d.start_at.isoformat() if d.start_at else None, "end_at": d.end_at.isoformat() if d.end_at else None,
                      "yanit_sayisi": db.query(PaydasYaniti).filter_by(wave_id=d.id).count(),
                      "son_kosu": kosu.id if kosu else None, "overall_score": kosu.sonuc.get("overall_score") if kosu else None})
    return sonuc


@router.post("/waves", status_code=201)
def dalga_ekle(g: DalgaGirdi, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    _arac(db, k, g.instrument_id)
    d = ItibarDalga(kurum_id=k.id, **g.model_dump())
    db.add(d)
    db.commit()
    return {"id": d.id}


@router.post("/waves/{wid}/responses")
def yanit_ekle(wid: int, kayitlar: list[YanitGirdi], k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    d = _dalga(db, k, wid)
    s = servis.yanit_aktar(db, d, [x.model_dump() for x in kayitlar])
    db.commit()
    return s


@router.post("/waves/{wid}/responses/csv")
async def yanit_csv(wid: int, dosya: UploadFile = File(...), k: Kullanici = Depends(gecerli_kullanici_al),
                    db: Session = Depends(get_db)):
    d = _dalga(db, k, wid)
    icerik = (await dosya.read(5_000_000)).decode("utf-8-sig", errors="replace")
    try:
        kayitlar = servis.csv_ayristir(icerik)
    except ValueError as e:
        raise HTTPException(422, f"CSV okunamadı: {e}")
    s = servis.yanit_aktar(db, d, kayitlar)
    db.commit()
    return s


@router.post("/waves/{wid}/margins", status_code=201)
def marj_ekle(wid: int, marjlar: list[MarjGirdi], k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    _dalga(db, k, wid)
    for m in marjlar:
        db.add(NufusMarji(wave_id=wid, **m.model_dump()))
    db.commit()
    return {"eklenen": len(marjlar)}


@router.post("/waves/{wid}/score-runs", status_code=201)
def puanla(wid: int, g: KosuGirdi = KosuGirdi(), k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    d = _dalga(db, k, wid)
    try:
        kosu = servis.kosu_calistir(db, d, **g.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return kosu.sonuc


@router.get("/waves/{wid}/scores")
def skorlar(wid: int, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    _dalga(db, k, wid)
    s = _son_kosu(db, wid).sonuc
    return {kk: s[kk] for kk in ("construct", "model", "instrument_version", "wave_id", "run_id", "params", "overall_score",
                                 "overall", "stakeholder_scores", "comparison")} | {"quality": {
        "invariance_level": s["quality"]["invariance_level"], "missing_rate": s["quality"]["missing_rate"]}}


@router.get("/waves/{wid}/drivers")
def surucular(wid: int, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    _dalga(db, k, wid)
    s = _son_kosu(db, wid).sonuc
    return {"run_id": s["run_id"], "drivers": s["drivers"],
            "not": "Sürücüler ana skora toplanmaz; önem ağırlıkları paydaşa ve pazara göre değişir (RepTrak 2026)."}


@router.get("/waves/{wid}/quality")
def kalite(wid: int, k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    _dalga(db, k, wid)
    s = _son_kosu(db, wid).sonuc
    return {"run_id": s["run_id"], "quality": s["quality"]}


