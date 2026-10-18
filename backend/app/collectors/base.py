"""Toplayıcı ortak tipleri (Rapor Bölüm 6)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

ZAMAN_ASIMI = 20.0

# Kaynak (= içeriğin platform alanı) → sosyal | haber. G1/G2/G3/G6/G8–G10/G12 sosyal, G5/G7 haber kaynaklarından ölçülür.
KAYNAK_TURU = {"google_news": "haber", "bing_news": "haber", "rss": "haber",
               "reddit": "sosyal", "youtube": "sosyal", "x": "sosyal", "instagram": "sosyal"}
KAYNAK_ADI = {"google_news": "Google Haber", "bing_news": "Bing Haber", "rss": "RSS", "reddit": "Reddit",
              "youtube": "YouTube", "x": "X", "instagram": "Instagram", "google_trends": "Google Trends"}


@dataclass
class Toplanan:
    platform: str
    tur: str                 # sosyal | haber
    dis_id: str
    metin: str
    tarih: datetime          # UTC, tz'siz
    yazar: Optional[str] = None
    baslik: str = ""
    url: str = ""
    begeni: int = 0
    yorum: int = 0
    paylasim: int = 0
    erisim: str = "acik"         # acik | bagli
    icerik_turu: str = "bahsetme"  # bahsetme | yorum | gonderi | haber


@dataclass
class KaynakDurumu:
    """Bir kaynağın bir tarama işindeki gerçek durumu; içerik sayısından bağımsızdır."""
    kaynak: str
    durum: str               # tamam | kismi | atlandi | hata
    mesaj: str = ""
    adet: int = 0
    belge: list[str] = field(default_factory=list)   # literatur.KAYNAKLAR kimlikleri
    istenen_bas: Optional[datetime] = None
    istenen_bit: Optional[datetime] = None
    ulasilan_bas: Optional[datetime] = None          # kaynağın fiilen tarayabildiği aralık
    ulasilan_bit: Optional[datetime] = None


def utc_simdi() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_naive(t: datetime) -> datetime:
    if t.tzinfo is not None:
        t = t.astimezone(timezone.utc).replace(tzinfo=None)
    return t


def iso_utc(s: str) -> datetime:
    return utc_naive(datetime.fromisoformat(s.replace("Z", "+00:00")))


def sorgu_terimleri(kurum: str, terimler: list[str] | None) -> list[str]:
    liste = [kurum] + [t for t in (terimler or []) if t and t.strip()]
    goruldu, sonuc = set(), []
    for t in liste:
        k = t.strip()
        if k and k.lower() not in goruldu:
            goruldu.add(k.lower())
            sonuc.append(k)
    return sonuc


# ---------------------------------------------------------------------------
# Ortak HTTP ve tarih yardımcıları
# ---------------------------------------------------------------------------
import asyncio  # noqa: E402
from datetime import timedelta  # noqa: E402

import httpx  # noqa: E402


class KaynakHatasi(Exception):
    """kod: yetki | kota | ag | bicim"""

    def __init__(self, kod: str, mesaj: str):
        super().__init__(mesaj)
        self.kod = kod


def dilimle(bas: datetime, bit: datetime, gun: int) -> list[tuple[datetime, datetime]]:
    sonuc, a = [], bas
    while a < bit:
        b = min(a + timedelta(days=gun), bit)
        sonuc.append((a, b))
        a = b
    return sonuc


async def istek(istemci: httpx.AsyncClient, url: str, *, params: dict | None = None, headers: dict | None = None,
                deneme: int = 3) -> httpx.Response:
    """GET; 429/5xx'te artan bekleme (Retry-After'a uyar, en çok 30 sn). Kalıcı hatayı KaynakHatasi'na çevirir."""
    son: Exception | None = None
    for i in range(deneme):
        try:
            r = await istemci.get(url, params=params, headers=headers)
        except httpx.HTTPError as e:
            son = e
            await asyncio.sleep(min(2 ** i, 8))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            try:
                bekle = float(r.headers.get("Retry-After", 2 ** i))
            except ValueError:
                bekle = 2 ** i
            son = KaynakHatasi("kota" if r.status_code == 429 else "ag", f"HTTP {r.status_code}")
            if i < deneme - 1:
                await asyncio.sleep(min(bekle, 30))
            continue
        if r.status_code in (401, 403):
            raise KaynakHatasi("yetki", f"HTTP {r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:
            raise KaynakHatasi("bicim", f"HTTP {r.status_code}: {r.text[:200]}")
        return r
    if isinstance(son, KaynakHatasi):
        raise son
    raise KaynakHatasi("ag", str(son) if son else "bağlantı kurulamadı")


def bitir(kaynak: str, liste: list, bas: datetime, bit: datetime, hata: Exception | None, *, belge: list[str] | None = None,
          ulasilan_bas: datetime | None = None, mesaj: str = "") -> tuple[list, KaynakDurumu]:
    """Toplayıcının ortak çıkışı: veri + hata durumuna göre tamam | kismi | hata."""
    if hata is None:
        durum, m = "tamam", mesaj
    elif liste:
        durum, m = "kismi", f"{hata}" + (f" — {mesaj}" if mesaj else "")
    else:
        durum, m = "hata", f"{hata}"
    ulas_bit = bit if durum == "tamam" else (max((o.tarih for o in liste), default=None) if liste else None)
    ulas_bas = (ulasilan_bas or bas) if durum != "hata" else None
    return liste, KaynakDurumu(kaynak, durum, mesaj=m[:500], adet=len(liste), belge=belge or [],
                               istenen_bas=bas, istenen_bit=bit, ulasilan_bas=ulas_bas, ulasilan_bit=ulas_bit)


def atlandi(kaynak: str, mesaj: str, bas: datetime, bit: datetime) -> tuple[list, KaynakDurumu]:
    return [], KaynakDurumu(kaynak, "atlandi", mesaj=mesaj, istenen_bas=bas, istenen_bit=bit)
