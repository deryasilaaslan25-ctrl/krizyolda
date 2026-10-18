"""
L-PTİ servis katmanı: araç/dalga/yanıt yönetimi, puanlama çalıştırması (Rapor Bölüm 5, 7, 8, 10), doğrulama kapısı (K9),
değişmezlik (K11), önceki_itibar etiketi (K5, K12, K13).
"""
from __future__ import annotations

import csv
import io
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from sqlalchemy.orm import Session

from app.models.orm import (ItibarArac, ItibarCevap, ItibarDalga, ItibarDogrulama, ItibarKosu, ItibarMadde,
                            ItibarSkor, ItibarSurucuSkor, Kullanici, NufusMarji, OlcumKalitesi, PaydasYaniti)
from app.reputation import lpti
from app.reputation.lpti import ItemSpec, ScoreStatus

MODEL_SURUMU = "L-PTI-1.0"
SURUCULER = ["products_services", "innovation", "workplace", "conduct", "citizenship", "leadership", "performance"]
SURUCU_ADLARI = {"products_services": "Ürün ve hizmetler", "innovation": "Yenilik", "workplace": "İşyeri",
                 "conduct": "Davranış / yönetişim", "citizenship": "Vatandaşlık", "leadership": "Liderlik",
                 "performance": "Performans"}
VARSAYILAN_GRUPLAR = ["customers", "employees", "investors", "suppliers_regulators", "general_public"]
DEGISMEZLIK_YETERLI = {"scalar", "partial_scalar", "strict"}
DONT_KNOW = {"dont_know", "dk", "emin degilim", "emin değilim", "bilmiyorum"}


def _simdi() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Araç
# ---------------------------------------------------------------------------
def madde_ozetleri(arac: ItibarArac) -> list[dict]:
    return [{"code": m.item_code, "scale_min": m.scale_min, "scale_max": m.scale_max, "reverse": bool(m.reverse),
             "construct": m.construct, "driver": m.driver} for m in arac.maddeler]


def arac_hash(arac: ItibarArac) -> str:
    return lpti.puanlama_ozeti_hash(madde_ozetleri(arac))


def arac_olustur(db: Session, kurum_id: int, *, name: str, version: str, language: str = "tr", license_status: str = "dogrulanmadi",
                 source_citations: Sequence[str] = (), aciklama: str = "", maddeler: Sequence[Mapping[str, Any]]) -> ItibarArac:
    if not maddeler:
        raise ValueError("En az bir madde gerekli")
    kodlar = [m["item_code"] for m in maddeler]
    if len(kodlar) != len(set(kodlar)):
        raise ValueError("Yinelenen madde kodu")
    a = ItibarArac(kurum_id=kurum_id, name=name, version=version, language=language, license_status=license_status,
                   source_citations=list(source_citations), aciklama=aciklama)
    for m in maddeler:
        if m["construct"] not in ("pulse", "driver"):
            raise ValueError("construct: pulse | driver")
        if m["construct"] == "driver" and not m.get("driver"):
            raise ValueError(f"{m['item_code']}: sürücü maddesi için driver gerekli")
        if float(m["scale_max"]) <= float(m["scale_min"]):
            raise ValueError(f"{m['item_code']}: geçersiz ölçek uçları")
        a.maddeler.append(ItibarMadde(construct=m["construct"], driver=m.get("driver"), item_code=m["item_code"],
                                      wording=m.get("wording", ""), reverse=bool(m.get("reverse", False)),
                                      scale_min=float(m["scale_min"]), scale_max=float(m["scale_max"])))
    if not any(m["construct"] == "pulse" for m in maddeler):
        raise ValueError("En az bir Pulse maddesi gerekli")
    db.add(a)
    db.flush()
    a.scoring_spec_hash = arac_hash(a)
    return a


def dogrulama_ekle(db: Session, arac: ItibarArac, *, cfa_supports_one_factor: bool, stakeholder_group: Optional[str] = None,
                   estimator: str = "", omega: Optional[float] = None, cfa_fit: Optional[dict] = None,
                   dfi_cutoffs: Optional[dict] = None, invariance_level: Optional[str] = None, kaynak: str = "harici",
                   not_metni: str = "") -> ItibarDogrulama:
    if invariance_level not in (None, "configural", "metric", "scalar", "partial_scalar", "strict"):
        raise ValueError("invariance_level geçersiz")
    d = ItibarDogrulama(instrument_id=arac.id, stakeholder_group=stakeholder_group, scoring_spec_hash=arac_hash(arac),
                        cfa_supports_one_factor=cfa_supports_one_factor, estimator=estimator, omega=omega,
                        cfa_fit=cfa_fit or {}, dfi_cutoffs=dfi_cutoffs or {}, invariance_level=invariance_level,
                        kaynak=kaynak, not_metni=not_metni)
    db.add(d)
    db.flush()
    return d


def gecerli_dogrulama(db: Session, arac: ItibarArac, grup: Optional[str]) -> tuple[Optional[ItibarDogrulama], str]:
    """Aracın GÜNCEL puanlama özetiyle eşleşen en son doğrulama kaydı. (kayıt, neden)."""
    h = arac_hash(arac)
    kayitlar = (db.query(ItibarDogrulama).filter(ItibarDogrulama.instrument_id == arac.id)
                .order_by(ItibarDogrulama.id.desc()).all())
    if not kayitlar:
        return None, "instrument_not_validated"
    uygun = [d for d in kayitlar if d.stakeholder_group in (None, grup)]
    if not uygun:
        return None, "instrument_not_validated_for_group"
    guncel = [d for d in uygun if d.scoring_spec_hash == h]
    if not guncel:
        return None, "item_spec_changed_since_validation"
    en_iyi = sorted(guncel, key=lambda d: (d.stakeholder_group == grup, d.id), reverse=True)[0]
    if not en_iyi.cfa_supports_one_factor:
        return en_iyi, "cfa_does_not_support_single_factor"
    return en_iyi, ""


# ---------------------------------------------------------------------------
# Yanıt içe aktarma (Adım 0)
# ---------------------------------------------------------------------------
def _deger(v: Any) -> tuple[Optional[float], Optional[str]]:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, "skipped"
    if isinstance(v, str) and v.strip().lower() in DONT_KNOW:
        return None, "dont_know"
    return float(v), None


def yanit_aktar(db: Session, dalga: ItibarDalga, kayitlar: Sequence[Mapping[str, Any]]) -> dict:
    """Katılımcı kayıtlarını içe aktarır. 'Emin değilim' eksik olarak saklanır (orta nokta değil); ölçek dışı değer reddedilir."""
    arac = db.get(ItibarArac, dalga.instrument_id)
    maddeler = {m.item_code: m for m in arac.maddeler}
    hatalar: list[str] = []
    eklenen = 0
    for i, k in enumerate(kayitlar, start=1):
        rid = str(k.get("respondent_id") or k.get("respondent_pseudo_id") or "").strip()
        grup = str(k.get("group") or k.get("stakeholder_group") or "").strip()
        if not rid or not grup:
            hatalar.append(f"satır {i}: respondent_id ve group gerekli")
            continue
        if db.query(PaydasYaniti).filter_by(wave_id=dalga.id, respondent_pseudo_id=rid).first():
            hatalar.append(f"satır {i}: {rid} zaten var")
            continue
        cevaplar, gecersiz = [], False
        for kod, ham in (k.get("answers") or {}).items():
            m = maddeler.get(kod)
            if m is None:
                hatalar.append(f"satır {i}: bilinmeyen madde {kod}")
                gecersiz = True
                continue
            try:
                deger, neden = _deger(ham)
            except (TypeError, ValueError):
                hatalar.append(f"satır {i}: {kod} sayısal değil")
                gecersiz = True
                continue
            if deger is not None and not (m.scale_min <= deger <= m.scale_max):
                hatalar.append(f"satır {i}: {kod}={deger} ölçek dışı [{m.scale_min}, {m.scale_max}]")
                gecersiz = True
                continue
            norm = lpti.normalize(deger, ItemSpec(m.item_code, m.scale_min, m.scale_max, m.reverse)) if deger is not None else None
            cevaplar.append((m, deger, norm, neden))
        if gecersiz:
            continue
        gorulen = {m.item_code for m, *_ in cevaplar}
        for kod, m in maddeler.items():
            if kod not in gorulen:
                cevaplar.append((m, None, None, "skipped"))
        fam = k.get("familiarity")
        uygun = k.get("familiarity_eligible")
        if uygun is None:
            uygun = True if fam is None or dalga.familiarity_min is None else float(fam) >= dalga.familiarity_min
        y = PaydasYaniti(wave_id=dalga.id, respondent_pseudo_id=rid, stakeholder_group=grup, language=k.get("language", "tr"),
                         familiarity=float(fam) if fam is not None else None, familiarity_eligible=bool(uygun),
                         design_weight=float(k.get("design_weight", 1.0)), nonresponse_weight=float(k.get("nonresponse_weight", 1.0)),
                         final_weight=float(k["final_weight"]) if k.get("final_weight") is not None else None,
                         strata=k.get("strata") or {})
        db.add(y)
        db.flush()
        for m, deger, norm, neden in cevaplar:
            db.add(ItibarCevap(response_id=y.id, item_id=m.id, raw_value=deger, normalized_value=norm, missing_reason=neden))
        eklenen += 1
    return {"eklenen": eklenen, "hatalar": hatalar}


def csv_ayristir(icerik: str) -> list[dict]:
    """Sütunlar: respondent_id, group, language, familiarity, design_weight, nonresponse_weight, final_weight,
    strata_<değişken>, geri kalanı madde kodu. Boş hücre = atlandı; 'dk' = emin değilim."""
    ayrac = ";" if icerik.split("\n", 1)[0].count(";") > icerik.split("\n", 1)[0].count(",") else ","
    okuyucu = csv.DictReader(io.StringIO(icerik), delimiter=ayrac)
    sabit = {"respondent_id", "group", "language", "familiarity", "familiarity_eligible", "design_weight",
             "nonresponse_weight", "final_weight"}
    kayitlar = []
    for satir in okuyucu:
        k: dict[str, Any] = {"answers": {}, "strata": {}}
        for ad, v in satir.items():
            if ad is None:
                continue
            ad = ad.strip()
            v = (v or "").strip().replace(",", ".") if ad in ("familiarity", "design_weight", "nonresponse_weight", "final_weight") else (v or "").strip()
            if ad in sabit:
                if ad in ("familiarity", "design_weight", "nonresponse_weight", "final_weight"):
                    if v:
                        k[ad] = float(v)
                elif ad == "familiarity_eligible":
                    if v:
                        k[ad] = v.lower() in ("1", "true", "evet", "e")
                elif v:
                    k[ad] = v
            elif ad.startswith("strata_"):
                if v:
                    k["strata"][ad[7:]] = v
            else:
                k["answers"][ad] = v.replace(",", ".") if v.lower() not in DONT_KNOW else "dont_know"
        kayitlar.append(k)
    return kayitlar


# ---------------------------------------------------------------------------
# Puanlama çalıştırması
# ---------------------------------------------------------------------------
def _liste(x):
    return list(x) if x is not None else None


def _sade(sozluk: dict) -> dict:
    """JSON'a yazılabilir hale getirir (enum, tuple)."""
    c = {}
    for k, v in sozluk.items():
        if isinstance(v, ScoreStatus):
            v = v.value
        elif isinstance(v, tuple):
            v = list(v)
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            v = None
        c[k] = v
    return c


def _marjlar(db: Session, dalga_id: int, grup: str) -> dict[str, dict[str, float]]:
    hedef: dict[str, dict[str, float]] = {}
    for m in db.query(NufusMarji).filter(NufusMarji.wave_id == dalga_id, NufusMarji.stakeholder_group == grup).all():
        if "=" not in m.stratum:
            continue
        d, c = m.stratum.split("=", 1)
        hedef.setdefault(d.strip(), {})[c.strip()] = m.population_share
    return hedef


def kosu_calistir(db: Session, dalga: ItibarDalga, *, min_items: int = 3, precision_target: float = 5.0,
                  pilot_sd: Optional[float] = None, pi: Optional[Mapping[str, float]] = None,
                  dogrulama_zorunlu: bool = True, agirlik_kirpma: Optional[tuple[float, float]] = None,
                  code_commit: str = "") -> ItibarKosu:
    arac = db.get(ItibarArac, dalga.instrument_id)
    maddeler = arac.maddeler
    pulse = [m for m in maddeler if m.construct == "pulse"]
    surucu_maddeleri: dict[str, list[ItibarMadde]] = {}
    for m in maddeler:
        if m.construct == "driver":
            surucu_maddeleri.setdefault(m.driver, []).append(m)
    min_neff = lpti.gereken_n_eff(pilot_sd, precision_target) if pilot_sd else None
    yanitlar = db.query(PaydasYaniti).filter_by(wave_id=dalga.id).all()
    cevap_sozluk: dict[int, dict[int, ItibarCevap]] = {y.id: {} for y in yanitlar}
    if yanitlar:
        for c in db.query(ItibarCevap).filter(ItibarCevap.response_id.in_([y.id for y in yanitlar])).all():
            cevap_sozluk[c.response_id][c.item_id] = c
    grup_yanit: dict[str, list[PaydasYaniti]] = {}
    for y in yanitlar:
        grup_yanit.setdefault(y.stakeholder_group, []).append(y)

    kosu = ItibarKosu(wave_id=dalga.id, model_version=MODEL_SURUMU, code_commit=code_commit,
                      weighting_method="final_weight | tasarım×yanıtsızlık×raking", missing_method="proration",
                      ci_method="linearization", min_items=min_items, precision_target=precision_target)
    db.add(kosu)
    db.flush()

    gruplar: dict[str, dict] = {}
    surucu_sonuclari: list[dict] = []
    kalite_satirlari: list[dict] = []
    for grup, rs in sorted(grup_yanit.items()):
        dogr, neden = gecerli_dogrulama(db, arac, grup)
        gecersiz_arac = dogr is None or bool(neden)
        atlanan = {"aşinalık_dışı": 0, "geçersiz_ağırlık": 0, "yetersiz_madde": 0}
        uygun = []
        for y in rs:
            eligible = y.familiarity_eligible
            if dalga.familiarity_min is not None and y.familiarity is not None:
                eligible = y.familiarity >= dalga.familiarity_min           # K1: ön kayıtlı eşik
            if eligible:
                uygun.append(y)
            else:
                atlanan["aşinalık_dışı"] += 1
        # Katılımcı puanları
        satirlar = []
        toplam_cevap, eksik_cevap = 0, 0
        ham_matris = []
        for y in uygun:
            c = cevap_sozluk[y.id]
            us = []
            for m in pulse:
                cv = c.get(m.id)
                u = cv.normalized_value if cv is not None else None
                us.append(u)
                toplam_cevap += 1
                eksik_cevap += 1 if u is None else 0
            ham_matris.append(us)
            pj = lpti.respondent_score(us, min_items)
            if pj is None:
                atlanan["yetersiz_madde"] += 1
                continue
            agirlik = y.final_weight if y.final_weight is not None else (y.design_weight or 1.0) * (y.nonresponse_weight or 1.0)
            if agirlik <= 0:
                atlanan["geçersiz_ağırlık"] += 1
                continue
            satirlar.append((y, pj, c))
        # Ağırlıklar
        w = [(y.final_weight if y.final_weight is not None else (y.design_weight or 1.0) * (y.nonresponse_weight or 1.0))
             for y, _, _ in satirlar]
        hedef = _marjlar(db, dalga.id, grup)
        rake_kullanildi = False
        if hedef and any(y.final_weight is None for y, _, _ in satirlar):
            yeni = lpti.raking(w, [y.strata or {} for y, _, _ in satirlar], hedef, agirlik_kirpma)
            w = [wi if y.final_weight is not None else yi for (y, _, _), wi, yi in zip(satirlar, w, yeni)]
            rake_kullanildi = True
        p = [pj for _, pj, _ in satirlar]
        gs = lpti.group_score(p, w, max_half_width=precision_target, min_neff=min_neff) if satirlar else lpti.group_score([], [])
        bypass = (not dogrulama_zorunlu) and neden in ("instrument_not_validated", "instrument_not_validated_for_group")
        if gecersiz_arac and not bypass:
            gs["status"], gs["reason"], gs["score"] = ScoreStatus.INVALID_INSTRUMENT, neden, None
            gs["estimate"] = gs["se"] = gs["ci95"] = None
        elif gecersiz_arac and bypass and gs["status"] == ScoreStatus.OK:
            gs["reason"] = "instrument_validation_bypassed"
        gs["dislanan"] = atlanan
        gs["aşinalık_dışı_oran"] = atlanan["aşinalık_dışı"] / len(rs) if rs else None
        gs["raking"] = rake_kullanildi
        gruplar[grup] = gs
        # Sürücü karnesi (Adım 9)
        if gs["status"] != ScoreStatus.INVALID_INSTRUMENT:
            for surucu, ms in surucu_maddeleri.items():
                need = min(min_items, len(ms))
                ps, rs_w = [], []
                for (y, _, c), wi in zip(satirlar, w):
                    us = [c[m.id].normalized_value if m.id in c else None for m in ms]
                    q = lpti.respondent_score(us, need)
                    if q is not None:
                        ps.append(q)
                        rs_w.append(wi)
                if ps:
                    sg = lpti.group_score(ps, rs_w, max_half_width=precision_target, min_neff=min_neff)
                    surucu_sonuclari.append({"group": grup, "driver": surucu, "driver_adi": SURUCU_ADLARI.get(surucu, surucu),
                                             **_sade(sg)})
        # Kalite
        tam_satir = [[u for u in s] for s in ham_matris if all(v is not None for v in s)]
        om = lpti.omega_pearson(tam_satir)
        kalite_satirlari.append({
            "group": grup, "omega": om, "estimator": "pearson_paf" if om is not None else "",
            "missing_rate": (eksik_cevap / toplam_cevap) if toplam_cevap else None,
            "cfa_fit": (dogr.cfa_fit if dogr else {}), "dfi_cutoffs": (dogr.dfi_cutoffs if dogr else {}),
            "invariance_level": dogr.invariance_level if dogr else None,
            "harici_omega": dogr.omega if dogr else None, "harici_estimator": dogr.estimator if dogr else "",
            "dogrulama_kaynagi": dogr.kaynak if dogr else None, "dogrulama_durumu": neden or ("ok" if dogr else "yok"),
        })

    kurum_geneli = lpti.kurum_geneli(gruplar, pi) if pi else lpti.kurum_geneli({}, None)
    if any(g["status"] == ScoreStatus.INVALID_INSTRUMENT for g in gruplar.values()):
        kurum_geneli = {"score": None, "estimate": None, "se": None, "ci95": None, "reason": "invalid_instrument"}
    karsilastirma = _karsilastirma(db, dalga, arac, gruplar, kalite_satirlari)
    toplam_eksik = [q["missing_rate"] for q in kalite_satirlari if q["missing_rate"] is not None]

    sonuc = {
        "construct": "corporate_reputation", "model": "L-PTI", "model_version": MODEL_SURUMU,
        "instrument_version": arac.version, "instrument_hash": arac_hash(arac), "wave_id": dalga.id, "run_id": kosu.id,
        "params": {"min_items": min_items, "precision_target": precision_target, "pilot_sd": pilot_sd, "min_neff": min_neff,
                   "pi": dict(pi) if pi else None, "dogrulama_zorunlu": dogrulama_zorunlu},
        "overall_score": kurum_geneli["score"],
        "overall": _sade({**kurum_geneli, "ci95": kurum_geneli.get("ci95")}),
        "stakeholder_scores": [{"group": g, **_sade({k: v for k, v in gs.items() if k != "deff_kish"}),
                                "deff_kish": gs.get("deff_kish")} for g, gs in gruplar.items()],
        "drivers": surucu_sonuclari,
        "quality": {"invariance_level": (kalite_satirlari[0]["invariance_level"] if kalite_satirlari else None),
                    "missing_rate": (sum(toplam_eksik) / len(toplam_eksik)) if toplam_eksik else None,
                    "gruplar": kalite_satirlari,
                    "validation_bypassed": (not dogrulama_zorunlu) and any(q["dogrulama_durumu"] in ("instrument_not_validated", "instrument_not_validated_for_group") for q in kalite_satirlari)},
        "comparison": karsilastirma,
    }
    kosu.sonuc = sonuc
    kosu.params = sonuc["params"]
    kosu.weighting_method = "final_weight | tasarım×yanıtsızlık" + ("×raking" if any(g.get("raking") for g in gruplar.values()) else "")
    for g, gs in gruplar.items():
        db.add(ItibarSkor(run_id=kosu.id, stakeholder_group=g, score=gs["score"], estimate=gs["estimate"], se=gs["se"],
                          ci_low=gs["ci95"][0] if gs["ci95"] else None, ci_high=gs["ci95"][1] if gs["ci95"] else None,
                          n=gs["n"], n_eff=gs["n_eff"], status=str(gs["status"]), reason=gs["reason"]))
    for d in surucu_sonuclari:
        db.add(ItibarSurucuSkor(run_id=kosu.id, stakeholder_group=d["group"], driver=d["driver"], score=d["score"],
                                se=d["se"], ci_low=d["ci95"][0] if d["ci95"] else None, ci_high=d["ci95"][1] if d["ci95"] else None,
                                n=d["n"], n_eff=d["n_eff"]))
    for q in kalite_satirlari:
        db.add(OlcumKalitesi(run_id=kosu.id, group=q["group"], omega=q["omega"], estimator=q["estimator"], cfa_fit=q["cfa_fit"],
                             dfi_cutoffs=q["dfi_cutoffs"], invariance_level=q["invariance_level"],
                             missing_rate=q["missing_rate"], ayrinti={k: v for k, v in q.items() if k.startswith(("harici", "dogrulama"))}))
    db.flush()
    return kosu


def _karsilastirma(db: Session, dalga: ItibarDalga, arac: ItibarArac, gruplar: dict, kalite: list[dict]) -> dict:
    """Bölüm 8 + K11: dalgalar arası Δ yalnız zaman değişmezliği ve aynı puanlama özeti varsa."""
    onceki = None
    for d in (db.query(ItibarDalga).filter(ItibarDalga.kurum_id == dalga.kurum_id, ItibarDalga.id != dalga.id,
                                           ItibarDalga.id < dalga.id).order_by(ItibarDalga.id.desc()).all()):
        a = db.get(ItibarArac, d.instrument_id)
        if arac_hash(a) != arac_hash(arac):
            continue
        k = db.query(ItibarKosu).filter_by(wave_id=d.id).order_by(ItibarKosu.id.desc()).first()
        if k and k.sonuc:
            onceki = (d, k)
            break
    if onceki is None:
        return {"durum": "onceki_dalga_yok", "delta": []}
    seviyeler = {q["invariance_level"] for q in kalite if q["invariance_level"]}
    yeterli = bool(seviyeler) and all(q["invariance_level"] in DEGISMEZLIK_YETERLI for q in kalite)
    if not yeterli:
        return {"durum": str(ScoreStatus.INVARIANCE_NOT_ESTABLISHED), "onceki_dalga": onceki[0].id, "delta": [],
                "neden": "Zaman değişmezliği (≥ skaler/kısmi skaler) doğrulama kaydında yok"}
    onceki_gruplar = {s["group"]: s for s in onceki[1].sonuc.get("stakeholder_scores", [])}
    liste = []
    for g, gs in gruplar.items():
        o = onceki_gruplar.get(g)
        if o and gs["status"] == ScoreStatus.OK and o.get("status") == "ok":
            d = lpti.delta(gs, o)
            if d:
                liste.append({"group": g, **_sade(d)})
    return {"durum": "ok", "onceki_dalga": onceki[0].id, "delta": liste}


# ---------------------------------------------------------------------------
# ERKİS entegrasyonu (K5, K12, K13)
# ---------------------------------------------------------------------------
def onceki_itibar_etiketi(db: Session, k: Kullanici) -> tuple[Optional[str], Optional[dict]]:
    """En son geçerli L-PTİ çalıştırmasından K5 etiketi. Yoksa (None, None) → ısınma Janis–Fadner yoluna dönülür."""
    for dalga in db.query(ItibarDalga).filter(ItibarDalga.kurum_id == k.id).order_by(ItibarDalga.id.desc()).all():
        kosu = db.query(ItibarKosu).filter_by(wave_id=dalga.id).order_by(ItibarKosu.id.desc()).first()
        if not kosu or not kosu.sonuc:
            continue
        s = kosu.sonuc
        if s["overall_score"] is not None and s["overall"].get("ci95"):
            etiket = lpti.onceki_itibar_etiketi("ok", s["overall"]["ci95"])
            return etiket, {"dalga": dalga.id, "kosu": kosu.id, "kaynak": "kurum_geneli", "skor": s["overall_score"],
                            "ci95": s["overall"]["ci95"]}
        ok = [g for g in s["stakeholder_scores"] if g["status"] == "ok" and g.get("ci95")]
        if ok:
            g = max(ok, key=lambda x: x["n_eff"] or 0)
            return lpti.onceki_itibar_etiketi("ok", g["ci95"]), {"dalga": dalga.id, "kosu": kosu.id, "kaynak": f"grup:{g['group']}",
                                                               "skor": g["score"], "ci95": g["ci95"]}
    return None, None
