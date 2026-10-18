"""Sentetik sözlükle kural testleri (sözlük NRC değildir)."""
from app.nlp.lexicon import Sozluk, sozluk_al
from app.nlp.normalize import sozcukler, tr_kucuk
from app.nlp.scct import siniflandir
from app.nlp.behavioral import niyet_tespit
from app.nlp.sentiment import analiz_et, kurum_sozcukleri
from app.indicators.analysis import yogunlastir


def S() -> Sozluk:
    s = sozluk_al()
    assert s is not None
    return s


def test_turkce_kucuk_harf_ve_kesme():
    assert tr_kucuk("IŞIK İzmir") == "ışık izmir"
    assert sozcukler("Gıda'nın ürünü https://x.co @ali berbat!") == ["gıda", "ürünü", "berbat"]


def test_cogunluk_birlestirme():
    e = S().girdiler[("öfke",)]
    assert "negative" in e and "anger" not in e and "positive" not in e


def test_onek_kurali():
    s = S()
    assert s.eslestir(["berbattı"], 0).girdi == "berbat"          # 6 karakter → önek
    assert s.eslestir(["iyice"], 0) is None                       # 'iyi' 3 karakter → yalnız birebir
    assert s.eslestir(["iyi"], 0) is not None


def test_kalite_kalitesiz():
    s = S()
    assert s.eslestir(["kalitesiz"], 0).girdi == "kalitesiz"
    assert s.eslestir(["kaliteli"], 0).etiketler == frozenset()   # en uzun eşleşme etiketsiz 'kalite'


def test_cok_sozcuklu_girdi():
    e = S().eslestir(["terk", "etmek"], 0)
    assert e.uzunluk == 2 and "fear" in e.etiketler


def test_olumsuzlama():
    r = analiz_et("ürün güzel değil")
    assert r.olumsuz == 1 and r.olumlu == 0 and r.etiket == "olumsuz"
    r = analiz_et("hiç kötü değildi")
    assert r.olumlu == 1 and r.etiket == "olumlu"


def test_kurum_adi_haric():
    r = analiz_et("Anadolu Gıda berbat", haric=kurum_sozcukleri("Anadolu Gıda A.Ş."))
    assert r.olumlu == 0 and r.olumsuz == 1 and r.ofke == 1 and r.igrenme == 1


def test_notr():
    assert analiz_et("güzel ama kötü").etiket == "notr"


def test_scct_en_yuksek_sorumluluk():
    r = siniflandir("asılsız iddialar ama ürün zehirlenmesi de var")
    assert r["tip"] == "insan_hatasi_urun" and r["seviye"] == 3


def test_scct_sozcuk_basi():
    assert siniflandir("mihmal")["seviye"] == 0
    assert siniflandir("ihmaller zinciri")["seviye"] == 3


def test_yogunlastirici():
    assert yogunlastir(1, "soylenti", [], True) == 2
    assert yogunlastir(2, "meydan_okuma", ["meydan_okuma"], False) == 3
    assert yogunlastir(3, "yolsuzluk", ["x"], True) == 3
    assert yogunlastir(1, "soylenti", ["kaza"], False) == 1


def test_niyet():
    assert set(niyet_tespit("Herkesi uyarıyorum, boykot ediyoruz")) == {"boykot", "baskalarini_uyarma"}
    assert niyet_tespit("güzel ürün") == []
