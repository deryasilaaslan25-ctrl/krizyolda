"""Bing Haber RSS (anahtarsız): bing.com/news/search?q=...&format=rss. Tarih aralığı parametresi yoktur; yalnız Bing'in
döndürdüğü güncel öğeler alınır. İstenen aralığın başına ulaşılamazsa durum 'kismi' olur ve ulaşılan aralık yazılır."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

import httpx

from app.collectors.base import ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, bitir, istek
from app.collectors.google_news import rss_ayristir

URL = "https://www.bing.com/news/search"


def _gercek_url(link: str) -> str:
    q = parse_qs(urlparse(link).query)
    return q["url"][0] if "url" in q else link


async def topla(terimler: list[str], bas: datetime, bit: datetime,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI, follow_redirects=True)
    hepsi: dict[str, Toplanan] = {}
    hata: Exception | None = None
    try:
        for t in terimler:
            r = await istek(istemci, URL, params={"q": f'"{t}"', "format": "rss", "setmkt": "tr-TR", "setlang": "tr"})
            for i in rss_ayristir(r.text, "bing_news"):
                i.url = _gercek_url(i.url)
                i.dis_id = i.url[:255]
                hepsi[i.dis_id] = i
    except KaynakHatasi as e:
        hata = e
    except ET.ParseError as e:
        hata = KaynakHatasi("bicim", f"RSS çözümlenemedi: {e}")
    finally:
        if kendi:
            await istemci.aclose()
    liste = [i for i in hepsi.values() if bas <= i.tarih < bit]
    en_eski = min((i.tarih for i in hepsi.values()), default=None)
    liste, d = bitir("bing_news", liste, bas, bit, hata, ulasilan_bas=en_eski if en_eski and en_eski > bas else None)
    if d.durum == "tamam" and en_eski is not None and en_eski > bas:
        d.durum = "kismi"
        d.mesaj = f"Bing yalnız {en_eski:%d.%m.%Y} sonrasını döndürdü; öncesi bu kaynaktan alınamaz."
    return liste, d
