"""
Aynı krizin tanınması için "parmak izi" (Tasarım kararı 39).

Alarm süresince toplanan negatif/kriz içeriklerinden TF-IDF ile en ayırt edici sözcük gövdeleri
çıkarılır. Gövde = ilk 5 karakter (Türkçe için F5 önek kırpma; Can vd. 2008 [CAN2008]).
TF-IDF ve Jaccard eşikleri kaynaksız tasarım tercihleridir; etiketli veriyle ayarlanmalıdır.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Optional, Sequence

from app.literatur import (ONEK_UZUNLUGU, PARMAK_IZI_BENZERLIK, PARMAK_IZI_BENZERLIK_AYNI_TIP,
                           PARMAK_IZI_TERIM_SAYISI)
from app.nlp.normalize import sozcukler

DURAK = frozenset("""
ve veya ile ya da de da ki mi mı mu mü bir bu şu o bunu şunu onu bunlar şunlar onlar ben sen biz siz ne neden nasıl
için gibi kadar çok daha en ama fakat ancak lakin ise var yok değil olan olarak oldu olduğu olduğunu olmuş oluyor olsun
her tüm bütün hiç sonra önce yine hem artık şimdi bugün dün yarın bile sadece yalnız çünkü diye kendi kendine
bana sana ona bize size onlara benim senin bizim sizin onun beni seni onu bizi sizi
the and for that with this from are was
""".split())


def govde(sozcuk: str) -> str:
    return sozcuk[:ONEK_UZUNLUGU]


def _kume(metin: str, haric: set[str]) -> set[str]:
    return {govde(s) for s in sozcukler(metin)
            if len(s) >= 3 and not s.isdigit() and s not in DURAK and s not in haric}


def anahtar_govdeler(alarm_metinleri: Sequence[str], tum_metinler: Sequence[str],
                     haric: Iterable[str] = (), n: int = PARMAK_IZI_TERIM_SAYISI) -> list[str]:
    """Alarm belgelerinde sık, tüm belge havuzunda seyrek gövdeler (TF-IDF)."""
    haric_govde = {govde(h) for h in haric}
    haric_tam = set(haric)
    dis = haric_tam | haric_govde
    alarm_kumeleri = [_kume(m, dis) for m in alarm_metinleri]
    if not alarm_kumeleri:
        return []
    tf: Counter[str] = Counter()
    for k in alarm_kumeleri:
        tf.update(k)
    df: Counter[str] = Counter()
    for m in tum_metinler:
        df.update(_kume(m, dis))
    N = max(len(tum_metinler), len(alarm_kumeleri))
    min_tf = 2 if len(alarm_kumeleri) >= 4 else 1
    puan = {t: c * math.log((N + 1) / (df.get(t, 0) + 1) + 1.0) for t, c in tf.items() if c >= min_tf}
    return [t for t, _ in sorted(puan.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def ayni_kriz_mi(a: Optional[dict], b: Optional[dict]) -> tuple[bool, float]:
    """İki parmak izi aynı kriz mi? Jaccard ≥ 0,5 ya da (aynı SCCT tipi ve Jaccard ≥ 0,2)."""
    if not a or not b:
        return False, 0.0
    j = jaccard(a.get("govdeler", []), b.get("govdeler", []))
    ayni_tip = bool(a.get("tip")) and a.get("tip") == b.get("tip")
    return (j >= PARMAK_IZI_BENZERLIK or (ayni_tip and j >= PARMAK_IZI_BENZERLIK_AYNI_TIP)), j
