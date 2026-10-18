"""
Bileşik gösterge adımları [OECD2008] — Rapor Bölüm 3.3–3.6.

  kırp:     s ← min(max(s, −3), +3)                        [SHEWHART1931; OECD2008 s.28]
  ağırlık:  1. beyin: w_i = 1/n (n = o pencerede ölçülebilen gösterge sayısı); 13 gösterge de varsa her biri 100/13 puan.
            2. beyin: w_i = u_i / Σ u_j (u: uzman puanlarından türetilmiş ağırlık, bkz. beyin/uzman.py).
            Her iki beyinde de eksik gösterge dışarıda bırakılır ve kalanlar yeniden normalleştirilir [OECD2008 s.31].
  KRE:      KRE_t = Σ w_i s_i,t                             [OECD2008]
  Z:        Z_t = Σ w_i s_i,t / √(Σ w_i²)                   [WHITLOCK2005; COUSINS2007]
  yüzdelik: 100·Φ(Z_t)

İsteğe bağlı (v5, varsayılan kapalı): bağımsızlık varsayımı yerine Strube
(1985) düzeltmesi  Z = Σ w_i s_i / √(Σ_i Σ_j w_i w_j ρ_ij)
[STRUBE1985; CINAR_VIECHTBAUER2022]. Tasarım kararı 20.
"""
from __future__ import annotations

import math
from typing import Mapping, Optional

from app.literatur import BOYUTLAR, KIRPMA_SINIRI


def kirp(s: float, sinir: float = KIRPMA_SINIRI) -> float:
    return min(max(s, -sinir), sinir)


def agirliklar(mevcut: set[str], temel: Optional[Mapping[str, float]] = None) -> dict[str, float]:
    """Ölçülebilen göstergeler için ağırlık; toplam her zaman 1.

    temel verilmezse (1. beyin) tüm göstergeler eşit ağırlık alır. temel verilirse (2. beyin) yalnız ölçülebilen
    göstergelerin temel ağırlıkları toplamı 1'e yeniden normalleştirilir."""
    secili = [k for k in sorted(mevcut, key=lambda x: int(x[1:])) if k in _SECILEN]
    if not secili:
        return {}
    if temel is None:
        return {k: 1.0 / len(secili) for k in secili}
    toplam = sum(temel.get(k, 0.0) for k in secili)
    if toplam <= 0:
        return {}
    return {k: temel[k] / toplam for k in secili}


def phi(z: float) -> float:
    """Standart normal dağılım fonksiyonu."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def birlestir(skorlar: Mapping[str, Optional[float]],
              korelasyon: Optional[Mapping[tuple[str, str], float]] = None,
              temel_agirlik: Optional[Mapping[str, float]] = None) -> dict:
    """Bir pencerenin kırpılmış skorlarından KRE ve Z hesaplar.

    skorlar: {"G1": 1.2, "G4": None, ...} (None = eksik)
    korelasyon: yalnız Strube modunda; {(a, b): ρ_ab}
    """
    kirpik = {k: kirp(v) for k, v in skorlar.items() if v is not None and k in _SECILEN}
    w = agirliklar(set(kirpik), temel_agirlik)
    if not w:
        return {"kre": None, "z": None, "yuzdelik": None, "agirliklar": {}, "katkilar": {},
                "kirpilmis": {}, "yontem": "yok"}
    kre = sum(w[k] * kirpik[k] for k in w)
    payda_bagimsiz = math.sqrt(sum(v * v for v in w.values()))
    yontem = "stouffer"
    payda = payda_bagimsiz
    if korelasyon is not None:
        kodlar = list(w)
        toplam = 0.0
        for a in kodlar:
            for b in kodlar:
                rho = 1.0 if a == b else korelasyon.get((a, b), korelasyon.get((b, a), 0.0))
                toplam += w[a] * w[b] * rho
        if toplam > 0:
            payda = math.sqrt(toplam)
            yontem = "strube"
    z = kre / payda
    return {
        "kre": kre,
        "z": z,
        "yuzdelik": 100.0 * phi(z),
        "agirliklar": w,
        "katkilar": {k: w[k] * kirpik[k] for k in w},
        "kirpilmis": kirpik,
        "yontem": yontem,
    }


_SECILEN = {k for v in BOYUTLAR.values() for k in v}
