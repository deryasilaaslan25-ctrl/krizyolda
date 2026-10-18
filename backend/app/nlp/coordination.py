"""
Koordineli / kopya içerik oranı (Q1) [PACHECO2021].

x = normalleştirilmiş metni en az iki farklı yazar tarafından paylaşılan
içerik oranı. KRE'ye girmez; yalnızca "manipülasyon şüphesi" uyarısıdır.
Kapsam ve normalleştirme: Tasarım kararı 17.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional, Sequence

from app.nlp.normalize import kopya_anahtari


def kopya_orani(icerikler: Sequence[tuple[str, str]]) -> Optional[float]:
    """icerikler: [(yazar, metin), ...]. Boşsa None."""
    if not icerikler:
        return None
    yazarlar: dict[str, set] = defaultdict(set)
    anahtarlar = []
    for yazar, metin in icerikler:
        a = kopya_anahtari(metin)
        anahtarlar.append(a)
        if a:
            yazarlar[a].add(yazar or "")
    kopya = sum(1 for a in anahtarlar if a and len(yazarlar[a]) >= 2)
    return kopya / len(icerikler)
