"""
2. beyin: uzman puanlarından gösterge ağırlığı (saf matematik, veritabanı yok).

Girdi: {uzman_kodu: {gosterge: puan}}. Her gösterge için uzmanlar arası ortalama ya da medyan alınır ve toplam 1 olacak
biçimde normalleştirilir. Uzmanlar arası uyum Kendall'ın uyum katsayısı W ile (bağlı sıra düzeltmesiyle) ölçülür.
Ölçek ve birleştirme yöntemi araştırmacı kararıdır (docs/TASARIM_KARARLARI.md); bu modül ikisini de parametre olarak alır.
"""
from __future__ import annotations

import statistics
from typing import Mapping, Optional, Sequence

GOSTERGELER = tuple(f"G{i}" for i in range(1, 14))


class UzmanVerisiHatasi(ValueError):
    pass


def tam_uzmanlar(puanlar: Mapping[str, Mapping[str, float]]) -> list[str]:
    """13 göstergenin tümünü puanlamış uzmanlar."""
    return sorted(u for u, p in puanlar.items() if all(g in p and p[g] is not None for g in GOSTERGELER))


def dogrula(puanlar: Mapping[str, Mapping[str, float]], olcek_min: float, olcek_max: float) -> None:
    if olcek_max <= olcek_min:
        raise UzmanVerisiHatasi("Ölçek üst sınırı alt sınırdan büyük olmalı")
    for u, p in puanlar.items():
        for g, v in p.items():
            if g not in GOSTERGELER:
                raise UzmanVerisiHatasi(f"{u}: bilinmeyen gösterge {g}")
            if not (olcek_min <= v <= olcek_max):
                raise UzmanVerisiHatasi(f"{u}/{g}: {v} puanı ölçek dışında [{olcek_min}, {olcek_max}]")


def _siralar(degerler: Sequence[float]) -> list[float]:
    """Ortalama sıra (bağlar paylaşılır); en küçük değer 1."""
    sirali = sorted(range(len(degerler)), key=lambda i: degerler[i])
    sira = [0.0] * len(degerler)
    i = 0
    while i < len(sirali):
        j = i
        while j + 1 < len(sirali) and degerler[sirali[j + 1]] == degerler[sirali[i]]:
            j += 1
        ort = (i + j) / 2 + 1
        for k in range(i, j + 1):
            sira[sirali[k]] = ort
        i = j + 1
    return sira


def kendall_w(puanlar: Mapping[str, Mapping[str, float]]) -> Optional[float]:
    """Kendall W ∈ [0,1]; 1 = uzmanlar göstergeleri aynı sıraya dizdi. En az 2 uzman gerekir.
    Bir uzman tüm göstergelere aynı puanı verdiyse sıraları ayırt edici olmadığından W tanımsızdır."""
    uzmanlar = tam_uzmanlar(puanlar)
    m, n = len(uzmanlar), len(GOSTERGELER)
    if m < 2:
        return None
    toplam_sira = [0.0] * n
    bag_duzeltmesi = 0.0
    for u in uzmanlar:
        v = [puanlar[u][g] for g in GOSTERGELER]
        for i, r in enumerate(_siralar(v)):
            toplam_sira[i] += r
        for deger in set(v):
            t = v.count(deger)
            bag_duzeltmesi += t ** 3 - t
    ort = m * (n + 1) / 2
    s = sum((r - ort) ** 2 for r in toplam_sira)
    payda = m * m * (n ** 3 - n) - m * bag_duzeltmesi
    if payda <= 0:
        return None
    return max(0.0, min(1.0, 12 * s / payda))


def agirliklari_hesapla(puanlar: Mapping[str, Mapping[str, float]], birlestirme: str = "ortalama") -> dict:
    """Uzman puanlarından ağırlık. Yalnızca 13 göstergeyi de puanlamış uzmanlar kullanılır."""
    if birlestirme not in ("ortalama", "medyan"):
        raise UzmanVerisiHatasi("birlestirme: ortalama | medyan")
    uzmanlar = tam_uzmanlar(puanlar)
    if not uzmanlar:
        raise UzmanVerisiHatasi("13 göstergenin tümünü puanlamış uzman yok")
    f = statistics.fmean if birlestirme == "ortalama" else statistics.median
    ham = {g: float(f(puanlar[u][g] for u in uzmanlar)) for g in GOSTERGELER}
    toplam = sum(ham.values())
    if toplam <= 0:
        raise UzmanVerisiHatasi("Puanların toplamı sıfır; ağırlık türetilemez")
    return {
        "agirliklar": {g: ham[g] / toplam for g in GOSTERGELER},
        "birlesik_puan": ham,
        "uzman_sayisi": len(uzmanlar),
        "birlestirme": birlestirme,
        "kendall_w": kendall_w(puanlar),
        "yayilim": {g: _yayilim([puanlar[u][g] for u in uzmanlar]) for g in GOSTERGELER},
    }


def _yayilim(v: Sequence[float]) -> dict:
    return {"min": min(v), "max": max(v), "std": statistics.pstdev(v) if len(v) > 1 else 0.0}
