"""Google Haber RSS (anahtarsız): news.google.com/rss/search?q=...&hl=tr&gl=TR&ceid=TR:tr
Resmî bir API olarak belgelenmemiştir; biçim ve davranış değişebilir. Sorgu başına en çok 100 öğe döner, bu yüzden tarih
aralığı `after:`/`before:` işleçleriyle haftalık dilimlere bölünür; dilim 100 öğeye ulaşırsa yarıya bölünür."""
from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx

from app.collectors.base import (ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, bitir, dilimle, istek, utc_naive)

URL = "https://news.google.com/rss/search"
_ETIKET = re.compile(r"<[^>]+>")
SAYFA_SINIRI = 100
ISTEK_ARASI_SN = 0.4


def rss_ayristir(xml_metni: str, platform: str, tur: str = "haber") -> list[Toplanan]:
    kok = ET.fromstring(xml_metni)
    sonuc: list[Toplanan] = []
    for item in kok.iter("item"):
        baslik = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link or baslik).strip()
        aciklama = _ETIKET.sub(" ", item.findtext("description") or "")
        yazar = None
        for alt in item:
            if alt.tag == "source" or alt.tag.endswith("}Source"):
                yazar = (alt.text or "").strip() or None
        yazar = yazar or item.findtext("author")
        tarih_s = item.findtext("pubDate")
        if not tarih_s:
            continue
        try:
            tarih = utc_naive(parsedate_to_datetime(tarih_s))
        except (TypeError, ValueError):
            continue
        metin = baslik if platform in ("google_news", "bing_news") else f"{baslik}. {aciklama}".strip()
        sonuc.append(Toplanan(platform=platform, tur=tur, dis_id=guid[:255], metin=metin, tarih=tarih, yazar=yazar,
                              baslik=baslik, url=link, icerik_turu="haber"))
    return sonuc


async def _dilim(istemci, terim: str, a: datetime, b: datetime, hepsi: dict[str, Toplanan], kisaltildi: list) -> None:
    q = f'"{terim}" after:{a:%Y-%m-%d} before:{(b + timedelta(days=1)):%Y-%m-%d}'
    r = await istek(istemci, URL, params={"q": q, "hl": "tr", "gl": "TR", "ceid": "TR:tr"})
    liste = rss_ayristir(r.text, "google_news")
    for i in liste:
        hepsi[i.dis_id] = i
    if len(liste) >= SAYFA_SINIRI:
        if (b - a) > timedelta(days=1):
            orta = a + (b - a) / 2
            await asyncio.sleep(ISTEK_ARASI_SN)
            await _dilim(istemci, terim, a, orta, hepsi, kisaltildi)
            await asyncio.sleep(ISTEK_ARASI_SN)
            await _dilim(istemci, terim, orta, b, hepsi, kisaltildi)
        else:
            kisaltildi.append(f"{terim} {a:%Y-%m-%d}")


async def topla(terimler: list[str], bas: datetime, bit: datetime,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI, follow_redirects=True)
    hepsi: dict[str, Toplanan] = {}
    kisaltildi: list[str] = []
    hata: Exception | None = None
    try:
        for t in terimler:
            for a, b in dilimle(bas, bit, 7):
                await _dilim(istemci, t, a, b, hepsi, kisaltildi)
                await asyncio.sleep(ISTEK_ARASI_SN)
    except KaynakHatasi as e:
        hata = e
    except ET.ParseError as e:
        hata = KaynakHatasi("bicim", f"RSS çözümlenemedi: {e}")
    finally:
        if kendi:
            await istemci.aclose()
    liste = [i for i in hepsi.values() if bas <= i.tarih < bit]
    mesaj = ("Gün başına 100 öğe sınırına ulaşıldı, bazı haberler eksik olabilir: " + "; ".join(kisaltildi[:5])) if kisaltildi else ""
    liste, d = bitir("google_news", liste, bas, bit, hata, mesaj=mesaj)
    if kisaltildi and d.durum == "tamam":
        d.durum = "kismi"
    return liste, d
