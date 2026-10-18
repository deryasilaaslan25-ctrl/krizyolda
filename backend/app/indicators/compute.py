"""
Pencere düzeyinde G1–G13 ve Q1 ölçümü (Rapor Bölüm 2 "Ölçüm" sütunu; Bölüm 3.1).

Veri yoksa gösterge 0'a zorlanmaz, eksik (None) kabul edilir; sayım ile
eksik ayrımı Tasarım kararı 13. Sosyal / haber ayrımı Tasarım kararı 11.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence

from app.nlp.coordination import kopya_orani


@dataclass
class IslenmisIcerik:
    """Toplanmış ve NLP'den geçmiş tek içerik."""
    kimlik: str
    platform: str
    tur: str                    # "sosyal" | "haber"
    yazar: Optional[str]
    metin: str
    tarih: datetime
    begeni: int = 0
    yorum: int = 0
    paylasim: int = 0
    duygu_etiketi: Optional[str] = None   # olumsuz | olumlu | notr | None
    olumlu: int = 0
    olumsuz: int = 0
    ofke: int = 0
    korku: int = 0
    igrenme: int = 0
    toplam_sozcuk: int = 0
    scct_seviye: int = 0
    scct_kume: Optional[str] = None
    scct_tip: Optional[str] = None
    niyet: list[str] = field(default_factory=list)


def janis_fadner(f: int, u: int, toplam: int) -> Optional[float]:
    """[DEEPHOUSE2000; JANIS_FADNER1965]
    JF = (f² − fu)/N² (f > u); 0 (f = u); (fu − u²)/N² (u > f)."""
    if toplam <= 0:
        return None
    if f > u:
        return (f * f - f * u) / (toplam * toplam)
    if u > f:
        return (f * u - u * u) / (toplam * toplam)
    return 0.0


@dataclass
class Baglam:
    """Bir pencerenin ölçüm bağlamı. *_kaynak_var: pencereyi kapsayan başarılı bir tarama var; yoksa sayım göstergesi
    sıfır değil eksiktir (Tasarım kararı 13)."""
    sosyal_kaynak_var: bool
    haber_kaynak_var: bool
    duygu_var: bool          # sözlük ya da TurkishBERTweet mevcut
    uyarilmislik_var: bool   # NRC sözlüğü mevcut (G8–G10)
    kapsayan_platformlar: frozenset = frozenset()   # pencereyi kapsayan kaynaklar; G11 paydası


def _oran(pay: float, payda: float) -> Optional[float]:
    return pay / payda if payda > 0 else None


def pencere_olc(icerikler: Sequence[IslenmisIcerik], trends: Optional[float], b: Baglam) -> dict:
    sosyal = [i for i in icerikler if i.tur == "sosyal"]
    haber = [i for i in icerikler if i.tur == "haber"]
    g: dict[str, Optional[float]] = {}

    # DİKKAT
    g["G1"] = float(len(sosyal)) if b.sosyal_kaynak_var else None
    g["G2"] = float(len({i.yazar if i.yazar else f"?{i.kimlik}" for i in sosyal})) if b.sosyal_kaynak_var else None
    g["G4"] = trends
    g["G5"] = float(len(haber)) if b.haber_kaynak_var else None
    # YAYILIM (G3)
    g["G3"] = float(sum(i.begeni + i.yorum + i.paylasim for i in sosyal)) if b.sosyal_kaynak_var else None
    # TONALİTE
    g["G6"] = _oran(sum(1 for i in sosyal if i.duygu_etiketi == "olumsuz"), len(sosyal)) if b.duygu_var else None
    if b.duygu_var and haber:
        f = sum(1 for i in haber if i.duygu_etiketi == "olumlu")
        u = sum(1 for i in haber if i.duygu_etiketi == "olumsuz")
        jf = janis_fadner(f, u, len(haber))
        g["G7"] = -jf if jf is not None else None
    else:
        g["G7"] = None
    # UYARILMIŞLIK
    toplam = sum(i.toplam_sozcuk for i in sosyal)
    if b.uyarilmislik_var:
        g["G8"] = _oran(sum(i.ofke for i in sosyal), toplam)
        g["G9"] = _oran(sum(i.korku for i in sosyal), toplam)
        g["G10"] = _oran(sum(i.igrenme for i in sosyal), toplam)
    else:
        g["G8"] = g["G9"] = g["G10"] = None
    # YAYILIM (G11): payda, pencereyi kapsayan kaynakların sayısıdır (içerik gelen platformların değil)
    if b.duygu_var and b.kapsayan_platformlar:
        olumsuz_platform = {i.platform for i in icerikler if i.duygu_etiketi == "olumsuz"} & set(b.kapsayan_platformlar)
        g["G11"] = len(olumsuz_platform) / len(b.kapsayan_platformlar)
    else:
        g["G11"] = None
    # NİYET
    g["G12"] = _oran(sum(1 for i in sosyal if i.niyet), len(sosyal))
    # SORUMLULUK
    g["G13"] = _oran(sum(i.scct_seviye for i in icerikler), len(icerikler))
    # KALİTE (formüle girmez)
    g["Q1"] = kopya_orani([(i.yazar or f"?{i.kimlik}", i.metin) for i in sosyal])
    return g
