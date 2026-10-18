"""
Kuruma özgü eşik katmanı (v5).

Bu modül raporun karar kuralını (WECO, Rapor Bölüm 3.7) DEĞİŞTİRMEZ
(Tasarım kararı 22). Kararın her kurum için neden farklı ham eşiklere
karşılık geldiğini ve kurumun kendi geçmişine göre ne kadar olağandışı
olduğunu açıklayan üç istatistik üretir:

1) Ham birim eşik karşılıkları
   Rapor Bölüm 3.2'deki z-skorunun tersi: bir sonraki pencerede göstergenin
   +kσ bölgesine girmesi için gereken ham değer
       x*_{i,k} = μ_{i,t} + k · √(π/2) · OMS_{i,t}        [MARCUS2011; GEARY1935]
   μ ve OMS kurumun kendi akışından geldiği için eşik kuruma özgüdür
   (ör. A kurumu için saatte 12 bahsetme +3σ iken B için 140 olabilir).
   Yerel/göreli eşik ilkesi: [WMO2023; THAYER2025].

2) Ampirik aşım olasılığı ve dönüş süresi
       p̂_t = (1 + #{j : Z_j ≥ Z_t}) / (n + 1)             [PHIPSON_SMYTH2010]
   Z_j: kurumun ısınma sonrası geçmiş Z değerleri (mevcut nokta hariç).
   Dönüş süresi = pencere uzunluğu / p̂ ("ortalama kaç saatte bir bu kadar
   yüksek bir değer görülür") [WMO2023; THAYER2025].

3) Kalibrasyon tanısı (Stouffer bağımsızlık varsayımı denetimi)
   Bağımsız standart normal bileşenler altında P(Z > k) = 1 − Φ(k)
   [WHITLOCK2005]. Kurumun gözlenen aşım oranının %95 Clopper–Pearson
   aralığı [CLOPPER_PEARSON1934] bu nominal değeri içermiyorsa "Z şişmesi /
   daralması" uyarısı verilir. Rapor Bölüm 8, Stouffer sınırlılığının
   kuruma özgü ölçümüdür.

İsteğe bağlı: Strube (1985) korelasyon matrisi kestirimi
[STRUBE1985; CINAR_VIECHTBAUER2022]; Tasarım kararı 20.
"""
from __future__ import annotations

import math
from typing import Mapping, Optional, Sequence

from scipy.stats import beta

from app.detection.composite import phi
from app.literatur import BIN_SAAT, ISINMA_PENCERE


def ampirik_asim_olasiligi(z_simdi: Optional[float], gecmis: Sequence[float]) -> Optional[dict]:
    if z_simdi is None or not gecmis:
        return None
    n = len(gecmis)
    b = sum(1 for z in gecmis if z >= z_simdi)
    p = (1 + b) / (n + 1)
    return {
        "p": p,
        "n_gecmis": n,
        "donus_suresi_saat": BIN_SAAT / p,
        "normal_teori_p": 1.0 - phi(z_simdi),
        "kaynaklar": ["PHIPSON_SMYTH2010", "WMO2023", "THAYER2025"],
    }


def clopper_pearson(x: int, n: int, guven: float = 0.95) -> tuple[float, float]:
    a = 1.0 - guven
    alt = 0.0 if x == 0 else float(beta.ppf(a / 2, x, n - x + 1))
    ust = 1.0 if x == n else float(beta.ppf(1 - a / 2, x + 1, n - x))
    return alt, ust


def kalibrasyon_tanisi(gecmis: Sequence[float]) -> Optional[dict]:
    n = len(gecmis)
    if n == 0:
        return None
    bolgeler = []
    for k in (1, 2, 3):
        x = sum(1 for z in gecmis if z > k)
        nominal = 1.0 - phi(k)
        alt, ust = clopper_pearson(x, n)
        durum = "uyumlu"
        if nominal < alt:
            durum = "şişme"      # gözlenen aşım nominalden anlamlı fazla
        elif nominal > ust:
            durum = "daralma"    # gözlenen aşım nominalden anlamlı az
        bolgeler.append({
            "k_sigma": k, "gozlenen": x, "n": n, "gozlenen_oran": x / n,
            "nominal_oran": nominal, "guven_araligi_95": [alt, ust], "durum": durum,
        })
    return {"bolgeler": bolgeler, "kaynaklar": ["WHITLOCK2005", "CLOPPER_PEARSON1934"]}


def korelasyon_kestir(skor_serileri: Mapping[str, Sequence[Optional[float]]],
                      en_az_ortak: int = ISINMA_PENCERE) -> dict[tuple[str, str], float]:
    """Çift bazında eksiksiz gözlemlerle Pearson ρ (Tasarım kararı 20)."""
    kodlar = list(skor_serileri)
    rho: dict[tuple[str, str], float] = {}
    for i, a in enumerate(kodlar):
        for b in kodlar[i + 1:]:
            ciftler = [(x, y) for x, y in zip(skor_serileri[a], skor_serileri[b])
                       if x is not None and y is not None]
            if len(ciftler) < en_az_ortak:
                rho[(a, b)] = 0.0
                continue
            xs, ys = zip(*ciftler)
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            sxy = sum((x - mx) * (y - my) for x, y in ciftler)
            sxx = sum((x - mx) ** 2 for x in xs)
            syy = sum((y - my) ** 2 for y in ys)
            rho[(a, b)] = sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0
    return rho
