import math

from app.detection.kurum_esik import ampirik_asim_olasiligi, clopper_pearson, kalibrasyon_tanisi, korelasyon_kestir


def test_phipson_smyth():
    r = ampirik_asim_olasiligi(2.0, [0.0, 1.0, 2.5, 3.0])
    assert math.isclose(r["p"], (1 + 2) / 5)
    assert math.isclose(r["donus_suresi_saat"], 1 / r["p"])


def test_en_buyuk_deger_sifir_olasilik_vermez():
    r = ampirik_asim_olasiligi(99.0, [0.0] * 99)
    assert math.isclose(r["p"], 1 / 100)


def test_clopper_pearson_bilinen_deger():
    alt, ust = clopper_pearson(0, 10)
    assert alt == 0.0 and math.isclose(ust, 1 - 0.025 ** (1 / 10), rel_tol=1e-9)


def test_kalibrasyon_uyumlu_ve_sisme():
    import random
    r = random.Random(1)
    normal = [r.gauss(0, 1) for _ in range(5000)]
    assert all(b["durum"] == "uyumlu" for b in kalibrasyon_tanisi(normal)["bolgeler"])
    sisik = [2 * z for z in normal]
    assert kalibrasyon_tanisi(sisik)["bolgeler"][1]["durum"] == "şişme"


def test_korelasyon():
    a = [float(i) for i in range(40)]
    rho = korelasyon_kestir({"G1": a, "G2": [2 * x for x in a], "G3": a[:10] + [None] * 30})
    assert math.isclose(rho[("G1", "G2")], 1.0)
    assert rho[("G1", "G3")] == 0.0     # 28'den az ortak gözlem → 0 (Tasarım kararı 20)
