"""
Kuruma özgü kriz eşiği — SAF MATEMATİK ("Kuruma Özgü Kriz Eşiği Metodolojisi").

Veritabanı bilmez; app/services/kurum_esik_servisi.py bu işlevleri çağırır. Bölüm numaraları
metodoloji raporunundur.

  Bölüm 2  eşik = normal dönem dağılımının (1 − p_k) yüzdeliği; dönüş süresi D_k = 1/p_k
  Bölüm 3  saatlik blok maksimumu; kirlenmeden arındırma (servis katmanında)
  Bölüm 4  4.1 ampirik yüzdelik · 4.2 GPD kuyruk modeli (PWM) · 4.3 sağlam z-puanı
  Bölüm 5  güvenilirlik ağırlığı Z = n/(n+n0) ve önsel zinciri (servis katmanında)
  Bölüm 6  maliyet-duyarlı etiketli düzeltme
  Bölüm 7  mutlak korkuluk
  Bölüm 8  hacim şoku
  Bölüm 9  histerezis: açılma gecikmesi, ölü bant, kapanma gecikmesi
  Bölüm 10 algoritmanın tamamı; p̂ ve açıklama metni

Tasarım kararı 30 (R), 31 (ölçüm=pencere), 32 (hacim Z), 33 (MAD=0), 34 (GPD kabulü).
Kaynaklar: [SIFFER2017] [HOSKING_WALLIS1987] [BUHLMANN1967] [YOUDEN1950] [IEC62682_2022]
[WMO2023] [THAYER2025] [ROBERTS1959] [ROUSSEEUW_HUBERT2018].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from statistics import NormalDist, median, stdev
from typing import Iterable, Optional, Sequence

from app.literatur import (ALFA, ESIK_C_FN, ESIK_C_FP, ESIK_ETIKET_N0, ESIK_GPD_MIN_ASIM, ESIK_GPD_MIN_N,
                           ESIK_GPD_U_YUZDELIK, ESIK_GUVENILIRLIK_N0, ESIK_MIN_ARALIK, ESIK_MIN_ASIM,
                           ESIK_MIN_ETIKET, ESIK_MIN_ETIKET_SINIF, ESIK_P, ESIK_SAGLAM_MIN_N, ESIK_TABAN,
                           ESIK_TAVAN, ESIK_UZMAN_ONSEL, HACIM_PENCERE_SAAT, HACIM_SOK_Z, HISTEREZIS_DELTA_KATSAYI,
                           HISTEREZIS_DELTA_MIN, HISTEREZIS_K_OFF, HISTEREZIS_K_ON, MAD_OLCEK, RISK_SEVIYE_KISA,
                           RISK_Z_TAVAN, TARAMA_ARALIGI_DAKIKA)

_N = NormalDist()
KADEMELER = ("orta", "yuksek", "kritik")


def norm_ppf(q: float) -> float:
    return _N.inv_cdf(q)


# ---------------------------------------------------------------------------
# Risk puanı ve saatlik blok (Bölüm 3.2; Tasarım kararı 30)
# ---------------------------------------------------------------------------
def risk_puani(z: Optional[float], z_tavan: float = RISK_Z_TAVAN) -> Optional[float]:
    """R = 100·min(max(Z,0), z_tavan)/z_tavan  (0–100)."""
    if z is None or (isinstance(z, float) and math.isnan(z)):
        return None
    return 100.0 * min(max(z, 0.0), z_tavan) / z_tavan


def saatlik_blok_maksimumu(olcumler: Iterable[tuple[datetime, float]]) -> dict[datetime, float]:
    """X_h = max{R_i : ölçüm i, h saatine düşüyor} (Bölüm 3.2)."""
    bloklar: dict[datetime, float] = {}
    for t, r in olcumler:
        h = t.replace(minute=0, second=0, microsecond=0)
        bloklar[h] = r if h not in bloklar else max(bloklar[h], r)
    return dict(sorted(bloklar.items()))


# ---------------------------------------------------------------------------
# 4.1 Ampirik yüzdelik
# ---------------------------------------------------------------------------
def ampirik_esik(x: Sequence[float], p: float) -> float:
    """h = (n−1)(1−p); T = x_(⌊h⌋+1) + (h−⌊h⌋)(x_(⌊h⌋+2) − x_(⌊h⌋+1)) (NumPy 'linear' ile aynı)."""
    xs = sorted(x)
    n = len(xs)
    if n == 0:
        raise ValueError("Boş veri")
    h = (n - 1) * (1.0 - p)
    i = int(math.floor(h))
    if i + 1 >= n:
        return xs[-1]
    return xs[i] + (h - i) * (xs[i + 1] - xs[i])


# ---------------------------------------------------------------------------
# 4.2 GPD kuyruk modeli (Hosking & Wallis 1987 PWM)
# ---------------------------------------------------------------------------
def gpd_pwm(y: Sequence[float]) -> Optional[tuple[float, float]]:
    """Aşımlar y için (σ̂, ξ̂). a0 = ⟨y⟩, a1 = ⟨(1−p_j) y_(j)⟩, p_j = (j−0,35)/m;
    k̂ = a0/(a0−2a1) − 2, σ̂ = 2·a0·a1/(a0−2a1), ξ̂ = −k̂."""
    ys = sorted(y)
    m = len(ys)
    if m < 2:
        return None
    a0 = sum(ys) / m
    a1 = sum((1.0 - (j - 0.35) / m) * v for j, v in enumerate(ys, start=1)) / m
    payda = a0 - 2.0 * a1
    if payda <= 0 or a0 <= 0:
        return None
    k = a0 / payda - 2.0
    sigma = 2.0 * a0 * a1 / payda
    return sigma, -k


@dataclass(frozen=True)
class GPDUyum:
    u: float
    lam_u: float
    sigma: float
    xi: float
    m: int
    gecerli: bool
    neden: str = ""

    def sozluk(self) -> dict:
        return {"u": self.u, "lam_u": self.lam_u, "sigma": self.sigma, "xi": self.xi, "m": self.m,
                "gecerli": self.gecerli, "neden": self.neden}


def gpd_uydur(x: Sequence[float], u_yuzdelik: float = ESIK_GPD_U_YUZDELIK,
              min_asim: int = ESIK_GPD_MIN_ASIM) -> Optional[GPDUyum]:
    """u = normal dönemin P90'ı; λ_u = N_u/n; aşımlara PWM ile GPD. Kabul: Tasarım kararı 34."""
    n = len(x)
    if n < 2:
        return None
    u = ampirik_esik(x, 1.0 - u_yuzdelik)
    y = [v - u for v in x if v > u]
    lam = len(y) / n
    if len(y) < min_asim:
        return GPDUyum(u, lam, float("nan"), float("nan"), len(y), False, "aşım sayısı yetersiz")
    fit = gpd_pwm(y)
    if fit is None:
        return GPDUyum(u, lam, float("nan"), float("nan"), len(y), False, "PWM tanımsız")
    sigma, xi = fit
    if not (math.isfinite(sigma) and math.isfinite(xi)) or sigma <= 0:
        return GPDUyum(u, lam, sigma, xi, len(y), False, "σ̂ geçersiz")
    if not (-1.0 < xi < 0.5):
        return GPDUyum(u, lam, sigma, xi, len(y), False, "ξ̂ kabul aralığı dışında")
    return GPDUyum(u, lam, sigma, xi, len(y), True)


def gpd_esik(p: float, f: GPDUyum) -> Optional[float]:
    """z_p = u + (σ/ξ)[(p/λ_u)^(−ξ) − 1] (ξ≠0); u − σ ln(p/λ_u) (ξ=0). Yalnız p < λ_u için."""
    if not f.gecerli or p <= 0 or p >= f.lam_u:
        return None
    oran = p / f.lam_u
    if abs(f.xi) < 1e-9:
        return f.u - f.sigma * math.log(oran)
    return f.u + (f.sigma / f.xi) * (oran ** (-f.xi) - 1.0)


def gpd_asim_olasiligi(r: float, f: GPDUyum) -> Optional[float]:
    """P(X ≥ R) = λ_u (1 + ξ(R−u)/σ)^(−1/ξ)  (R > u)."""
    if not f.gecerli or r <= f.u:
        return None
    if abs(f.xi) < 1e-9:
        return f.lam_u * math.exp(-(r - f.u) / f.sigma)
    taban = 1.0 + f.xi * (r - f.u) / f.sigma
    if taban <= 0:
        return None
    return f.lam_u * taban ** (-1.0 / f.xi)


# ---------------------------------------------------------------------------
# 4.3 Sağlam z-puanı
# ---------------------------------------------------------------------------
def saglam_olcek(x: Sequence[float]) -> tuple[float, float, float]:
    """(medyan, MAD, s). s = 1,4826·MAD; MAD = 0 ise örneklem s.s. (Tasarım kararı 33)."""
    m = median(x)
    mad = median([abs(v - m) for v in x])
    s = MAD_OLCEK * mad
    if s <= 0 and len(x) > 1:
        s = stdev(x)
    return m, mad, s


def saglam_z_esigi(x: Sequence[float], p: float) -> Optional[float]:
    m, _, s = saglam_olcek(x)
    if s <= 0:
        return None
    return m + norm_ppf(1.0 - p) * s


# ---------------------------------------------------------------------------
# Kademe için yöntem seçimi (Bölüm 4 tablosu)
# ---------------------------------------------------------------------------
def kademe_esigi(x: Sequence[float], p: float, gpd: Optional[GPDUyum] = None) -> tuple[Optional[float], str]:
    """n·p ≥ 5 → ampirik; n ≥ 200 ve kuyruk modeli uyduysa → GPD; n ≥ 10 → sağlam z; aksi halde tanımsız."""
    n = len(x)
    if n == 0:
        return None, "yok"
    if n * p >= ESIK_MIN_ASIM:
        return ampirik_esik(x, p), "ampirik"
    if n >= ESIK_GPD_MIN_N:
        f = gpd if gpd is not None else gpd_uydur(x)
        if f is not None:
            t = gpd_esik(p, f)
            if t is not None:
                return t, "gpd"
    if n >= ESIK_SAGLAM_MIN_N:
        t = saglam_z_esigi(x, p)
        if t is not None:
            return t, "saglam_z"
    return None, "yok"


# ---------------------------------------------------------------------------
# Bölüm 5 güvenilirlik ağırlığı, Bölüm 6 etiket, Bölüm 7 korkuluk
# ---------------------------------------------------------------------------
def guvenilirlik_agirligi(n: int, n0: float = ESIK_GUVENILIRLIK_N0) -> float:
    """Z = n/(n+n0); n < 10 ise Z = 0 [BUHLMANN1967]."""
    if n < ESIK_SAGLAM_MIN_N:
        return 0.0
    return n / (n + n0)


def harmanla(kurum: Optional[float], onsel: float, z: float) -> float:
    """T = Z·T(kurum) + (1−Z)·T(önsel)."""
    if kurum is None or z <= 0:
        return onsel
    return z * kurum + (1.0 - z) * onsel


def maliyet_optimal_esik(gercek: Sequence[float], siradan: Sequence[float],
                         c_fn: float = ESIK_C_FN, c_fp: float = ESIK_C_FP) -> Optional[float]:
    """c* = argmin C(c), C = c_FN·FNR + c_FP·FPR; FNR = #{gerçek: R<c}/#gerçek, FPR = #{sıradan: R≥c}/#sıradan.
    Adaylar gözlenen R değerleridir; eşit maliyette en küçük c seçilir (kaçırma pahalı). [YOUDEN1950]"""
    if not gercek or not siradan:
        return None
    en_iyi, en_iyi_c = None, None
    for c in sorted(set(gercek) | set(siradan)):
        fnr = sum(1 for r in gercek if r < c) / len(gercek)
        fpr = sum(1 for r in siradan if r >= c) / len(siradan)
        maliyet = c_fn * fnr + c_fp * fpr
        if en_iyi is None or maliyet < en_iyi - 1e-12:
            en_iyi, en_iyi_c = maliyet, c
    return en_iyi_c


def etiket_agirligi(m: int, n0: float = ESIK_ETIKET_N0) -> float:
    """Z_e = m/(m+30)."""
    return m / (m + n0)


def korkuluk_uygula(t: Sequence[float], taban: Sequence[float] = ESIK_TABAN, tavan: Sequence[float] = ESIK_TAVAN,
                    aralik: float = ESIK_MIN_ARALIK) -> tuple[tuple[float, float, float], list[str]]:
    """T_k ← min(max(T_k, taban_k), tavan_k); T_yüksek ≥ T_orta+2, T_kritik ≥ T_yüksek+2.
    Devreye giren kademelerin adlarını döndürür."""
    yeni = [min(max(t[i], taban[i]), tavan[i]) for i in range(3)]
    devrede = [KADEMELER[i] for i in range(3) if abs(yeni[i] - t[i]) > 1e-12]
    for i in (1, 2):
        alt = yeni[i - 1] + aralik
        if yeni[i] < alt:
            yeni[i] = alt
            if KADEMELER[i] not in devrede:
                devrede.append(KADEMELER[i])
    return (yeni[0], yeni[1], yeni[2]), devrede


# ---------------------------------------------------------------------------
# Eşiklerin tam hesabı (Bölüm 10, adım 3–5)
# ---------------------------------------------------------------------------
@dataclass
class EsikSonucu:
    esikler: tuple[float, float, float]
    kurum_tahmini: tuple[Optional[float], Optional[float], Optional[float]]
    onsel: tuple[float, float, float]
    onsel_kaynak: str
    yontemler: tuple[str, str, str]
    guvenilirlik_z: float
    n: int
    medyan: Optional[float]
    olcek_s: float
    gpd: Optional[dict]
    korkuluk: list[str]
    etiket_duzeltme: Optional[dict]
    kaynak: str

    def sozluk(self) -> dict:
        return {
            "esikler": dict(zip(KADEMELER, self.esikler)),
            "kurum_tahmini": dict(zip(KADEMELER, self.kurum_tahmini)),
            "onsel": dict(zip(KADEMELER, self.onsel)), "onsel_kaynak": self.onsel_kaynak,
            "yontemler": dict(zip(KADEMELER, self.yontemler)), "guvenilirlik_z": self.guvenilirlik_z,
            "n": self.n, "medyan": self.medyan, "olcek_s": self.olcek_s, "gpd": self.gpd,
            "korkuluk": self.korkuluk, "etiket_duzeltme": self.etiket_duzeltme, "kaynak": self.kaynak,
        }


def havuz_esikleri(x: Sequence[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Sektör/platform havuzu: aynı yöntemle ham eşik (harmanlama ve korkuluk yok)."""
    gpd = gpd_uydur(x) if len(x) >= ESIK_GPD_MIN_N else None
    return tuple(kademe_esigi(x, ESIK_P[k], gpd)[0] for k in KADEMELER)  # type: ignore[return-value]


def onsel_olustur(havuz: Optional[Sequence[float]], havuz_kaynagi: str) -> tuple[tuple[float, float, float], str]:
    """Havuz eşiklerinde tanımsız kademe uzman önseline düşer. Havuz yoksa uzman önseli."""
    if not havuz:
        return tuple(ESIK_UZMAN_ONSEL), "uzman"  # type: ignore[return-value]
    ham = havuz_esikleri(havuz)
    if all(v is None for v in ham):
        return tuple(ESIK_UZMAN_ONSEL), "uzman"  # type: ignore[return-value]
    return tuple(ham[i] if ham[i] is not None else ESIK_UZMAN_ONSEL[i] for i in range(3)), havuz_kaynagi  # type: ignore[return-value]


def esik_hesapla(x: Sequence[float], onsel: Sequence[float], onsel_kaynak: str = "uzman", *,
                 etiket_gercek: Sequence[float] = (), etiket_siradan: Sequence[float] = (),
                 n0: float = ESIK_GUVENILIRLIK_N0) -> EsikSonucu:
    n = len(x)
    gpd = gpd_uydur(x) if n >= ESIK_GPD_MIN_N else None
    kurum: list[Optional[float]] = []
    yontem: list[str] = []
    for k in KADEMELER:
        t, y = kademe_esigi(x, ESIK_P[k], gpd)
        kurum.append(t)
        yontem.append(y)
    z = guvenilirlik_agirligi(n, n0)
    if n:
        med, _, s = saglam_olcek(x)
    else:
        med, s = None, 0.0
    t = [harmanla(kurum[i], onsel[i], z) for i in range(3)]

    etiket = None
    m = len(etiket_gercek) + len(etiket_siradan)
    if m >= ESIK_MIN_ETIKET and len(etiket_gercek) >= ESIK_MIN_ETIKET_SINIF and len(etiket_siradan) >= ESIK_MIN_ETIKET_SINIF:
        c_star = maliyet_optimal_esik(etiket_gercek, etiket_siradan)
        if c_star is not None:
            ze = etiket_agirligi(m)
            onceki = t[1]
            t[1] = ze * c_star + (1.0 - ze) * t[1]
            etiket = {"c_star": c_star, "z_e": ze, "m": m, "onceki_yuksek": onceki,
                      "gercek": len(etiket_gercek), "siradan": len(etiket_siradan)}

    son, devrede = korkuluk_uygula(t)
    if z <= 0:
        kaynak = onsel_kaynak
    else:
        kaynak = "kurum" if onsel_kaynak == "uzman" else f"kurum+{onsel_kaynak}"
    return EsikSonucu(esikler=son, kurum_tahmini=tuple(kurum), onsel=tuple(onsel), onsel_kaynak=onsel_kaynak,  # type: ignore[arg-type]
                      yontemler=tuple(yontem), guvenilirlik_z=z, n=n, medyan=med, olcek_s=s,  # type: ignore[arg-type]
                      gpd=gpd.sozluk() if gpd else None, korkuluk=devrede, etiket_duzeltme=etiket, kaynak=kaynak)


# ---------------------------------------------------------------------------
# Seviye, olasılık, dönüş süresi (Bölüm 2, 10)
# ---------------------------------------------------------------------------
def seviye_ham(r: float, esikler: Sequence[float]) -> int:
    """R ≥ T_kritik → 3; R ≥ T_yüksek → 2; R ≥ T_orta → 1; aksi halde 0."""
    if r >= esikler[2]:
        return 3
    if r >= esikler[1]:
        return 2
    if r >= esikler[0]:
        return 1
    return 0


def asim_olasiligi(r: float, x: Sequence[float], gpd: Optional[GPDUyum] = None) -> float:
    """GPD kuyruğunda λ_u(1+ξ(R−u)/σ)^(−1/ξ); diğer durumlarda p̂ = (1 + #{X ≥ R})/(n+1)."""
    if gpd is not None:
        p = gpd_asim_olasiligi(r, gpd)
        if p is not None and p > 0:
            return p
    n = len(x)
    return (1 + sum(1 for v in x if v >= r)) / (n + 1)


def donus_suresi_saat(p: float) -> float:
    """D = 1/p (saat)."""
    return 1.0 / p


def donus_metni(saat: float) -> str:
    if saat < 1.5:
        return "her saat"
    if saat < 48:
        return f"yaklaşık {round(saat)} saatte bir"
    gun = saat / 24
    if gun < 14:
        return f"yaklaşık {round(gun)} günde bir"
    if gun < 60:
        return f"yaklaşık {round(gun / 7)} haftada bir"
    if gun < 730:
        return f"yaklaşık {round(gun / 30.4)} ayda bir"
    return f"yaklaşık {round(gun / 365)} yılda bir"


# ---------------------------------------------------------------------------
# Bölüm 8 hacim şoku (Tasarım kararı 32)
# ---------------------------------------------------------------------------
def hacim_z_skoru(gecmis: Sequence[float], simdi: float, lam: float = ALFA,
                  pencere: int = HACIM_PENCERE_SAAT) -> Optional[float]:
    """Son 24 saatlik hacmin EWMA'sına göre standartlaştırma [ROBERTS1959]:
    EWMA_0 = y_1; EWMA_i = λ y_i + (1−λ) EWMA_{i−1}; ölçek = √max(s², EWMA) (Poisson tabanı)."""
    g = list(gecmis)[-pencere:]
    if len(g) < pencere:
        return None
    ew = g[0]
    for v in g[1:]:
        ew = lam * v + (1.0 - lam) * ew
    s2 = stdev(g) ** 2 if len(g) > 1 else 0.0
    olcek = math.sqrt(max(s2, ew))
    if olcek <= 0:
        return None
    return (simdi - ew) / olcek


# ---------------------------------------------------------------------------
# Bölüm 9 histerezis
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Histerezis:
    nihai: int
    yon: str          # yukseldi | dustu | korundu
    kod: str
    metin: str
    ham: int
    aday: int
    sok: bool
    delta: float

    def sozluk(self) -> dict:
        return {"nihai": self.nihai, "yon": self.yon, "kod": self.kod, "metin": self.metin, "ham": self.ham,
                "aday": self.aday, "hacim_sok": self.sok, "delta": self.delta}


def delta_bandi(olcek_s: float) -> float:
    """δ = max(2, 0,5·s)."""
    return max(HISTEREZIS_DELTA_MIN, HISTEREZIS_DELTA_KATSAYI * olcek_s)


def histerezis(*, r_dizi: Sequence[float], ham_dizi: Sequence[int], onceki_nihai: int,
               esikler: Sequence[float], olcek_s: float, hacim_z: Optional[float],
               k_on: int = HISTEREZIS_K_ON, k_off: int = HISTEREZIS_K_OFF) -> Histerezis:
    """r_dizi / ham_dizi: kronolojik, SON ELEMAN mevcut ölçümdür.

    Yükselme: teyitli = min(son k_on ham seviye); nihai = max(önceki, teyitli). İstisna: Kritik ham seviye
    ve hacim şoku (Z_hacim ≥ 3 → ham+1 kademe) beklemeden yükseltir.
    Düşüş: son k_off ölçümün hepsi T_terk − δ'nın altındaysa TEK kademe iner; hacim şoku düşüşü engeller."""
    ham = ham_dizi[-1]
    sok = hacim_z is not None and hacim_z >= HACIM_SOK_Z
    aday = min(ham + 1, 3) if sok else ham
    delta = delta_bandi(olcek_s)

    if sok:
        yukselen, kod_yuk = aday, "hacim_soku"
    elif ham == 3:
        yukselen, kod_yuk = 3, "kritik_aninda"
    else:
        yukselen = min(ham_dizi[-k_on:]) if len(ham_dizi) >= k_on else 0
        kod_yuk = "teyitli_yukselme"

    if yukselen > onceki_nihai:
        metin = {"hacim_soku": "hacim şoku: seviye bir kademe yükseltildi, teyit beklenmedi",
                 "kritik_aninda": "Kritik seviyeye anında izin verilir",
                 "teyitli_yukselme": f"{k_on} ardışık ölçüm teyidi: yükselme"}[kod_yuk]
        return Histerezis(yukselen, "yukseldi", kod_yuk, metin, ham, aday, sok, delta)

    if onceki_nihai > 0 and aday < onceki_nihai:
        if len(r_dizi) >= k_off:
            t_terk = esikler[onceki_nihai - 1]
            if all(r < t_terk - delta for r in r_dizi[-k_off:]):
                return Histerezis(onceki_nihai - 1, "dustu", "kademeli_dusus",
                                  f"son {k_off} ölçümün hepsi {t_terk - delta:.1f} altında: bir kademe düşüş",
                                  ham, aday, sok, delta)
        return Histerezis(onceki_nihai, "korundu", "olu_bant",
                          f"ölü bant/kapanma gecikmesi: seviye korunuyor (bırakma sınırı {esikler[onceki_nihai - 1] - delta:.1f})",
                          ham, aday, sok, delta)

    if ham > onceki_nihai:
        return Histerezis(onceki_nihai, "korundu", "teyit_bekleniyor",
                          "yükselme için ardışık ölçüm teyidi bekleniyor", ham, aday, sok, delta)
    if sok and onceki_nihai > 0:
        return Histerezis(onceki_nihai, "korundu", "hacim_soku_dusus_engel",
                          "hacim şoku: düşüş engellendi", ham, aday, sok, delta)
    return Histerezis(onceki_nihai, "korundu", "degisim_yok", "değişim yok", ham, aday, sok, delta)


# ---------------------------------------------------------------------------
# Uyarlamalı tarama aralığı (Bölüm 3.2; Tasarım kararı 42)
# ---------------------------------------------------------------------------
def tarama_araligi_dakika(nihai_seviye: int, taban_dakika: int = 15) -> int:
    """Seviye yükseldikçe sık ölçüm; alt sınır yapılandırılabilir (5–60 dakika)."""
    return max(5, min(60, max(TARAMA_ARALIGI_DAKIKA.get(nihai_seviye, 60), taban_dakika)))


# ---------------------------------------------------------------------------
# Açıklama metni (Bölüm 12)
# ---------------------------------------------------------------------------
def aciklama_metni(*, r: float, nihai: int, ham: int, esik: EsikSonucu, p_hat: float, donus_saat: float,
                   hist: Histerezis) -> str:
    e = esik.esikler
    kaynak_ad = {"kurum": "kurum", "uzman": "uzman önseli", "sektor": "sektör havuzu", "platform": "platform havuzu",
                 "kurum+sektor": "kurum + sektör", "kurum+platform": "kurum + platform"}.get(esik.kaynak, esik.kaynak)
    s = (f"Risk puanı {r:.1f}/100 → {RISK_SEVIYE_KISA[nihai]} Risk. Bu kurum için eşikler: Orta ≥ {e[0]:.1f}, "
         f"Yüksek ≥ {e[1]:.1f}, Kritik ≥ {e[2]:.1f} (kaynak: {kaynak_ad}; güvenilirlik ağırlığı Z = {esik.guvenilirlik_z:.2f}, "
         f"{esik.n} saatlik normal dönem verisi). Bu puan, kurumun normal döneminde saat başına p ≈ {p_hat:.4f} olasılıkla, "
         f"yani {donus_metni(donus_saat)} görülür. ")
    if ham != nihai:
        s += f"Ham seviye {RISK_SEVIYE_KISA[ham]} Risk; {hist.metin}. "
    elif hist.yon != "korundu":
        s += f"{hist.metin[0].upper()}{hist.metin[1:]}. "
    if esik.korkuluk:
        s += f"Mutlak korkuluk devrede: {', '.join(esik.korkuluk)}. "
    if esik.etiket_duzeltme:
        d = esik.etiket_duzeltme
        s += (f"Analist geri bildirimleriyle (m = {d['m']}) Yüksek eşiği {d['onceki_yuksek']:.1f} değerinden "
              f"maliyet-duyarlı olarak düzeltildi (c* = {d['c_star']:.1f}, Z_e = {d['z_e']:.2f}). ")
    return s.strip()
