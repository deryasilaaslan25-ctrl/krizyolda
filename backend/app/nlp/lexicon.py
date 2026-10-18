"""
NRC Word-Emotion Association Lexicon (EmoLex), Türkçe dosyası
[MOHAMMAD_TURNEY2013; NRC_EMOLEX].

Lisans: araştırma amaçlı ücretsiz, ticari kullanım lisans gerektirir; bu
nedenle pakete gömülmez, scripts/indir_nrc.py ile indirilir.

Dosya biçimi (sekme ayrımlı): English Word, anger, anticipation, disgust,
fear, joy, negative, positive, sadness, surprise, trust, Turkish Word.

Kurallar:
  * Çoklu çeviri birleştirme: aynı Türkçe sözcüğe eşlenen satırlarda bir
    etiket satırların yarısından fazlasında işaretliyse atanır (Tasarım kararı 6).
  * Önek eşleşmesi: sözlük girdisi ≥ 5 karakterse metindeki sözcüğün öneki
    olarak eşleşir [CAN2008]; daha kısa girdiler yalnız birebir eşleşir.
    Sözlük tarafı kesilmez; birden çok girdi eşleşirse en uzun girdi seçilir
    (etiketsiz olsa bile) (Tasarım kararı 7).
"""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.literatur import ONEK_UZUNLUGU
from app.nlp.normalize import sozcukler

ETIKETLER = ("anger", "anticipation", "disgust", "fear", "joy", "negative",
             "positive", "sadness", "surprise", "trust")

VARSAYILAN_YOL = Path(__file__).resolve().parents[2] / "data" / "nrc" / "Turkish-NRC-EmoLex.txt"


def sozcuk_eslesir(metin_sozcugu: str, girdi_sozcugu: str, onek: int = ONEK_UZUNLUGU) -> bool:
    if metin_sozcugu == girdi_sozcugu:
        return True
    return len(girdi_sozcugu) >= onek and metin_sozcugu.startswith(girdi_sozcugu)


@dataclass(frozen=True)
class Eslesme:
    bas: int
    uzunluk: int          # kaç metin sözcüğü tüketildi
    girdi: str
    etiketler: frozenset


class Sozluk:
    def __init__(self, girdiler: dict[tuple[str, ...], frozenset]):
        self.girdiler = girdiler
        self._ilk: dict[str, list[tuple[str, ...]]] = defaultdict(list)
        for anahtar in girdiler:
            self._ilk[anahtar[0]].append(anahtar)

    def __len__(self) -> int:
        return len(self.girdiler)

    @classmethod
    def satirlardan(cls, satirlar: list[str]) -> "Sozluk":
        baslik = satirlar[0].rstrip("\n").split("\t")
        idx = {ad: i for i, ad in enumerate(baslik)}
        tr_i = idx.get("Turkish Word", len(baslik) - 1)
        gruplar: dict[tuple[str, ...], list[set]] = defaultdict(list)
        for satir in satirlar[1:]:
            parca = satir.rstrip("\n").split("\t")
            if len(parca) <= tr_i:
                continue
            anahtar = tuple(sozcukler(parca[tr_i]))
            if not anahtar:
                continue
            isaretli = {e for e in ETIKETLER if e in idx and parca[idx[e]].strip() == "1"}
            gruplar[anahtar].append(isaretli)
        girdiler: dict[tuple[str, ...], frozenset] = {}
        for anahtar, satir_etiketleri in gruplar.items():
            n = len(satir_etiketleri)
            secilen = {e for e in ETIKETLER if sum(1 for s in satir_etiketleri if e in s) > n / 2}
            girdiler[anahtar] = frozenset(secilen)
        return cls(girdiler)

    @classmethod
    def dosyadan(cls, yol: str | Path) -> "Sozluk":
        with open(yol, encoding="utf-8") as f:
            return cls.satirlardan(f.readlines())

    def _adaylar(self, sozcuk: str) -> list[tuple[str, ...]]:
        adaylar = list(self._ilk.get(sozcuk, []))
        for L in range(ONEK_UZUNLUGU, len(sozcuk)):
            for a in self._ilk.get(sozcuk[:L], []):
                if len(a[0]) >= ONEK_UZUNLUGU:
                    adaylar.append(a)
        return adaylar

    def eslestir(self, tokenler: list[str], i: int) -> Optional[Eslesme]:
        """i konumunda başlayan en uzun sözlük eşleşmesi."""
        en_iyi: Optional[tuple[str, ...]] = None
        for aday in self._adaylar(tokenler[i]):
            if i + len(aday) > len(tokenler):
                continue
            if all(sozcuk_eslesir(tokenler[i + j], aday[j]) for j in range(len(aday))):
                if en_iyi is None or (len(aday), len(" ".join(aday))) > (len(en_iyi), len(" ".join(en_iyi))):
                    en_iyi = aday
        if en_iyi is None:
            return None
        return Eslesme(i, len(en_iyi), " ".join(en_iyi), self.girdiler[en_iyi])


@lru_cache(maxsize=4)
def _yukle(yol: str) -> Optional[Sozluk]:
    if not os.path.exists(yol):
        return None
    return Sozluk.dosyadan(yol)


def sozluk_al() -> Optional[Sozluk]:
    """ERKIS_NRC_YOLU ya da varsayılan yoldan NRC Türkçe sözlüğü. Yoksa None."""
    return _yukle(os.environ.get("ERKIS_NRC_YOLU", str(VARSAYILAN_YOL)))
