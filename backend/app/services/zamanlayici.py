"""Uyarlamalı tarama sıklığı: sistem veriyi sürekli toplar; aralığı kuruma özgü risk seviyesine göre, kurumun izin verdiği
alt-üst sınır içinde seçer. Bildirim sıklığı bundan bağımsızdır (alarm_servisi)."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.config import settings
from app.models.orm import Kullanici

# Log ölçekte alt-üst sınır arasındaki konum: 0 = en uzun aralık, 1 = en kısa aralık
_KONUM = {0: 0.0, 1: 0.75, 2: 0.92, 3: 1.0}


def sinirlar(k: Kullanici) -> tuple[int, int]:
    alt = max(settings.TARAMA_ARALIGI_MIN, int(k.tarama_min_dk or settings.TARAMA_ARALIGI_MIN))
    ust = min(settings.TARAMA_ARALIGI_MAX, int(k.tarama_max_dk or settings.TARAMA_ARALIGI_MAX))
    return alt, max(alt, ust)


def aralik_sec(k: Kullanici, seviye: int, hacim_sok: bool = False) -> int:
    """Seviye 0 → üst sınır; 3 → alt sınır. Hacim şoku varsa en az 'Orta' sıklığı uygulanır."""
    alt, ust = sinirlar(k)
    if hacim_sok:
        seviye = max(seviye, 1)
    f = _KONUM.get(max(0, min(3, seviye)), 0.0)
    return int(round(ust * (alt / ust) ** f))


def sonraki_tarama(k: Kullanici, simdi: datetime, seviye: int, hacim_sok: bool = False) -> datetime | None:
    """Tek seferlik planda sonraki tarama yoktur."""
    if k.tekrar_plani == "tek_seferlik":
        k.tarama_aralik_dk = None
        return None
    dk = aralik_sec(k, seviye, hacim_sok)
    k.tarama_aralik_dk = dk
    return simdi + timedelta(minutes=dk)
