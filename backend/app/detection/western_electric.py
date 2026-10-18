"""
Western Electric kuralları — yalnız üst taraf [WECO1956; NIST_WECO] (Rapor Bölüm 3.7).

  Kural 1: tek nokta > +3σ              → 3 KRİZ
  Kural 2: son 3 noktanın 2'si > +2σ    → 2 YÜKSEK UYARI
  Kural 3: son 5 noktanın 4'ü > +1σ     → 1 ERKEN UYARI
  Kural 4: 8 ardışık nokta > 0          → 1 ERKEN UYARI ("sessiz birikim", [FINK1986] prodromal evre)

Kuralların seviyelere sıralanması ihlal edilen bölgenin sigma uzaklığına göredir;
bir pencerenin seviyesi ihlal edilen kuralların en yükseğidir.

Isınma (Rapor Bölüm 3.8): ISINMA = p + ⌈ln 0,05 / ln(1−α)⌉ = 28 pencere
[MARCUS2011; FISHER_P05]. Isınma içindeki pencerelerde alarm üretilmez.

Tasarım kararı 23: Kurallar, ısınma sonrasındaki ve Z'si tanımlı olan noktalar
dizisi üzerinde uygulanır; Z'si eksik pencere bir nokta sayılmaz (atlanır).
"""
from __future__ import annotations

from typing import Optional, Sequence

from app.literatur import ISINMA_PENCERE, SEVIYE_ETIKETLERI, WECO_KURALLARI


def _ihlal(son_noktalar: Sequence[float], n: int, m: int, sinir: float) -> bool:
    if len(son_noktalar) < n:
        return False
    pencere = son_noktalar[-n:]
    return sum(1 for z in pencere if z > sinir) >= m


def seviyeler(z_serisi: Sequence[Optional[float]], isinma: int = ISINMA_PENCERE) -> list[dict]:
    """Her pencere için {seviye, etiket, kurallar, isinmada} döndürür."""
    sonuc: list[dict] = []
    noktalar: list[float] = []
    for t, z in enumerate(z_serisi):
        if t < isinma:
            sonuc.append({"seviye": 0, "etiket": "ISINMA", "kurallar": [], "isinmada": True})
            continue
        if z is None:
            sonuc.append({"seviye": 0, "etiket": "VERİ YOK", "kurallar": [], "isinmada": False, "eksik": True})
            continue
        noktalar.append(z)
        ihlaller = [k for k in WECO_KURALLARI if _ihlal(noktalar, k["n"], k["m"], k["sinir"])]
        seviye = max((k["seviye"] for k in ihlaller), default=0)
        sonuc.append({
            "seviye": seviye,
            "etiket": SEVIYE_ETIKETLERI[seviye],
            "kurallar": [k["kural"] for k in ihlaller],
            "sessiz_birikim": any(k["kural"] == 4 for k in ihlaller),
            "isinmada": False,
        })
    return sonuc
