from datetime import datetime

from app.indicators.compute import Baglam, IslenmisIcerik, janis_fadner, pencere_olc


def test_janis_fadner():
    assert janis_fadner(6, 2, 10) == (36 - 12) / 100
    assert janis_fadner(2, 6, 10) == (12 - 36) / 100
    assert janis_fadner(3, 3, 10) == 0
    assert janis_fadner(0, 0, 0) is None


def _ic(i, **kw):
    d = dict(kimlik=str(i), platform="reddit", tur="sosyal", yazar=f"a{i}", metin=f"m{i}", tarih=datetime(2026, 1, 1))
    d.update(kw)
    return IslenmisIcerik(**d)


def test_pencere_olcumu():
    ic = [
        _ic(1, duygu_etiketi="olumsuz", ofke=1, toplam_sozcuk=10, begeni=3, yorum=1, niyet=["boykot"], scct_seviye=3),
        _ic(2, duygu_etiketi="olumlu", toplam_sozcuk=10, platform="youtube", yazar="a1"),
        _ic(3, tur="haber", platform="google_news", duygu_etiketi="olumsuz"),
        _ic(4, tur="haber", platform="google_news", duygu_etiketi="notr"),
    ]
    g = pencere_olc(ic, 50.0, Baglam(True, True, True, True, frozenset({"reddit", "youtube", "google_news"})))
    assert g["G1"] == 2 and g["G2"] == 1 and g["G3"] == 4 and g["G4"] == 50 and g["G5"] == 2
    assert g["G6"] == 0.5
    assert g["G7"] == -janis_fadner(0, 1, 2)
    assert g["G8"] == 1 / 20
    assert g["G11"] == 2 / 3          # reddit ve google_news olumsuz; pencereyi kapsayan 3 kaynak
    assert g["G12"] == 0.5
    assert g["G13"] == 3 / 4


def test_eksik_ve_sifir():
    g = pencere_olc([], None, Baglam(True, False, True, True))
    assert g["G1"] == 0 and g["G5"] is None and g["G6"] is None and g["G13"] is None


def test_q1():
    ic = [_ic(1, metin="Aynı METİN!"), _ic(2, metin="aynı metin"), _ic(3, metin="farklı")]
    assert pencere_olc(ic, None, Baglam(True, True, True, True))["Q1"] == 2 / 3


def test_g11_paydasi_kapsayan_kaynaklardir_icerik_gelen_platformlar_degil():
    """Üç kaynak başarıyla taranmış, yalnız birinden olumsuz içerik gelmiş: 1/3 (1/1 değil)."""
    ic = [_ic(1, duygu_etiketi="olumsuz")]
    g = pencere_olc(ic, None, Baglam(True, True, True, True, frozenset({"reddit", "youtube", "google_news"})))
    assert g["G11"] == 1 / 3


def test_g11_kapsam_yoksa_eksik():
    g = pencere_olc([_ic(1, duygu_etiketi="olumsuz")], None, Baglam(True, True, True, True, frozenset()))
    assert g["G11"] is None


def test_kapsami_olmayan_kaynakta_sifir_degil_eksik():
    g = pencere_olc([], None, Baglam(False, True, True, True))
    assert g["G1"] is None and g["G2"] is None and g["G3"] is None
    g = pencere_olc([], None, Baglam(True, True, True, True))
    assert g["G1"] == 0 and g["G3"] == 0
