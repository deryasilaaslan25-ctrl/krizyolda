"""Reddit genel arama (kimlik doğrulamasız): reddit.com/search.json. Reddit anonim istekleri sınırlayabilir ya da
engelleyebilir (özellikle sunucu IP'lerinde); bu durumda kaynak 'hata' olarak raporlanır, sıfır içerik sayılmaz.
Yalnız gönderiler alınır; yorumlar bu modda toplanmaz."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.collectors.base import ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, bitir, istek

URL = "https://www.reddit.com/search.json"
SAYFA_SINIRI = 5
ISTEK_ARASI_SN = 1.2
UA = "web:krizyolda:1.0 (itibar izleme)"


def _t(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)


def _zaman_filtresi(bas: datetime, simdi: datetime) -> str:
    fark = (simdi - bas).days
    return "week" if fark <= 7 else "month" if fark <= 31 else "year"


async def topla(terimler: list[str], bas: datetime, bit: datetime,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI, follow_redirects=True)
    sonuc: dict[str, Toplanan] = {}
    hata: Exception | None = None
    try:
        for t in terimler:
            after = None
            for _ in range(SAYFA_SINIRI):
                p = {"q": f'"{t}"', "sort": "new", "limit": 100, "t": _zaman_filtresi(bas, bit), "type": "link", "raw_json": 1}
                if after:
                    p["after"] = after
                r = await istek(istemci, URL, params=p, headers={"User-Agent": UA})
                veri = r.json().get("data", {})
                cocuk = veri.get("children", [])
                for c in cocuk:
                    d = c.get("data", {})
                    if not d.get("id"):
                        continue
                    tarih = _t(d.get("created_utc", 0))
                    if tarih < bas or tarih >= bit:
                        continue
                    sonuc["t3_" + d["id"]] = Toplanan(
                        platform="reddit", tur="sosyal", dis_id="t3_" + d["id"], yazar=d.get("author"),
                        baslik=d.get("title", ""), metin=f'{d.get("title", "")}. {d.get("selftext", "")}'.strip(),
                        url="https://www.reddit.com" + d.get("permalink", ""), tarih=tarih,
                        begeni=int(d.get("ups", 0) or 0), yorum=int(d.get("num_comments", 0) or 0), icerik_turu="gonderi")
                after = veri.get("after")
                if not after or not cocuk or _t(cocuk[-1].get("data", {}).get("created_utc", 0)) < bas:
                    break
                await asyncio.sleep(ISTEK_ARASI_SN)
            await asyncio.sleep(ISTEK_ARASI_SN)
    except KaynakHatasi as e:
        hata = e
    except ValueError as e:
        hata = KaynakHatasi("bicim", f"Reddit yanıtı çözümlenemedi: {e}")
    finally:
        if kendi:
            await istemci.aclose()
    return bitir("reddit", list(sonuc.values()), bas, bit, hata,
                 mesaj="Yalnız gönderiler (yorumlar bu modda alınmaz)")
