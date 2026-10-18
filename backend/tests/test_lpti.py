"""L-PTİ raporu: formüller, işlenmiş örnek (Bölüm 6) ve birim testleri (Bölüm 11)."""
import math

import pytest

from app.reputation import lpti
from app.reputation.lpti import ItemSpec, ScoreStatus

I7 = ItemSpec("P", 1, 7)
I5 = ItemSpec("P", 1, 5)


def test_pomp_uclari_ve_orta_nokta():                                  # Test 1
    for it in (I5, I7):
        assert lpti.normalize(it.scale_min, it) == 0 and lpti.normalize(it.scale_max, it) == 1
    assert lpti.normalize(4, I7) == 0.5 and lpti.normalize(3, I5) == 0.5


def test_ters_madde():                                                 # Test 2
    r = ItemSpec("R", 1, 7, reverse=True)
    assert lpti.normalize(1, r) == 1 and lpti.normalize(7, r) == 0 and math.isclose(lpti.normalize(3, r), 1 - 2 / 6)


def test_olcek_disi_ve_gecersiz_uclar_reddedilir():                    # Test 3
    with pytest.raises(ValueError):
        lpti.normalize(8, I7)
    with pytest.raises(ValueError):
        lpti.normalize(0, I7)
    with pytest.raises(ValueError):
        lpti.normalize(3, ItemSpec("X", 5, 5))


def test_emin_degilim_eksik_olarak_islenir():                          # Test 4/6
    assert lpti.respondent_score([0.5, None, 0.5, 0.5], 3) == 0.5
    assert lpti.respondent_score([0.5, None, None, 0.5], 3) is None


def test_agirlik_ve_neff():                                            # Test 7
    with pytest.raises(ValueError):
        lpti.group_score([0.5, 0.6], [1.0, 0.0])
    with pytest.raises(ValueError):
        lpti.group_score([0.5, 0.6], [1.0, -1.0])
    assert math.isclose(lpti.kish_n_eff([1, 1, 1, 1]), 4)
    assert lpti.kish_n_eff([1, 2, 3]) < 3


# Rapor Bölüm 6 işlenmiş örnek (K1–K5; K6 m=3'ün altında)
YANIT = {"K1": [6, 6, 5, 7], "K2": [4, 5, None, 4], "K3": [7, 7, 6, 6], "K4": [3, 2, 3, 4], "K5": [5, 6, 6, 5],
         "K6": [6, None, None, 5]}
AGIRLIK = {"K1": 1.2, "K2": 0.8, "K3": 1.0, "K4": 1.5, "K5": 0.5, "K6": 1.0}


def _ornek():
    p, r = [], []
    for k, ham in YANIT.items():
        us = [None if x is None else lpti.normalize(x, I7) for x in ham]
        pj = lpti.respondent_score(us, 3)
        if pj is not None:
            p.append(pj)
            r.append(AGIRLIK[k])
    return p, r


def test_rapor_bolum6_ornegi_birebir():                                # Test 8
    p, r = _ornek()
    assert [round(x, 4) for x in p] == [0.8333, 0.5556, 0.9167, 0.3333, 0.75]      # K6 geçersiz
    g = lpti.group_score(p, r)                                                       # varsayılan E = ±5
    assert round(g["estimate"], 1) == 64.7
    assert round(g["n_eff"], 2) == 4.48 and round(g["deff_kish"], 2) == 1.12
    assert round(g["se"], 1) == 13.3
    assert round(g["ci95"][0], 1) == 38.7 and round(g["ci95"][1], 1) == 90.7
    assert g["status"] == ScoreStatus.INSUFFICIENT_DATA and g["score"] is None
    assert g["reason"] == "ci_half_width_exceeds_target"
    # hedef gevşetilirse skor yayımlanır
    assert lpti.group_score(p, r, max_half_width=30)["score"] == 64.7


def test_kurum_geneli_ve_pi():                                         # Test 10 ve Bölüm 6 Adım 8
    ok = lambda est, se: {"status": ScoreStatus.OK, "estimate": est, "se": se, "score": est}
    g = {"customers": ok(64.7, 2.0), "employees": ok(58.0, 3.0)}
    o = lpti.kurum_geneli(g, {"customers": 0.6, "employees": 0.4})
    assert o["score"] == 62.0
    assert math.isclose(o["se"], math.sqrt(0.36 * 4 + 0.16 * 9))
    assert lpti.kurum_geneli(g, None)["score"] is None and lpti.kurum_geneli(g, None)["reason"] == "pi_undefined"
    assert lpti.kurum_geneli(g, {"customers": 0.5, "employees": 0.4})["score"] is None
    g["employees"]["status"] = ScoreStatus.INSUFFICIENT_DATA
    assert lpti.kurum_geneli(g, {"customers": 0.6, "employees": 0.4})["score"] is None


def test_hic_veri_yoksa_skor_yok_asla_50_degil():                      # Test 9
    g = lpti.group_score([], [])
    assert g["score"] is None and g["status"] == ScoreStatus.INSUFFICIENT_DATA
    assert lpti.group_score([0.7], [1.0])["score"] is None


def test_k5_onceki_itibar_eslemesi():                                  # Test 12
    assert lpti.onceki_itibar_etiketi("ok", (55, 70)) == "olumlu"
    assert lpti.onceki_itibar_etiketi("ok", (30, 45)) == "olumsuz"
    assert lpti.onceki_itibar_etiketi("ok", (45, 60)) == "notr"
    assert lpti.onceki_itibar_etiketi("insufficient_data", (55, 70)) is None
    assert lpti.onceki_itibar_etiketi("ok", None) is None


def test_delta_ve_gereken_neff():
    d = lpti.delta({"estimate": 64.0, "se": 2.0}, {"estimate": 60.0, "se": 1.5})
    assert d["delta"] == 4 and math.isclose(d["se"], 2.5) and not d["anlamli"]
    assert lpti.delta({"estimate": 70, "se": 1}, {"estimate": 60, "se": 1})["anlamli"]
    assert math.isclose(lpti.gereken_n_eff(20, 5), (1.96 * 20 / 5) ** 2)


def test_hash_degisirse_ozet_degisir():                                # Test 11 (araç sürümü)
    a = [ItemSpec("P1", 1, 7), ItemSpec("P2", 1, 7)]
    b = [ItemSpec("P1", 1, 5), ItemSpec("P2", 1, 7)]
    assert lpti.puanlama_ozeti_hash(a) == lpti.puanlama_ozeti_hash(list(reversed(a)))
    assert lpti.puanlama_ozeti_hash(a) != lpti.puanlama_ozeti_hash(b)


def test_raking_marjlari_tutturur():
    kat = [{"yas": "a"}] * 60 + [{"yas": "b"}] * 40
    w = lpti.raking([1.0] * 100, kat, {"yas": {"a": 0.5, "b": 0.5}})
    pay_a = sum(w[:60]) / sum(w)
    assert abs(pay_a - 0.5) < 1e-6 and abs(sum(w) - 100) < 1e-6


def test_omega_yaklasik():
    import random
    r = random.Random(4)
    satirlar = []
    for _ in range(400):
        t = r.gauss(0, 1)
        satirlar.append([t + r.gauss(0, 0.6) for _ in range(4)])
    om = lpti.omega_pearson(satirlar)
    assert 0.85 < om < 0.95                     # λ² ≈ 0,74 → ω ≈ 0,92
    assert lpti.omega_pearson(satirlar[:10]) is None
