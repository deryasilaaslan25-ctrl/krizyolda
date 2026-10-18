"""
ERKİS v4 raporundaki 13 gösterge (G1–G13 + Q1) ile kodun BİREBİR uyumu.

Beklenen değerler rapor tablosundan (Bölüm 2–3) elle aktarılmıştır; kod kataloğundan türetilmemiştir.
"""
from datetime import datetime, timedelta

import pytest

from app import literatur as L
from app.indicators import compute
from app.indicators.compute import IslenmisIcerik, Baglam, pencere_olc

# kod: (boyut, kaynaklar)
RAPOR = {
    "G1": ("DIKKAT", {"PFEFFER2014", "MARCUS2011", "HERHAUSEN2019"}),
    "G2": ("DIKKAT", {"PFEFFER2014", "JOHNEN2018", "ROST2016"}),
    "G3": ("YAYILIM", {"HERHAUSEN2019", "STIEGLITZ2013", "CHA2010"}),
    "G4": ("DIKKAT", {"CHOI_VARIAN2012", "GINSBERG2009", "LAZER2014"}),
    "G5": ("DIKKAT", {"DEEPHOUSE2000", "MCCOMBS_SHAW1972", "CARROLL_MCCOMBS2003"}),
    "G6": ("TONALITE", {"THELWALL2011", "HANSEN2011", "HERHAUSEN2019"}),
    "G7": ("TONALITE", {"DEEPHOUSE2000", "JANIS_FADNER1965"}),
    "G8": ("UYARILMISLIK", {"HERHAUSEN2019", "BERGER_MILKMAN2012", "COOMBS2007", "COOMBS_HOLLADAY2007"}),
    "G9": ("UYARILMISLIK", {"HERHAUSEN2019", "BERGER_MILKMAN2012", "JIN2012"}),
    "G10": ("UYARILMISLIK", {"HERHAUSEN2019", "CROCKETT2017"}),
    "G11": ("YAYILIM", {"PFEFFER2014", "HARDER2017", "KASPERSON1988"}),
    "G12": ("NIYET", {"COOMBS_HOLLADAY2007", "COOMBS2007", "KLEIN2004"}),
    "G13": ("SORUMLULUK", {"COOMBS2007", "COOMBS_HOLLADAY2002"}),
}


def test_gosterge_kodlari_ve_sayisi():
    secilen = [g["kod"] for g in L.secilen_gostergeler()]
    assert len(secilen) == 13 and set(secilen) == set(RAPOR)
    from app.indicators.analysis import SECILEN_KODLAR
    assert SECILEN_KODLAR == secilen and len(SECILEN_KODLAR) == 13
    assert L.gosterge("Q1") and "Q1" not in secilen                    # Q1 kalite göstergesi, Z'ye girmez


@pytest.mark.parametrize("kod", sorted(RAPOR))
def test_gosterge_boyut_ve_kaynaklari(kod):
    boyut, kaynaklar = RAPOR[kod]
    g = L.gosterge(kod)
    assert g["boyut"] == boyut
    assert set(g["kaynaklar"]) == kaynaklar
    assert all(k in L.tum_kaynaklar() for k in g["kaynaklar"])


def test_boyut_haritasi():
    beklenen = {"DIKKAT": ["G1", "G2", "G4", "G5"], "TONALITE": ["G6", "G7"], "UYARILMISLIK": ["G8", "G9", "G10"],
                "YAYILIM": ["G3", "G11"], "NIYET": ["G12"], "SORUMLULUK": ["G13"]}
    assert {b: sorted(v, key=lambda c: int(c[1:])) for b, v in L.BOYUTLAR.items()} == beklenen


def test_birinci_beyin_agirliklari_esit():
    """13 göstergenin tamamı eşit (1/13 = 100/13 puan); boyutlar yalnız gösterim için."""
    a = L.tam_veri_agirliklari()
    assert len(a) == 13 and abs(sum(a.values()) - 1) < 1e-12
    assert all(abs(v - 1 / 13) < 1e-12 for v in a.values())


def test_weco_kurallari_rapor_tablosu():
    kur = {k["kural"]: (k["n"], k["m"], k["sinir"], k["seviye"]) for k in L.WECO_KURALLARI}
    assert kur[1][:3] == (1, 1, 3.0) and kur[2][:3] == (3, 2, 2.0) and kur[3][:3] == (5, 4, 1.0) and kur[4][:3] == (8, 8, 0.0)
    assert L.ISINMA_PENCERE == 28


def test_scct_tohum_listesi_rapor_ile_ayni():
    from app.nlp.scct import KRIZ_TIPLERI
    beklenen = {
        "dogal_afet": ["deprem", "sel felaket", "doğal afet", "heyelan", "kasırga"],
        "soylenti": ["asılsız", "yalan haber", "sahte haber", "dezenformasyon", "söylenti", "gerçeği yansıtm", "yalanla"],
        "meydan_okuma": ["protesto", "imza kampanya", "tepki yağ", "etik değil", "tepki göster", "kınıyor"],
        "teknik_hata_kaza": ["teknik arıza", "ekipman arıza", "sistem çök", "erişim kesinti", "arıza nedeniyle"],
        "teknik_hata_urun": ["geri çağır", "geri çağrıl", "toplatıl", "toplatma", "üretim hata", "yazılım hata"],
        "insan_hatasi_kaza": ["insan hata", "ihmal", "iş kaza", "dikkatsizlik"],
        "suistimal_yaralanmali": ["bile bile", "göz göre göre", "önlem alınma", "uyarılara rağmen", "denetimsiz"],
    }
    for tip, tohumlar in beklenen.items():
        assert set(tohumlar) <= set(KRIZ_TIPLERI[tip]["tohumlar"]), tip
    kume = {t: v["kume"] for t, v in KRIZ_TIPLERI.items()}
    assert kume["dogal_afet"] == kume["soylenti"] == "magdur"
    assert kume["meydan_okuma"] == kume["teknik_hata_kaza"] == kume["teknik_hata_urun"] == "kaza"
    assert kume["insan_hatasi_kaza"] == kume["suistimal_yaralanmali"] == "onlenebilir"


# --- Ölçüm formülleri: her gösterge elle kurulmuş bir pencerede raporun tanımıyla ---------------------------
T0 = datetime(2026, 9, 1, 10, 0)


def ic(kimlik, platform, tur, yazar, metin="x", begeni=0, yorum=0, paylasim=0, etiket=None, ofke=0, korku=0, igrenme=0,
       sozcuk=10, seviye=0, tip=None, olumsuz=0, olumlu=0, niyet=()):
    return IslenmisIcerik(kimlik=kimlik, platform=platform, tur=tur, yazar=yazar, metin=metin, tarih=T0, begeni=begeni,
                          yorum=yorum, paylasim=paylasim, duygu_etiketi=etiket, olumlu=olumlu, olumsuz=olumsuz, ofke=ofke,
                          korku=korku, igrenme=igrenme, toplam_sozcuk=sozcuk, scct_seviye=seviye, scct_tip=tip, niyet=list(niyet))


def test_olcumler_rapor_tanimlariyla():
    liste = [
        ic("1", "reddit", "sosyal", "a", begeni=5, yorum=2, paylasim=1, etiket="olumsuz", ofke=2, korku=1, igrenme=0, sozcuk=20,
           seviye=2, tip="insan_hatasi_urun", niyet=("boykot",)),
        ic("2", "youtube", "sosyal", "a", begeni=1, yorum=0, paylasim=0, etiket="olumlu", sozcuk=10, seviye=0),
        ic("3", "x", "sosyal", "b", begeni=0, yorum=3, paylasim=2, etiket="olumsuz", ofke=1, sozcuk=10, seviye=1, tip="teknik_hata_kaza"),
        ic("4", "google_news", "haber", "haber1", etiket="olumsuz", olumsuz=3, olumlu=1, sozcuk=30, seviye=0),
        ic("5", "rss", "haber", "haber2", etiket="olumlu", olumsuz=0, olumlu=2, sozcuk=30, seviye=0),
    ]
    o = pencere_olc(liste, 40.0, Baglam(True, True, True, True, frozenset({"reddit", "youtube", "x", "google_news", "rss"})))
    assert set(k for k in o if k.startswith("G")) == set(RAPOR)
    assert o["G1"] == 3                                        # sosyal içerik sayısı
    assert o["G2"] == 2                                        # farklı sosyal yazar
    assert o["G3"] == (5 + 2 + 1) + (1) + (3 + 2)              # beğeni+yorum+paylaşım (yalnız sosyal)
    assert o["G4"] == 40.0                                     # Google Trends
    assert o["G5"] == 2                                        # haber sayısı
    assert abs(o["G6"] - 2 / 3) < 1e-12                        # olumsuz etiketli sosyal / sosyal
    assert o["G7"] is not None                                 # −JF (haber)
    assert abs(o["G8"] - 3 / 40) < 1e-12 and abs(o["G9"] - 1 / 40) < 1e-12 and o["G10"] == 0     # öfke/korku/iğrenme ÷ toplam sözcük (sosyal)
    assert abs(o["G11"] - 3 / 5) < 1e-12                       # olumsuz platform (reddit, x, google_news) / pencereyi kapsayan kaynak (5)
    assert abs(o["G12"] - 1 / 3) < 1e-12                       # niyet içeren sosyal / sosyal
    assert abs(o["G13"] - (2 + 0 + 1 + 0 + 0) / 5) < 1e-12    # ortalama SCCT seviyesi (tüm içerik)
    assert "Q1" in o
