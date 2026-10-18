import math
from datetime import datetime, timedelta

from app.indicators.analysis import alarm_donemleri, analiz_et, baskin_kume
from app.indicators.compute import IslenmisIcerik

SIMDI = datetime(2026, 9, 1, 12, 30)


def _uret(kriz: bool):
    ic = []
    bas = datetime(2026, 9, 1, 12) - timedelta(hours=720)
    for h in range(720):
        n = 3 + (h % 3)
        if kriz and h >= 715:
            n = 60
        for j in range(n):
            ic.append(IslenmisIcerik(kimlik=f"{h}-{j}", platform="reddit", tur="sosyal", yazar=f"u{j}",
                                     metin=f"m{h}-{j}", tarih=bas + timedelta(hours=h, minutes=j % 60),
                                     duygu_etiketi="olumsuz" if (kriz and h >= 715) else "notr",
                                     toplam_sozcuk=5, scct_seviye=3 if (kriz and h >= 715) else 0,
                                     scct_tip="insan_hatasi_urun" if (kriz and h >= 715) else None))
    return ic


def test_kriz_tespiti_ve_tehdit():
    s = analiz_et(_uret(True), SIMDI, haber_kaynak_var=False)
    assert s["pencere_sayisi"] == 720
    son5 = s["pencereler"][-5:]
    assert son5[0]["seviye"] == 3 and 1 in son5[0]["kurallar"]      # kriz başlangıcında Kural 1
    assert all(p["seviye"] >= 2 for p in son5)                       # akış uyarlansa da uyarı sürer
    assert s["son"]["tehdit"] == "Şiddetli"
    assert "G5" in s["eksik_gostergeler"] and "G4" in s["eksik_gostergeler"]
    assert math.isclose(sum(s["son"]["agirliklar"].values()), 1)


def test_olagan_akista_son_pencere_normal():
    s = analiz_et(_uret(False), SIMDI, haber_kaynak_var=False)
    assert s["son"]["seviye"] == 0


def test_tamamlanmamis_pencere_dislanir():
    s = analiz_et(_uret(False), SIMDI)
    assert s["bitis"] == "2026-09-01T12:00:00"


def test_onceki_itibar_kullanici():
    s = analiz_et([], SIMDI, onceki_itibar="olumsuz")
    assert s["onceki_itibar"]["kaynak"] == "kullanici"


def test_baskin_kume():
    assert baskin_kume([1, 1, 3, 3, 0]) == "onlenebilir"
    assert baskin_kume([2, 2, 1]) == "kaza"
    assert baskin_kume([0, 0]) is None


def test_alarm_donemleri():
    b = [datetime(2026, 1, 1, h) for h in range(5)]
    sev = [{"seviye": v, "kurallar": [1] if v else []} for v in (0, 1, 3, 0, 2)]
    d = alarm_donemleri(b, sev)
    assert len(d) == 2 and d[0]["max_seviye"] == 3 and not d[0]["acik"] and d[1]["acik"]
