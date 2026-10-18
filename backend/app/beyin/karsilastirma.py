"""1. beyin (eşit ağırlık) ile 2. beyin (uzman ağırlığı) sonuçlarının yan yana raporu."""
from __future__ import annotations

import math
from typing import Optional, Sequence

from app.detection import esik_kalibrasyonu as E
from app.literatur import ESIK_UZMAN_ONSEL, ISINMA_PENCERE, RISK_SEVIYE_ETIKETLERI, gosterge


def _pearson(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def _yuzdelik_yeri(deger: float, gecmis: Sequence[float]) -> Optional[float]:
    if not gecmis:
        return None
    return sum(1 for g in gecmis if g <= deger) / len(gecmis)


def karsilastir(sonuc: dict, brain1_ham_seviye: Optional[int], uzman_agirliklari: dict[str, float]) -> dict:
    """analiz_et çıktısındaki pencereler üzerinden iki beynin karşılaştırması.

    Karar 1. beyindedir; 2. beyin paralel raporlanır. 2. beynin seviyesi kendi R geçmişinden, aynı eşik metodolojisiyle
    (esik_kalibrasyonu.esik_hesapla, uzman önseliyle) bulunur; histerezis uygulanmaz, bu yüzden 'ham' seviyedir."""
    pen = sonuc["pencereler"]
    r1 = [p.get("risk_ham_puan") for p in pen]
    r2 = [p.get("risk_uzman") for p in pen]
    cift = [(a, b) for a, b in zip(r1[ISINMA_PENCERE:], r2[ISINMA_PENCERE:]) if a is not None and b is not None]
    son = pen[-1] if pen else {}
    son_r1, son_r2 = r1[-1] if r1 else None, r2[-1] if r2 else None
    gecmis2 = [b for b in r2[ISINMA_PENCERE:-1] if b is not None]
    esik2 = E.esik_hesapla(gecmis2, ESIK_UZMAN_ONSEL, "uzman") if son_r2 is not None else None
    seviye2 = E.seviye_ham(son_r2, esik2.esikler) if esik2 else None

    s = sonuc["son"]
    w1, w2 = s.get("agirliklar") or {}, s.get("uzman_agirliklar") or {}
    z1 = s.get("kirpilmis") or {}
    katki = []
    for kod in sorted(set(w1) | set(w2), key=lambda k: int(k[1:])):
        sk = z1.get(kod)
        k1 = w1.get(kod, 0.0) * sk if sk is not None else None
        k2 = w2.get(kod, 0.0) * sk if sk is not None else None
        katki.append({"kod": kod, "ad": gosterge(kod)["ad"], "w1": w1.get(kod), "w2": w2.get(kod), "skor": sk,
                      "katki1": k1, "katki2": k2,
                      "fark": (k2 - k1) if k1 is not None and k2 is not None else None})
    katki.sort(key=lambda x: -abs(x["fark"] or 0.0))

    seri = []
    for p, a, b in zip(pen, r1, r2):
        if a is not None and b is not None:
            seri.append({"bas": p["bas"], "r1": a, "r2": b})
    if len(seri) > 720:                                  # grafik için 6 saatlik bloklarda en yüksek değer
        blok = [seri[i:i + 6] for i in range(0, len(seri), 6)]
        seri = [{"bas": b[0]["bas"], "r1": max(x["r1"] for x in b), "r2": max(x["r2"] for x in b)} for b in blok]

    return {
        "etkin": True,
        "son": {"bas": son.get("bas"), "r1": son_r1, "r2": son_r2,
                "fark": (son_r2 - son_r1) if son_r1 is not None and son_r2 is not None else None,
                "z1": son.get("z"), "z2": son.get("z_uzman"),
                "seviye1": brain1_ham_seviye, "seviye2": seviye2,
                "etiket1": RISK_SEVIYE_ETIKETLERI[brain1_ham_seviye] if brain1_ham_seviye is not None else None,
                "etiket2": RISK_SEVIYE_ETIKETLERI[seviye2] if seviye2 is not None else None,
                "yuzdelik1": _yuzdelik_yeri(son_r1, [a for a in r1[ISINMA_PENCERE:-1] if a is not None]) if son_r1 is not None else None,
                "yuzdelik2": _yuzdelik_yeri(son_r2, gecmis2) if son_r2 is not None else None,
                "esikler2": list(esik2.esikler) if esik2 else None},
        "donem": {"n": len(cift),
                  "korelasyon": _pearson([a for a, _ in cift], [b for _, b in cift]),
                  "ortalama_mutlak_fark": (sum(abs(a - b) for a, b in cift) / len(cift)) if cift else None,
                  "r1_ortalama": (sum(a for a, _ in cift) / len(cift)) if cift else None,
                  "r2_ortalama": (sum(b for _, b in cift) / len(cift)) if cift else None},
        "katkilar": katki,
        "seri": seri,
    }
