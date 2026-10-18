import math

from app import literatur as L


def test_katalog_tutarli():
    assert L.dogrula_katalog() == []


def test_isinma_formulu():
    # ISINMA = p + ceil(ln 0.05 / ln(1 - alpha)) = 5 + 23 = 28 (Rapor Bölüm 3.8)
    assert L.ISINMA_PENCERE == L.P_BASLATMA + math.ceil(math.log(0.05) / math.log(1 - L.ALFA)) == 28


def test_sabitler():
    assert L.ALFA == 0.125 and L.TAU == 2 and L.KIRPMA_SINIRI == 3
    assert abs(L.OMS_SIGMA_CARPANI - math.sqrt(math.pi / 2)) < 1e-12


def test_secilen_gostergeler_ve_boyutlar():
    kodlar = {g["kod"] for g in L.secilen_gostergeler()}
    assert kodlar == {f"G{i}" for i in range(1, 14)}
    assert {k for v in L.BOYUTLAR.values() for k in v} == kodlar


def test_tam_veri_agirliklari_toplami_bir():
    w = L.tam_veri_agirliklari()
    assert abs(sum(w.values()) - 1) < 1e-12


def test_her_gosterge_kaynagi_kaynakcada():
    tum = {**L.KAYNAKLAR, **L.EK_KAYNAKLAR}
    for g in L.GOSTERGELER:
        for k in g["kaynaklar"]:
            assert k in tum, (g["kod"], k)


def test_tasarim_kararlari_sirali():
    nolar = [k["no"] for k in L.TASARIM_KARARLARI]
    assert nolar == list(range(1, len(nolar) + 1))


def test_weco_kurallari():
    k = {r["kural"]: r for r in L.WECO_KURALLARI}
    assert (k[1]["n"], k[1]["m"], k[1]["sinir"], k[1]["seviye"]) == (1, 1, 3, 3)
    assert (k[2]["n"], k[2]["m"], k[2]["sinir"], k[2]["seviye"]) == (3, 2, 2, 2)
    assert (k[3]["n"], k[3]["m"], k[3]["sinir"], k[3]["seviye"]) == (5, 4, 1, 1)
    assert (k[4]["n"], k[4]["m"], k[4]["sinir"], k[4]["seviye"]) == (8, 8, 0, 1)
