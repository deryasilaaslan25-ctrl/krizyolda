"""Instagram Graph API — işletme/içerik üreticisi hesabı (ig_user_id) ve erişim belirteci ile.

* Hesabın gönderileri (/{ig-user-id}/media) ve her gönderinin yorumları (/{media-id}/comments).
* Hesabın etiketlendiği herkese açık gönderiler (/{ig-user-id}/tags).
Hashtag araması ve keyfi marka bahsetme araması bu API ile sınırlıdır ve kapsam dışıdır."""
from __future__ import annotations

from datetime import datetime

import httpx

from app.collectors.base import ZAMAN_ASIMI, KaynakDurumu, KaynakHatasi, Toplanan, atlandi, bitir, istek, iso_utc
from app.config import settings

GONDERI_SINIRI = 50
SAYFA_SINIRI = 10
BELGE: list[str] = []


def _taban() -> str:
    return f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_SURUMU}"


async def _al(istemci, yol_veya_url: str, belirtec: str, **p):
    url = yol_veya_url if yol_veya_url.startswith("http") else f"{_taban()}/{yol_veya_url}"
    sayfa_url = yol_veya_url.startswith("http")          # paging.next adresi belirteci kendisi taşır
    r = await istek(istemci, url, params=None if sayfa_url else {**p, "access_token": belirtec})
    d = r.json()
    if "error" in d:
        hata = d["error"]
        kod = "yetki" if hata.get("code") in (10, 190, 200) or hata.get("type") == "OAuthException" else "bicim"
        raise KaynakHatasi(kod, f"Instagram: {hata.get('message', 'bilinmeyen hata')}")
    return d


def _tarih(s: str) -> datetime:
    return iso_utc(s.replace("+0000", "+00:00"))


async def baglanti_test(belirtec: str, ig_user_id: str, istemci: httpx.AsyncClient | None = None) -> dict:
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI)
    try:
        d = await _al(istemci, ig_user_id, belirtec, fields="username,media_count")
        return {"hesap": d.get("username"), "gonderi_sayisi": d.get("media_count"),
                "veri_turleri": ["hesap gönderileri", "gönderi yorumları", "hesabı etiketleyen gönderiler"],
                "tarih_siniri": "Son 50 gönderi ve yorumları", "kota": "Graph API uygulama düzeyi hız sınırı"}
    finally:
        if kendi:
            await istemci.aclose()


async def topla(terimler: list[str], bas: datetime, bit: datetime, belirtec: str, ig_user_id: str,
                istemci: httpx.AsyncClient | None = None) -> tuple[list[Toplanan], KaynakDurumu]:
    if not belirtec or not ig_user_id:
        return atlandi("instagram", "Instagram bağlantısı yapılmamış", bas, bit)
    kendi = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=ZAMAN_ASIMI)
    sonuc: dict[str, Toplanan] = {}
    hata: Exception | None = None
    alanlar = "id,caption,timestamp,permalink,like_count,comments_count,username"
    gonderiler: list[dict] = []
    try:
        d = await _al(istemci, f"{ig_user_id}/media", belirtec, fields=alanlar, limit=50)
        for _ in range(SAYFA_SINIRI):
            gonderiler += d.get("data", [])
            sonraki = d.get("paging", {}).get("next")
            if not sonraki or len(gonderiler) >= GONDERI_SINIRI:
                break
            d = await _al(istemci, sonraki, belirtec)
        for g in gonderiler[:GONDERI_SINIRI]:
            t = _tarih(g["timestamp"])
            if bas <= t < bit:
                sonuc["m_" + g["id"]] = Toplanan(
                    platform="instagram", tur="sosyal", dis_id="m_" + g["id"], yazar=g.get("username") or ig_user_id,
                    metin=g.get("caption", "") or "", url=g.get("permalink", ""), tarih=t,
                    begeni=int(g.get("like_count", 0) or 0), yorum=int(g.get("comments_count", 0) or 0),
                    erisim="bagli", icerik_turu="gonderi")
            if not g.get("comments_count"):
                continue
            c = await _al(istemci, f"{g['id']}/comments", belirtec, fields="id,text,timestamp,username,like_count", limit=100)
            for _ in range(SAYFA_SINIRI):
                for y in c.get("data", []):
                    ty = _tarih(y["timestamp"])
                    if bas <= ty < bit:
                        sonuc["c_" + y["id"]] = Toplanan(
                            platform="instagram", tur="sosyal", dis_id="c_" + y["id"], yazar=y.get("username"),
                            metin=y.get("text", ""), url=g.get("permalink", ""), tarih=ty,
                            begeni=int(y.get("like_count", 0) or 0), erisim="bagli", icerik_turu="yorum")
                sonraki = c.get("paging", {}).get("next")
                if not sonraki:
                    break
                c = await _al(istemci, sonraki, belirtec)
        e = await _al(istemci, f"{ig_user_id}/tags", belirtec, fields=alanlar, limit=50)
        for g in e.get("data", []):
            t = _tarih(g["timestamp"])
            if bas <= t < bit:
                sonuc["t_" + g["id"]] = Toplanan(
                    platform="instagram", tur="sosyal", dis_id="t_" + g["id"], yazar=g.get("username"),
                    metin=g.get("caption", "") or "", url=g.get("permalink", ""), tarih=t,
                    begeni=int(g.get("like_count", 0) or 0), yorum=int(g.get("comments_count", 0) or 0),
                    erisim="bagli", icerik_turu="bahsetme")
    except KaynakHatasi as ex:
        hata = ex
    finally:
        if kendi:
            await istemci.aclose()
    liste, dur = bitir("instagram", list(sonuc.values()), bas, bit, hata, belge=BELGE)
    gonderi_zamanlari = [o.tarih for o in liste if o.icerik_turu == "gonderi"]
    if dur.durum == "tamam" and len(gonderiler) >= GONDERI_SINIRI and gonderi_zamanlari and min(gonderi_zamanlari) > bas:
        dur.durum = "kismi"
        dur.mesaj = f"Yalnız son {GONDERI_SINIRI} gönderi tarandı; daha eski gönderilerin yorumları alınmadı."
    return liste, dur
