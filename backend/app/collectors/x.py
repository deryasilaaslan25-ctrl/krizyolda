"""X API v2 — kurumun kendi taşıyıcı (bearer) token'ı ve hesabıyla.

Aralık 7 günden uzunsa önce tam arşiv araması (GET /2/tweets/search/all) denenir; erişim düzeyi yetmezse
son 7 gün araması (search/recent) ile devam edilir ve durum 'kismi' olarak ulaşılan aralıkla raporlanır."""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from app.collectors.base import (ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, atlandi, bitir, istek, iso_utc,
                                 utc_simdi)

RECENT = "https://api.x.com/2/tweets/search/recent"
ARSIV = "https://api.x.com/2/tweets/search/all"
BELGE = ["X_SEARCH_DOC", "X_PRICING_DOC"]
SAYFA_SINIRI = 20


def sorgu_olustur(terimler: list[str], hesap: str, sinir: int) -> str:
    parcalar = [f'"{t}"' for t in terimler]
    h = hesap.lstrip("@").strip()
    if h:
        parcalar += [f"@{h}", f"to:{h}"]
    sorgu = ""
    for p in parcalar:
        aday = (sorgu + " OR " + p) if sorgu else p
        if len(aday) + len(" -is:retweet") + 2 > sinir:
            break
        sorgu = aday
    return f"({sorgu}) -is:retweet"


def _tweet(tw: dict, yazarlar: dict[str, str]) -> Toplanan:
    pm = tw.get("public_metrics", {})
    return Toplanan(platform="x", tur="sosyal", dis_id=tw["id"], yazar=yazarlar.get(tw.get("author_id", ""), tw.get("author_id")),
                    metin=tw.get("text", ""), url=f"https://x.com/i/web/status/{tw['id']}", tarih=iso_utc(tw["created_at"]),
                    begeni=int(pm.get("like_count", 0)), yorum=int(pm.get("reply_count", 0)),
                    paylasim=int(pm.get("retweet_count", 0)) + int(pm.get("quote_count", 0)), erisim="bagli",
                    icerik_turu="bahsetme")


async def _ara(istemci, url: str, bearer: str, sorgu: str, bas: datetime, bit: datetime, sayfa_boyu: int, cikti: dict) -> None:
    token = None
    for _ in range(SAYFA_SINIRI):
        p = {"query": sorgu, "max_results": sayfa_boyu, "start_time": bas.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "end_time": bit.strftime("%Y-%m-%dT%H:%M:%SZ"), "tweet.fields": "created_at,public_metrics,author_id,lang",
             "expansions": "author_id", "user.fields": "username"}
        if token:
            p["next_token"] = token
        d = (await istek(istemci, url, params=p, headers={"Authorization": f"Bearer {bearer}"})).json()
        yazarlar = {u["id"]: u.get("username", u["id"]) for u in (d.get("includes", {}).get("users", []) or [])}
        for tw in d.get("data", []) or []:
            cikti[tw["id"]] = _tweet(tw, yazarlar)
        token = d.get("meta", {}).get("next_token")
        if not token:
            return


async def baglanti_test(bearer: str, istemci: httpx.AsyncClient | None = None) -> dict:
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI)
    try:
        simdi = utc_simdi()
        p = {"query": "krizyolda -is:retweet", "max_results": 10, "start_time": (simdi - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")}
        await istek(istemci, RECENT, params=p, headers={"Authorization": f"Bearer {bearer}"})
        arsiv = False
        try:
            await istek(istemci, ARSIV, params={**p, "start_time": (simdi - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                "end_time": (simdi - timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%SZ")},
                        headers={"Authorization": f"Bearer {bearer}"}, deneme=1)
            arsiv = True
        except KaynakHatasi:
            arsiv = False
        return {"veri_turleri": ["marka bahsetmeleri", "hesaba yanıtlar"],
                "tarih_siniri": "Tam arşiv (6 aya kadar) erişimi var" if arsiv else "Yalnız son 7 gün (arşiv erişimi yok)",
                "arsiv_erisimi": arsiv, "kota": "X API erişim düzeyine bağlı"}
    finally:
        if kendi:
            await istemci.aclose()


async def topla(terimler: list[str], bas: datetime, bit: datetime, bearer: str, hesap: str,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    if not bearer:
        return atlandi("x", "X bağlantısı yapılmamış", bas, bit)
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI)
    sonuc: dict[str, Toplanan] = {}
    hata: Exception | None = None
    ulas_bas: datetime | None = None
    mesaj = ""
    try:
        simdi = utc_simdi()
        yedi_gun = simdi - timedelta(days=7) + timedelta(minutes=5)
        arsiv_ok = False
        if bas < yedi_gun:
            try:
                await _ara(istemci, ARSIV, bearer, sorgu_olustur(terimler, hesap, 1024), bas, bit, 500, sonuc)
                arsiv_ok = True
            except KaynakHatasi as e:
                if e.kod != "yetki":
                    raise
                mesaj = "Tam arşiv erişimi yok; yalnız son 7 gün tarandı."
        if not arsiv_ok:
            sonuc.clear()
            ulas_bas = max(bas, yedi_gun)
            if ulas_bas < bit:
                await _ara(istemci, RECENT, bearer, sorgu_olustur(terimler, hesap, 512), ulas_bas, bit, 100, sonuc)
    except KaynakHatasi as e:
        hata = e
    finally:
        if kendi:
            await istemci.aclose()
    liste, d = bitir("x", list(sonuc.values()), bas, bit, hata, belge=BELGE, ulasilan_bas=ulas_bas, mesaj=mesaj)
    if d.durum == "tamam" and ulas_bas and ulas_bas > bas:
        d.durum = "kismi"
        d.mesaj = mesaj
    return liste, d
