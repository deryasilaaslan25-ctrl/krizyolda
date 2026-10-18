from app.detection.western_electric import seviyeler

I = 28


def _seri(son):
    return [0.0] * I + son


def test_isinmada_alarm_yok():
    s = seviyeler([5.0] * I)
    assert all(p["seviye"] == 0 and p["isinmada"] for p in s)


def test_kural1():
    s = seviyeler(_seri([3.1]))
    assert s[-1]["seviye"] == 3 and 1 in s[-1]["kurallar"]


def test_kural2():
    s = seviyeler(_seri([2.5, 0.0, 2.1]))
    assert s[-1]["seviye"] == 2


def test_kural3():
    s = seviyeler(_seri([1.5, 1.2, 0.0, 1.1, 1.3]))
    assert s[-1]["seviye"] == 1 and 3 in s[-1]["kurallar"]


def test_kural4_sessiz_birikim():
    s = seviyeler(_seri([0.3] * 8))
    assert s[-1]["seviye"] == 1 and s[-1]["sessiz_birikim"]
    assert seviyeler(_seri([0.3] * 7))[-1]["seviye"] == 0


def test_eksik_nokta_atlanir():
    s = seviyeler(_seri([0.0, 0.0, 2.5, None, 2.1]))
    assert s[-2].get("eksik") and s[-1]["seviye"] == 2


def test_isinma_noktalari_kurala_girmez():
    z = [0.5] * I + [0.5]
    assert seviyeler(z)[-1]["seviye"] == 0
