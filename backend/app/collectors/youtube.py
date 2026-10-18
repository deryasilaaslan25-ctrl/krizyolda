"""YouTube Data API v3 — kurumun kendi API anahtarı ve kanal kimliğiyle.

* Kanalın yükleme listesi (playlistItems, 1 kota birimi/çağrı) → son videolar → her videonun yorumları (commentThreads,
  1 birim/çağrı). Yorumlar tarih aralığına göre süzülür; video aralıktan eski olsa da yeni yorumları alınır.
* Marka bahsetmeleri: search.list (100 birim/çağrı); kota nedeniyle terim başına en çok 2 sayfa.
Günlük kota tükenirse elde edilen veri korunur ve durum 'kismi' olur."""
from __future__ import annotations

from datetime import datetime

import httpx

from app.collectors.base import ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, bitir, istek, iso_utc, atlandi

API = "https://www.googleapis.com/youtube/v3"
BELGE = ["YOUTUBE_QUOTA_DOC"]
KANAL_VIDEO_SINIRI = 50
YORUM_SAYFA_SINIRI = 10
ARAMA_SAYFA_SINIRI = 2


def _hata_cevir(e: KaynakHatasi) -> KaynakHatasi:
    if e.kod == "yetki" and "quota" in str(e).lower():
        return KaynakHatasi("kota", "YouTube günlük kotası doldu")
    return e


async def _al(istemci, yol: str, anahtar: str, **p):
    try:
        return (await istek(istemci, f"{API}/{yol}", params={**p, "key": anahtar})).json()
    except KaynakHatasi as e:
        raise _hata_cevir(e)


def _video(v: dict, tur: str = "gonderi") -> Toplanan:
    sn, st = v.get("snippet", {}), v.get("statistics", {})
    return Toplanan(platform="youtube", tur="sosyal", dis_id="v_" + v["id"], yazar=sn.get("channelId") or sn.get("channelTitle"),
                    baslik=sn.get("title", ""), metin=f'{sn.get("title", "")}. {sn.get("description", "")}'.strip(),
                    url=f"https://www.youtube.com/watch?v={v['id']}", tarih=iso_utc(sn["publishedAt"]),
                    begeni=int(st.get("likeCount", 0) or 0), yorum=int(st.get("commentCount", 0) or 0),
                    erisim="bagli", icerik_turu=tur)


async def _video_ayrintilari(istemci, anahtar: str, idler: list[str]) -> list[dict]:
    sonuc = []
    for i in range(0, len(idler), 50):
        d = await _al(istemci, "videos", anahtar, part="snippet,statistics", id=",".join(idler[i:i + 50]))
        sonuc += d.get("items", [])
    return sonuc


async def _yorumlar(istemci, anahtar: str, video_id: str, bas: datetime, bit: datetime, cikti: dict) -> None:
    token = None
    for _ in range(YORUM_SAYFA_SINIRI):
        p = {"part": "snippet", "videoId": video_id, "maxResults": 100, "order": "time", "textFormat": "plainText"}
        if token:
            p["pageToken"] = token
        try:
            d = await _al(istemci, "commentThreads", anahtar, **p)
        except KaynakHatasi as e:
            if e.kod in ("bicim", "yetki") and "quota" not in str(e).lower():
                return                          # yorumlar kapalı olabilir
            raise
        eskiye_ulasti = False
        for th in d.get("items", []):
            ts = th.get("snippet", {})
            c = ts.get("topLevelComment", {}).get("snippet", {})
            if not c.get("publishedAt"):
                continue
            t = iso_utc(c["publishedAt"])
            if t < bas:
                eskiye_ulasti = True
                continue
            if t >= bit:
                continue
            yazar = (c.get("authorChannelId") or {}).get("value") or c.get("authorDisplayName")
            cikti["c_" + th["id"]] = Toplanan(
                platform="youtube", tur="sosyal", dis_id="c_" + th["id"], yazar=yazar,
                metin=c.get("textOriginal") or c.get("textDisplay", ""),
                url=f"https://www.youtube.com/watch?v={video_id}&lc={th['id']}", tarih=t,
                begeni=int(c.get("likeCount", 0) or 0), yorum=int(ts.get("totalReplyCount", 0) or 0),
                erisim="bagli", icerik_turu="yorum")
        token = d.get("nextPageToken")
        if not token or eskiye_ulasti:
            return


async def baglanti_test(anahtar: str, kanal_id: str, istemci: httpx.AsyncClient | None = None) -> dict:
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI)
    try:
        d = await _al(istemci, "channels", anahtar, part="snippet,statistics", id=kanal_id)
        if not d.get("items"):
            raise KaynakHatasi("bicim", "Bu kanal kimliği bulunamadı")
        k = d["items"][0]
        return {"hesap": k["snippet"].get("title"), "video_sayisi": k["statistics"].get("videoCount"),
                "veri_turleri": ["kanal videoları", "video yorumları", "marka aramaları"],
                "tarih_siniri": "Yorumlar için API tarih sınırı yok; kanalın son 50 videosu taranır",
                "kota": "Günlük 10.000 birim (search.list 100 birim)"}
    finally:
        if kendi:
            await istemci.aclose()


async def topla(terimler: list[str], bas: datetime, bit: datetime, anahtar: str, kanal_id: str,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    if not anahtar:
        return atlandi("youtube", "YouTube bağlantısı yapılmamış", bas, bit)
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI)
    sonuc: dict[str, Toplanan] = {}
    hata: Exception | None = None
    try:
        if kanal_id:
            kanal = await _al(istemci, "channels", anahtar, part="contentDetails", id=kanal_id)
            yukleme = ((kanal.get("items") or [{}])[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"))
            if not yukleme:
                raise KaynakHatasi("bicim", "Kanalın yükleme listesi bulunamadı")
            idler: list[str] = []
            token = None
            while len(idler) < KANAL_VIDEO_SINIRI:
                p = {"part": "contentDetails", "playlistId": yukleme, "maxResults": 50}
                if token:
                    p["pageToken"] = token
                d = await _al(istemci, "playlistItems", anahtar, **p)
                idler += [i["contentDetails"]["videoId"] for i in d.get("items", [])]
                token = d.get("nextPageToken")
                if not token:
                    break
            for v in await _video_ayrintilari(istemci, anahtar, idler[:KANAL_VIDEO_SINIRI]):
                if bas <= iso_utc(v["snippet"]["publishedAt"]) < bit:
                    sonuc["v_" + v["id"]] = _video(v)
                await _yorumlar(istemci, anahtar, v["id"], bas, bit, sonuc)
        bulunan: list[str] = []
        for t in terimler:
            token = None
            for _ in range(ARAMA_SAYFA_SINIRI):
                p = {"part": "snippet", "q": f'"{t}"', "type": "video", "order": "date", "maxResults": 50,
                     "publishedAfter": bas.strftime("%Y-%m-%dT%H:%M:%SZ"), "publishedBefore": bit.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "regionCode": "TR", "relevanceLanguage": "tr"}
                if token:
                    p["pageToken"] = token
                d = await _al(istemci, "search", anahtar, **p)
                bulunan += [i["id"]["videoId"] for i in d.get("items", []) if i.get("id", {}).get("videoId")]
                token = d.get("nextPageToken")
                if not token:
                    break
        yeni = [i for i in dict.fromkeys(bulunan) if "v_" + i not in sonuc]
        for v in await _video_ayrintilari(istemci, anahtar, yeni):
            sonuc["v_" + v["id"]] = _video(v, "bahsetme")
    except KaynakHatasi as e:
        hata = e
    finally:
        if kendi:
            await istemci.aclose()
    return bitir("youtube", list(sonuc.values()), bas, bit, hata, belge=BELGE)
