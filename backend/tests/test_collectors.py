import asyncio
from datetime import datetime

import httpx
import respx

from app.collectors import bing_news, google_news, google_trends, instagram, reddit_acik, rss, x, youtube
from app.collectors.base import dilimle

BAS, BIT = datetime(2026, 9, 14), datetime(2026, 9, 28)
RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Anadolu Gıda yeni fabrika</title><link>https://ornek/1</link><guid>g1</guid>
<pubDate>Mon, 21 Sep 2026 10:00:00 GMT</pubDate><source url="https://a">Ajans A</source></item>
</channel></rss>"""


def test_dilimleme_aralik_sinirlarini_korur():
    d = dilimle(datetime(2026, 1, 1), datetime(2026, 1, 20), 7)
    assert d[0][0] == datetime(2026, 1, 1) and d[-1][1] == datetime(2026, 1, 20) and len(d) == 3


def test_google_news_haftalik_dilim_ve_tarih_filtresi():
    google_news.ISTEK_ARASI_SN = 0
    with respx.mock:
        yol = respx.get(google_news.URL).mock(return_value=httpx.Response(200, text=RSS))
        ogeler, d = asyncio.run(google_news.topla(["Anadolu Gıda"], BAS, BIT))
    assert yol.call_count == 2                                  # 14 gün = 2 haftalık dilim
    assert d.durum == "tamam" and len(ogeler) == 1 and ogeler[0].yazar == "Ajans A" and ogeler[0].icerik_turu == "haber"
    assert "after:2026-09-14" in str(yol.calls[0].request.url).replace("%3A", ":")


def test_google_news_tarih_disi_haber_elenir():
    google_news.ISTEK_ARASI_SN = 0
    with respx.mock:
        respx.get(google_news.URL).mock(return_value=httpx.Response(200, text=RSS))
        ogeler, d = asyncio.run(google_news.topla(["x"], datetime(2026, 10, 1), datetime(2026, 10, 8)))
    assert ogeler == [] and d.durum == "tamam"                  # başarılı tarama, kapsamda içerik yok = gerçek sıfır


def test_google_news_hata_sifir_icerik_degil_hata_olarak_raporlanir():
    google_news.ISTEK_ARASI_SN = 0
    with respx.mock:
        respx.get(google_news.URL).mock(return_value=httpx.Response(403, text="engellendi"))
        ogeler, d = asyncio.run(google_news.topla(["x"], BAS, BIT))
    assert d.durum == "hata" and ogeler == [] and "403" in d.mesaj and d.ulasilan_bas is None


def test_bing_aralik_basina_ulasamazsa_kismi():
    with respx.mock:
        respx.get(bing_news.URL).mock(return_value=httpx.Response(200, text=RSS))
        ogeler, d = asyncio.run(bing_news.topla(["x"], datetime(2026, 6, 1), BIT))
    assert d.durum == "kismi" and d.ulasilan_bas == datetime(2026, 9, 21, 10) and len(ogeler) == 1


def test_rss_terim_filtresi():
    with respx.mock:
        respx.get("https://ornek.com/feed").mock(return_value=httpx.Response(200, text=RSS))
        ogeler, d = asyncio.run(rss.topla(["https://ornek.com/feed"], ["Anadolu Gıda"], BAS, BIT))
        bos, _ = asyncio.run(rss.topla(["https://ornek.com/feed"], ["baska"], BAS, BIT))
    assert len(ogeler) == 1 and bos == []
    assert asyncio.run(rss.topla([], ["x"], BAS, BIT))[1].durum == "atlandi"


def test_reddit_acik_gonderi_ve_engel():
    reddit_acik.ISTEK_ARASI_SN = 0
    veri = {"data": {"after": None, "children": [{"kind": "t3", "data": {
        "id": "a1", "author": "u", "title": "Başlık", "selftext": "metin", "created_utc": 1790000000 - 86400 * 30,
        "ups": 5, "num_comments": 2, "permalink": "/r/x/a1"}}]}}
    with respx.mock:
        respx.get(reddit_acik.URL).mock(return_value=httpx.Response(200, json=veri))
        ogeler, d = asyncio.run(reddit_acik.topla(["x"], datetime(2026, 8, 1), datetime(2027, 1, 1)))
    assert d.durum == "tamam" and ogeler[0].begeni == 5 and ogeler[0].icerik_turu == "gonderi"
    with respx.mock:
        respx.get(reddit_acik.URL).mock(return_value=httpx.Response(403))
        ogeler, d = asyncio.run(reddit_acik.topla(["x"], BAS, BIT))
    assert d.durum == "hata" and ogeler == []


def test_x_arsiv_yoksa_son_7_gune_dusup_kismi_bildirir():
    sim = datetime.utcnow()
    tweet = {"data": [{"id": "1", "text": "t", "author_id": "9", "created_at": (sim.strftime("%Y-%m-%dT%H:%M:%S.000Z")),
                       "public_metrics": {"like_count": 2, "reply_count": 1, "retweet_count": 3, "quote_count": 1}}]}
    with respx.mock:
        respx.get(x.ARSIV).mock(return_value=httpx.Response(403, json={"title": "Forbidden"}))
        respx.get(x.RECENT).mock(return_value=httpx.Response(200, json=tweet))
        ogeler, d = asyncio.run(x.topla(["marka"], sim - __import__("datetime").timedelta(days=60), sim + __import__("datetime").timedelta(hours=1), "tok", "@marka"))
    assert d.durum == "kismi" and "arşiv" in d.mesaj and ogeler[0].paylasim == 4 and ogeler[0].erisim == "bagli"


def test_x_sorgu_uzunluk_siniri():
    q = x.sorgu_olustur([f"terim{i}" * 5 for i in range(50)], "@m", 512)
    assert len(q) <= 512 and q.startswith("(") and q.endswith("-is:retweet")


def test_x_bearer_yoksa_atlanir():
    assert asyncio.run(x.topla(["a"], BAS, BIT, "", ""))[1].durum == "atlandi"


def test_youtube_kota_asilirsa_elde_edilen_korunur():
    kanal = {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}
    with respx.mock:
        respx.get(f"{youtube.API}/channels").mock(return_value=httpx.Response(200, json=kanal))
        respx.get(f"{youtube.API}/playlistItems").mock(return_value=httpx.Response(200, json={"items": [{"contentDetails": {"videoId": "v1"}}]}))
        respx.get(f"{youtube.API}/videos").mock(return_value=httpx.Response(200, json={"items": [{"id": "v1", "snippet": {
            "title": "Video", "description": "", "publishedAt": "2026-09-20T10:00:00Z", "channelId": "UC1"},
            "statistics": {"likeCount": "3", "commentCount": "1"}}]}))
        respx.get(f"{youtube.API}/commentThreads").mock(return_value=httpx.Response(200, json={"items": [{"id": "c1", "snippet": {
            "totalReplyCount": 0, "topLevelComment": {"snippet": {"publishedAt": "2026-09-21T10:00:00Z", "textOriginal": "kötü ürün",
                                                                    "likeCount": 1, "authorDisplayName": "a"}}}}]}))
        respx.get(f"{youtube.API}/search").mock(return_value=httpx.Response(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}}, ))
        ogeler, d = asyncio.run(youtube.topla(["marka"], BAS, BIT, "anahtar", "UC1"))
    assert d.durum == "kismi" and {o.icerik_turu for o in ogeler} == {"gonderi", "yorum"}


def test_youtube_anahtar_yoksa_atlanir():
    assert asyncio.run(youtube.topla(["a"], BAS, BIT, "", ""))[1].durum == "atlandi"


def test_instagram_gonderi_yorum_ve_yetki_hatasi():
    base = instagram._taban()
    with respx.mock:
        respx.get(f"{base}/17/media").mock(return_value=httpx.Response(200, json={"data": [{
            "id": "m1", "caption": "Yeni ürün", "timestamp": "2026-09-20T10:00:00+0000", "permalink": "https://i/p/1",
            "like_count": 4, "comments_count": 1, "username": "marka"}]}))
        respx.get(f"{base}/m1/comments").mock(return_value=httpx.Response(200, json={"data": [{
            "id": "c1", "text": "berbat", "timestamp": "2026-09-21T10:00:00+0000", "username": "u", "like_count": 0}]}))
        respx.get(f"{base}/17/tags").mock(return_value=httpx.Response(200, json={"data": []}))
        ogeler, d = asyncio.run(instagram.topla([], BAS, BIT, "tok", "17"))
    assert d.durum == "tamam" and {o.icerik_turu for o in ogeler} == {"gonderi", "yorum"}
    with respx.mock:
        respx.get(f"{base}/17/media").mock(return_value=httpx.Response(200, json={"error": {"message": "expired", "code": 190, "type": "OAuthException"}}))
        ogeler, d = asyncio.run(instagram.topla([], BAS, BIT, "tok", "17"))
    assert d.durum == "hata" and "expired" in d.mesaj


def test_trends_csv():
    csv = "Kategori: Tüm kategoriler\n\nZaman,Anadolu Gıda: (Türkiye)\n2026-09-21T13,45\n2026-09-21T14,<1\n"
    d = google_trends.csv_ayristir(csv, 3)
    assert len(d) == 2 and list(d.values()) == [45.0, 0.0] and min(d).hour == 10
