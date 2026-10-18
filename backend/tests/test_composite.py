import math

from app.detection.composite import agirliklar, birlestir, kirp, phi


def test_kirpma():
    assert kirp(5) == 3 and kirp(-7) == -3 and kirp(1.2) == 1.2


def test_birinci_beyin_13_gosterge_esit_agirlik():
    w = agirliklar({f"G{i}" for i in range(1, 14)})
    assert len(w) == 13
    assert math.isclose(sum(w.values()), 1)
    assert all(math.isclose(v, 1 / 13) for v in w.values())
    assert math.isclose(100 * w["G1"], 7.692307692307692)     # 100/13 puan


def test_eksikte_yeniden_normallestirme():
    mevcut = {f"G{i}" for i in range(1, 14)} - {"G4", "G13"}
    w = agirliklar(mevcut)
    assert math.isclose(sum(w.values()), 1)
    assert "G13" not in w and all(math.isclose(v, 1 / 11) for v in w.values())


def test_ikinci_beyin_temel_agirliktan_yeniden_normallestirir():
    temel = {f"G{i}": float(i) for i in range(1, 14)}
    w = agirliklar({"G1", "G2", "G3"}, temel)
    assert math.isclose(sum(w.values()), 1)
    assert math.isclose(w["G3"], 3 / 6)


def test_ikinci_beyin_temel_agirligi_olmayan_gostergede_bos():
    assert agirliklar({"G1"}, {"G2": 1.0}) == {}


def test_stouffer_z():
    s = {f"G{i}": 1.0 for i in range(1, 14)}
    r = birlestir(s)
    w = agirliklar(set(s))
    assert math.isclose(r["kre"], 1.0)
    assert math.isclose(r["z"], 1.0 / math.sqrt(sum(v * v for v in w.values())))
    assert math.isclose(r["yuzdelik"], 100 * phi(r["z"]))


def test_strube_tam_korelasyonda_kre_esit():
    s = {"G1": 2.0, "G2": 2.0}
    rho = {("G1", "G2"): 1.0}
    r = birlestir(s, rho)
    assert r["yontem"] == "strube" and math.isclose(r["z"], 2.0)


def test_bos():
    assert birlestir({"G1": None})["z"] is None
