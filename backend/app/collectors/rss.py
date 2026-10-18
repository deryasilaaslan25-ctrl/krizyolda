"""Kurumun ve sistemin tanımladığı RSS kaynakları; başlık/açıklamada kurum terimi geçen öğeler alınır."""
from __future__ import annotations

from datetime import datetime
import xml.etree.ElementTree as ET

import httpx

from app.collectors.base import ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, atlandi, bitir, istek
from app.collectors.google_news import rss_ayristir
from app.nlp.normalize import tr_kucuk


def terim_geciyor(metin: str, terimler: list[str]) -> bool:
    m = tr_kucuk(metin)
    return any(tr_kucuk(t) in m for t in terimler)


async def topla(adresler: list[str], terimler: list[str], bas: datetime, bit: datetime,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    if not adresler:
        return atlandi("rss", "RSS adresi tanımlı değil", bas, bit)
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI, follow_redirects=True)
    sonuc: list[Toplanan] = []
    hatalar: list[str] = []
    try:
        for a in adresler:
            try:
                r = await istek(istemci, a)
                sonuc += [i for i in rss_ayristir(r.text, "rss")
                          if terim_geciyor(i.metin, terimler) and bas <= i.tarih < bit]
            except (KaynakHatasi, ET.ParseError) as e:
                hatalar.append(f"{a}: {str(e)[:120]}")
    finally:
        if kendi:
            await istemci.aclose()
    hata = KaynakHatasi("ag", "; ".join(hatalar)) if hatalar else None
    if hata and len(hatalar) == len(adresler) and not sonuc:
        return bitir("rss", sonuc, bas, bit, hata)
    liste, d = bitir("rss", sonuc, bas, bit, hata)
    # RSS beslemeleri yalnız son öğeleri tutar; erişilen en eski tarih ulaşılan aralığın başıdır.
    d.ulasilan_bas = min((o.tarih for o in sonuc), default=bas) if sonuc else bas
    return liste, d
