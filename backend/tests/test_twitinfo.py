import math

from app.detection.twitinfo import AkisNormallestirici, guncelle, populasyon_varyansi, zirve_pencereleri


def test_guncelle_formulu():
    m, o = guncelle(10.0, 2.0, 18.0, 0.125)
    assert m == 0.125 * 18 + 0.875 * 10
    assert o == 0.125 * 8 + 0.875 * 2


def test_baslatma_ve_skor():
    n = AkisNormallestirici()
    C = [4, 6, 5, 7, 3]
    for c in C:
        assert n.adim(c) is None                 # ilk p pencerede skor tanımsız
    m, o = C[0], populasyon_varyansi(C)
    for c in C[1:]:
        m, o = guncelle(m, o, c)
    assert math.isclose(n.durum.ortalama, m) and math.isclose(n.durum.oms, o)
    s = n.adim(20)
    assert math.isclose(s, (20 - m) / (math.sqrt(math.pi / 2) * o))   # güncellemeden önceki durum


def test_eksik_deger_durumu_degistirmez():
    n = AkisNormallestirici()
    for c in [1, 2, 3, 4, 5]:
        n.adim(c)
    once = (n.durum.ortalama, n.durum.oms)
    assert n.adim(None) is None
    assert (n.durum.ortalama, n.durum.oms) == once


def test_sifir_oms_tanimsiz():
    n = AkisNormallestirici()
    for _ in range(5):
        n.adim(3)
    assert n.adim(3) is None


def test_esik_karsiligi_ters_formul():
    n = AkisNormallestirici()
    for c in [4, 6, 5, 7, 3, 5, 6]:
        n.adim(c)
    x2 = n.esik_karsiligi(2)
    kopya = AkisNormallestirici()
    kopya.durum.ortalama, kopya.durum.oms = n.durum.ortalama, n.durum.oms
    assert math.isclose(kopya.adim(x2), 2.0)


def test_zirve_bulma():
    C = [5, 6, 5, 6, 5, 6, 5, 40, 60, 30, 8, 6, 5, 6]
    z = zirve_pencereleri(C)
    # Algoritma 1 sözde kodunun birebir çevirisi: patlama (indeks 7-8) bir pencere içinde bulunur
    assert any(a <= 7 and b >= 8 for a, b in z)


def test_duz_seride_zirve_yok():
    assert zirve_pencereleri([5] * 30) == []
