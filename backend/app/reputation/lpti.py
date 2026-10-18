"""
L-PTİ (Literatür-Temelli Paydaş İtibar Endeksi) — SAF HESAP ("L-PTİ İtibar Skoru Hesaplama Raporu" Bölüm 5–8).

Veritabanı bilmez. Denklem numaraları raporundur:
  (1) POMP u = (x−L)/(U−L) [COHEN1999; MOELLER2015]      (2) ters madde u' = 1−u
  (3) katılımcı puanı p_j = ortalama(u_jk), |K_j| ≥ m [MAZZA2015]
  (4) LPTI_g = 100·Σ r_j p_j / Σ r_j
  (5) n_eff = (Σr)²/Σr², deff_Kish = n/n_eff [VALLIANT2018]
  (6) V̂ = n/(n−1)·Σ r_j²(p_j−p̄)²/(Σr)²; SE = 100√V̂; %95 GA = LPTI ± 1,96 SE [LUMLEY2004]
  (7) status kodları · (8) kurum geneli skor Σπ_g LPTI_g, V = Σπ_g² V_g
  (9) sürücü karnesi · Bölüm 8: Δ = LPTI_t − LPTI_{t−1}
Skor bir olasılık değildir; veri yoksa skor yoktur (score=None) — hiçbir durumda 50 varsayılanı basılmaz.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

Z95 = 1.96


class ScoreStatus(StrEnum):
    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"
    INVALID_INSTRUMENT = "invalid_instrument"
    INVARIANCE_NOT_ESTABLISHED = "invariance_not_established"


@dataclass(frozen=True)
class ItemSpec:
    code: str
    scale_min: float
    scale_max: float
    reverse: bool = False


def normalize(x: float, item: ItemSpec) -> float:
    """Denklem (1)–(2): POMP dönüşümü ve ters madde."""
    if item.scale_max <= item.scale_min:
        raise ValueError("Geçersiz ölçek uçları")
    if not item.scale_min <= x <= item.scale_max:
        raise ValueError("Yanıt ölçek dışında")
    u = (x - item.scale_min) / (item.scale_max - item.scale_min)
    return 1.0 - u if item.reverse else u


def respondent_score(us: Sequence[Optional[float]], m: int) -> Optional[float]:
    """Denklem (3): geçerli madde sayısı m'nin altındaysa None."""
    valid = [u for u in us if u is not None]
    return sum(valid) / len(valid) if len(valid) >= m else None


def kish_n_eff(r: Sequence[float]) -> float:
    """Denklem (5): n_eff = (Σr)²/Σr²."""
    s = sum(r)
    return s * s / sum(w * w for w in r)


def gereken_n_eff(pilot_sd: float, half_width: float) -> float:
    """K3: n_eff ≥ (1,96·σ/E)²  (σ: 0–100 ölçeğinde pilot standart sapma)."""
    return (Z95 * pilot_sd / half_width) ** 2


def group_score(p: Sequence[float], r: Sequence[float], z: float = Z95, max_half_width: float = 5.0,
                min_neff: Optional[float] = None) -> dict:
    """Denklem (4)–(7): ağırlıklı grup skoru, n_eff, SE, %95 GA ve durum.
    Tek aşamalı iadeli örnekleme varyansıdır; tabakalı/kümeli tasarımda tasarıma uygun yordam gerekir."""
    if any(w <= 0 for w in r):
        raise ValueError("Ağırlıklar pozitif olmalı")
    if len(p) != len(r):
        raise ValueError("p ve r uzunlukları farklı")
    n = len(p)
    if n == 0:
        return {"score": None, "estimate": None, "se": None, "ci95": None, "n": 0, "n_eff": None,
                "status": ScoreStatus.INSUFFICIENT_DATA, "reason": "no_valid_respondents"}
    if n < 2:
        return {"score": None, "estimate": 100 * p[0], "se": None, "ci95": None, "n": n, "n_eff": 1.0,
                "status": ScoreStatus.INSUFFICIENT_DATA, "reason": "fewer_than_2_respondents"}
    S = sum(r)
    mean = sum(pi * wi for pi, wi in zip(p, r)) / S
    n_eff = kish_n_eff(r)
    var = n / (n - 1) * sum((w * (pi - mean)) ** 2 for pi, w in zip(p, r)) / S ** 2
    se = 100 * math.sqrt(var)
    half = z * se
    reason = None
    status = ScoreStatus.OK
    if min_neff is not None and n_eff < min_neff:
        status, reason = ScoreStatus.INSUFFICIENT_DATA, "neff_below_minimum"
    elif half > max_half_width:
        status, reason = ScoreStatus.INSUFFICIENT_DATA, "ci_half_width_exceeds_target"
    return {"score": round(100 * mean, 1) if status == ScoreStatus.OK else None,
            "estimate": 100 * mean, "se": se, "ci95": (100 * mean - half, 100 * mean + half),
            "n": n, "n_eff": n_eff, "deff_kish": n / n_eff, "status": status, "reason": reason}


def kurum_geneli(gruplar: Mapping[str, dict], pi: Optional[Mapping[str, float]], z: float = Z95) -> dict:
    """Denklem (8): π_g tanımsızsa, Σπ ≠ 1 ise ya da gerekli gruplardan biri 'ok' değilse skor None (K4)."""
    bos = {"score": None, "estimate": None, "se": None, "ci95": None, "reason": None}
    if not pi:
        return {**bos, "reason": "pi_undefined"}
    if abs(sum(pi.values()) - 1.0) > 1e-9 or any(v < 0 for v in pi.values()):
        return {**bos, "reason": "pi_does_not_sum_to_one"}
    gerekli = [g for g, v in pi.items() if v > 0]
    for g in gerekli:
        sonuc = gruplar.get(g)
        if sonuc is None or sonuc["status"] != ScoreStatus.OK:
            return {**bos, "reason": f"required_group_not_ok:{g}"}
    est = sum(pi[g] * gruplar[g]["estimate"] for g in gerekli)
    var = sum(pi[g] ** 2 * gruplar[g]["se"] ** 2 for g in gerekli)         # bağımsız gruplar
    se = math.sqrt(var)
    return {"score": round(est, 1), "estimate": est, "se": se, "ci95": (est - z * se, est + z * se), "reason": None}


def delta(simdi: Mapping, onceki: Mapping, cov: float = 0.0, z: float = Z95) -> Optional[dict]:
    """Bölüm 8: Δ = LPTI_t − LPTI_{t−1}; SE(Δ) = √(SE_t² + SE_{t−1}² − 2·Cov). GA örtüşmesine bakılmaz."""
    if simdi.get("estimate") is None or onceki.get("estimate") is None or simdi.get("se") is None or onceki.get("se") is None:
        return None
    d = simdi["estimate"] - onceki["estimate"]
    se = math.sqrt(max(simdi["se"] ** 2 + onceki["se"] ** 2 - 2 * cov, 0.0))
    return {"delta": d, "se": se, "ci95": (d - z * se, d + z * se), "anlamli": bool(se > 0 and abs(d) > z * se)}


def onceki_itibar_etiketi(status: str, ci95: Optional[Sequence[float]]) -> Optional[str]:
    """K5: %95 GA tamamen 50'nin üstündeyse olumlu, tamamen altındaysa olumsuz, 50'yi kapsıyorsa nötr;
    status ≠ ok ise None (ısınma dönemi yoluna dönülür)."""
    if str(status) != ScoreStatus.OK.value or not ci95:
        return None
    lo, hi = ci95
    if lo > 50:
        return "olumlu"
    if hi < 50:
        return "olumsuz"
    return "notr"


def puanlama_ozeti_hash(maddeler: Iterable[ItemSpec | Mapping]) -> str:
    """Madde uçları, yönü, yapısı ve sürücü atamasından değişmez özet (scoring_spec_hash)."""
    satirlar = []
    for m in maddeler:
        if isinstance(m, ItemSpec):
            satirlar.append([m.code, m.scale_min, m.scale_max, m.reverse, "", ""])
        else:
            satirlar.append([m["code"], m["scale_min"], m["scale_max"], bool(m.get("reverse", False)),
                             m.get("construct", ""), m.get("driver") or ""])
    satirlar.sort(key=lambda s: s[0])
    return hashlib.sha256(json.dumps(satirlar, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Ağırlıklandırma: raking (iteratif oransal uydurma) [MERCER2018]
# ---------------------------------------------------------------------------
def raking(agirlik: Sequence[float], kategoriler: Sequence[Mapping[str, str]], hedefler: Mapping[str, Mapping[str, float]],
           kirpma: Optional[tuple[float, float]] = None, max_iter: int = 200, tol: float = 1e-9) -> list[float]:
    """Ağırlıklı marjinal payları hedef paylara eşitler. hedefler: {değişken: {kategori: pay}} (payların toplamı
    örnekte gözlenen kategoriler üzerinden yeniden ölçeklenir). kirpma=(alt, üst): ortalama ağırlığın katı."""
    w = np.array(agirlik, dtype=float)
    n = len(w)
    if n == 0:
        return []
    for _ in range(max_iter):
        onceki = w.copy()
        for degisken, hedef in hedefler.items():
            var_kat = [k.get(degisken) for k in kategoriler]
            gozlenen = {c for c in var_kat if c is not None and hedef.get(c, 0) > 0}
            top = sum(hedef[c] for c in gozlenen)
            if not gozlenen or top <= 0:
                continue
            toplam_w = w.sum()
            for c in gozlenen:
                idx = np.array([kk == c for kk in var_kat])
                mevcut = w[idx].sum() / toplam_w
                if mevcut > 0:
                    w[idx] *= (hedef[c] / top) / mevcut
        if kirpma is not None:
            ort = w.mean()
            w = np.clip(w, kirpma[0] * ort, kirpma[1] * ort)
        w *= n / w.sum()
        if np.max(np.abs(w - onceki)) < tol:
            break
    return [float(v) for v in w]


# ---------------------------------------------------------------------------
# Yaklaşık güvenirlik (K10): Pearson korelasyonuna dayalı tek faktörlü ω — kategorik ω'nun yerine geçmez
# ---------------------------------------------------------------------------
def omega_pearson(satirlar: Sequence[Sequence[float]], min_gozlem: int = 30) -> Optional[float]:
    """Eksiksiz gözlemli satırlardan tek faktörlü (temel eksen) ω = (Σλ)²/((Σλ)² + Σ(1−λ²)) [FLORA2020; MCNEISH2018]."""
    X = np.array([s for s in satirlar if all(v is not None for v in s)], dtype=float)
    if X.ndim != 2 or X.shape[0] < min_gozlem or X.shape[1] < 3:
        return None
    if np.any(X.std(axis=0) == 0):
        return None
    R = np.corrcoef(X, rowvar=False)
    try:
        h2 = 1.0 - 1.0 / np.diag(np.linalg.inv(R))
    except np.linalg.LinAlgError:
        return None
    h2 = np.clip(h2, 0.05, 0.995)
    lam = np.sqrt(h2)
    for _ in range(500):
        Rr = R.copy()
        np.fill_diagonal(Rr, h2)
        vals, vecs = np.linalg.eigh(Rr)
        v = vecs[:, -1] * math.sqrt(max(vals[-1], 1e-12))
        v = v if v.sum() >= 0 else -v
        yeni = np.clip(v ** 2, 0.05, 0.995)
        if np.max(np.abs(yeni - h2)) < 1e-8:
            h2, lam = yeni, np.abs(v)
            break
        h2, lam = yeni, np.abs(v)
    lam = np.clip(lam, 0, 0.9975)
    pay = lam.sum() ** 2
    return float(pay / (pay + np.sum(1 - lam ** 2)))
