"""
Metin normalleştirme ve Türkçe sözcüklere ayırma.

Türkçe büyük/küçük harf dönüşümü (I→ı, İ→i) Python'un str.lower()
davranışından farklı olduğu için ayrıca uygulanır. Kesme işaretinden
sonraki ek (özel ad + ek yazımı, ör. "Gıda'nın") atılır (Tasarım kararı 24).
Q1 için kopya karşılaştırma normalleştirmesi: Tasarım kararı 17 [PACHECO2021].
"""
from __future__ import annotations

import re

_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_KULLANICI = re.compile(r"@\w+")
_KESME_EKI = re.compile(r"['’`´]\w+")
_SOZCUK = re.compile(r"[a-zçğıöşüâîû0-9]+")


def tr_kucuk(metin: str) -> str:
    return metin.replace("I", "ı").replace("İ", "i").lower()


def sozcukler(metin: str) -> list[str]:
    m = tr_kucuk(metin or "")
    m = _URL.sub(" ", m)
    m = _KULLANICI.sub(" ", m)
    m = _KESME_EKI.sub("", m)
    return _SOZCUK.findall(m)


def kopya_anahtari(metin: str) -> str:
    """Q1 için normalleştirilmiş metin (Tasarım kararı 17)."""
    return " ".join(sozcukler(metin))


def duz_metin(metin: str) -> str:
    """Tohum eşleşmesi için: küçük harf, noktalama → boşluk, tek boşluk."""
    return " " + " ".join(sozcukler(metin)) + " "
