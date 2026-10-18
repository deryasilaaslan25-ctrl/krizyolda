"""Eşik metodolojisi raporundaki formül ve sayısal örneklerin birebir doğrulaması."""
import math
import random

import numpy as np
from scipy.stats import genpareto

from app.detection import esik_kalibrasyonu as E


def test_ampirik_esik_numpy_linear_ile_ayni():
    r = random.Random(3)
    x = [r.gauss(20, 8) for _ in range(500)]
    for p in (0.05, 0.01, 0.1):
        assert math.isclose(E.ampirik_esik(x, p), float(np.percentile(x, 100 * (1 - p), method="linear")), rel_tol=1e-12)


def test_rapor_ornegi_sagam_z_katsayilari():
    # Rapor 11.1: medyan 13,48, MAD 5,26 → s = 7,79; sağlam z eşikleri 26,30 / 31,61 / 37,56
    m, s = 13.48, 1.4826 * 5.26
    assert round(s, 2) == 7.80 or round(s, 2) == 7.79
    assert abs(m + E.norm_ppf(0.95) * s - 26.30) < 0.05
    assert abs(m + E.norm_ppf(0.99) * s - 31.61) < 0.06
    assert abs(m + E.norm_ppf(0.999) * s - 37.56) < 0.08
    assert abs(E.norm_ppf(0.95) - 1.645) < 1e-3 and abs(E.norm_ppf(0.99) - 2.326) < 1e-3 and abs(E.norm_ppf(0.999) - 3.09) < 1e-2


def test_rapor_ornegi_gpd_eşigi():
    # Rapor 11.1: u=25,83 λ=0,100 σ=6,486 ξ=−0,168 → z = 46,61
    f = E.GPDUyum(u=25.83, lam_u=0.100, sigma=6.486, xi=-0.168, m=216, gecerli=True)
    assert abs(E.gpd_esik(0.001, f) - 46.61) < 0.05


def test_rapor_ornegi_harman_ve_korkuluk():
    z = E.guvenilirlik_agirligi(2160)
    assert abs(z - 0.956) < 1e-3
    t = [E.harmanla(a, b, z) for a, b in ((30.12, 50), (37.97, 75), (46.61, 95))]
    assert abs(t[0] - 31.00) < 0.02 and abs(t[1] - 39.61) < 0.02 and abs(t[2] - 48.75) < 0.02
    son, devrede = E.korkuluk_uygula(t)
    assert abs(son[0] - 31.0) < 0.02 and son[1] == 40.0 and son[2] == 55.0 and devrede == ["yuksek", "kritik"]
    # Kurum B: 77,98/84,87/90,15 → 70,0 / 84,4 / 90,4
    tb = [E.harmanla(a, b, z) for a, b in ((77.98, 50), (84.87, 75), (90.15, 95))]
    sb, dv = E.korkuluk_uygula(tb)
    assert sb[0] == 70.0 and abs(sb[1] - 84.4) < 0.05 and abs(sb[2] - 90.4) < 0.05 and dv == ["orta"]


def test_rapor_ornegi_yeni_kurum_c():
    z = E.guvenilirlik_agirligi(48)
    assert abs(z - 0.324) < 1e-3
    # raporun önsel değerleri yuvarlanmış gösterilir (73,5/82,7/87,1) → 0,1 tolerans
    assert abs(E.harmanla(42.96, 73.5, z) - 63.6) < 0.1
    assert abs(E.harmanla(50.76, 82.7, z) - 72.3) < 0.1
    assert abs(E.harmanla(59.50, 87.1, z) - 78.2) < 0.1


def test_guvenilirlik_tablosu():
    for n, beklenen in ((24, 0.19), (100, 0.50), (168, 0.63), (720, 0.88), (2160, 0.96)):
        assert abs(E.guvenilirlik_agirligi(n) - beklenen) < 0.006
    assert E.guvenilirlik_agirligi(9) == 0.0


def test_rapor_ornegi_etiket_agirligi():
    ze = E.etiket_agirligi(40)
    assert abs(ze - 0.571) < 1e-3
    assert abs(ze * 75.11 + (1 - ze) * 84.43 - 79.11) < 0.02


def test_maliyet_optimal_esik_kaçirmayı_daha_pahalı_sayar():
    gercek = [60, 70, 80, 90]
    siradan = [30, 40, 50, 65, 75]
    esit = E.maliyet_optimal_esik(gercek, siradan, 1, 1)
    pahali = E.maliyet_optimal_esik(gercek, siradan, 5, 1)
    assert pahali <= esit
    assert pahali == 60      # tüm gerçekleri yakalayan en yüksek eşik


def test_gpd_pwm_bilinen_parametreleri_geri_verir():
    for xi in (-0.3, 0.0, 0.2):
        y = genpareto.rvs(c=xi, scale=5, size=5000, random_state=11)
        sigma, xi_hat = E.gpd_pwm(list(y))
        assert abs(sigma - 5) < 0.4 and abs(xi_hat - xi) < 0.06, (xi, sigma, xi_hat)


def test_gpd_kuyruk_eşigi_gercek_kuantile_yakin():
    x = list(genpareto.rvs(c=-0.2, scale=10, size=20000, random_state=5))
    f = E.gpd_uydur(x)
    assert f.gecerli
    gercek = genpareto.ppf(1 - 0.001, c=-0.2, scale=10)
    assert abs(E.gpd_esik(0.001, f) - gercek) / gercek < 0.05
    # p̂: GPD kuyruğunda
    p = E.asim_olasiligi(gercek, x, f)
    assert 0.0004 < p < 0.0025


def test_yontem_secimi():
    r = random.Random(1)
    x = [min(100, max(0, r.gauss(15, 6))) for _ in range(2160)]
    assert E.kademe_esigi(x, 0.05)[1] == "ampirik" and E.kademe_esigi(x, 0.01)[1] == "ampirik"
    assert E.kademe_esigi(x, 0.001)[1] == "gpd"
    assert E.kademe_esigi(x[:48], 0.05)[1] == "saglam_z"
    assert E.kademe_esigi(x[:9], 0.05) == (None, "yok")


def test_mad_sifir_ise_standart_sapmaya_donulur():
    x = [0.0] * 30 + [10.0, 20.0, 30.0]
    m, mad, s = E.saglam_olcek(x)
    assert mad == 0 and s > 0
    assert E.saglam_z_esigi([0.0] * 20, 0.05) is None


def test_seviye_ve_donus():
    assert [E.seviye_ham(r, (31.0019, 40, 55)) for r in (30, 31, 40, 54.9, 55)] == [0, 0, 2, 2, 3]
    assert E.donus_suresi_saat(0.01) == 100
    assert E.donus_metni(1625) == "yaklaşık 2 ayda bir"
    assert abs(E.asim_olasiligi(48, [1.0] * 1624 + [99] * 1) - 2 / 1626) < 1e-12
    assert E.asim_olasiligi(99.0, [0.0] * 99) == 1 / 100          # sıfır olasılık atanmaz


def test_blok_maksimumu():
    from datetime import datetime
    b = E.saatlik_blok_maksimumu([(datetime(2026, 1, 1, 10, 5), 20), (datetime(2026, 1, 1, 10, 50), 35),
                                  (datetime(2026, 1, 1, 11, 0), 5)])
    assert b == {datetime(2026, 1, 1, 10): 35, datetime(2026, 1, 1, 11): 5}


def test_korkuluk_siralama():
    son, dv = E.korkuluk_uygula([70, 71, 72])
    assert son[1] >= son[0] + 2 and son[2] >= son[1] + 2


def test_risk_puani():
    assert E.risk_puani(-1) == 0 and E.risk_puani(3) == 50 and E.risk_puani(4.5) == 75 and E.risk_puani(9) == 100
    assert E.risk_puani(None) is None


# ---- Rapor 11.4: histerezis dizisi (Kurum A; eşikler 31/40/55; s = 7,79 → δ = 3,9) ----------------
RAPOR_DIZI = [  # (R, Z_hacim, beklenen ham, beklenen nihai)
    (18, 0.4, 0, 0), (31, 0.8, 0, 0), (37, 1.2, 1, 0), (39, 1.5, 1, 1), (44, 2.1, 2, 1), (41, 1.7, 2, 2),
    (38, 1.1, 1, 2), (36, 0.9, 1, 2), (33, 0.6, 1, 2), (31, 0.5, 0, 1), (29, 0.4, 0, 1), (22, 3.4, 0, 1),
    (20, 0.5, 0, 1),
]


def test_rapor_histerezis_dizisi_birebir():
    T = (31.0019, 40.0, 55.0)
    s = 7.79
    rs, hams, nihai = [], [], 0
    for r, zh, ham_b, nihai_b in RAPOR_DIZI:
        ham = E.seviye_ham(r, T)
        rs.append(r)
        hams.append(ham)
        h = E.histerezis(r_dizi=rs, ham_dizi=hams, onceki_nihai=nihai, esikler=T, olcek_s=s, hacim_z=zh)
        nihai = h.nihai
        assert (ham, nihai) == (ham_b, nihai_b), (r, ham, nihai, h.kod)
    assert abs(E.delta_bandi(s) - 3.895) < 1e-9


def test_kritik_aninda_ve_tek_kademe_dusus():
    T = (31.0, 40.0, 55.0)
    h = E.histerezis(r_dizi=[80], ham_dizi=[3], onceki_nihai=0, esikler=T, olcek_s=5, hacim_z=0)
    assert h.nihai == 3 and h.kod == "kritik_aninda"
    # Kritik'ten düşüş: üç ölçüm de T_kritik − δ altında olsa bile yalnız bir kademe
    h = E.histerezis(r_dizi=[45, 45, 45], ham_dizi=[2, 2, 2], onceki_nihai=3, esikler=T, olcek_s=5, hacim_z=0)
    assert h.nihai == 2


def test_hacim_sok_yuksegi_kritige_cikarir_teyit_beklemez():
    T = (31.0, 40.0, 55.0)
    h = E.histerezis(r_dizi=[45], ham_dizi=[2], onceki_nihai=0, esikler=T, olcek_s=5, hacim_z=3.5)
    assert h.nihai == 3 and h.kod == "hacim_soku"


def test_hacim_z_skoru():
    dur = [5.0, 6.0, 4.0, 5.0] * 6
    assert E.hacim_z_skoru(dur, 5.0) is not None and abs(E.hacim_z_skoru(dur, 5.0)) < 1
    assert E.hacim_z_skoru(dur, 60.0) > 3
    assert E.hacim_z_skoru(dur[:10], 5.0) is None
    assert E.hacim_z_skoru([0.0] * 24, 0.0) is None


def test_esik_hesapla_uctan_uca_ve_aciklama():
    r = random.Random(7)
    x = [min(100, max(0, r.gauss(13, 7))) for _ in range(2160)]
    s = E.esik_hesapla(x, (50, 75, 95))
    assert s.kaynak == "kurum" and s.n == 2160 and s.yontemler[:2] == ("ampirik", "ampirik") and s.yontemler[2] == "gpd"
    assert s.esikler[0] < s.esikler[1] < s.esikler[2]
    h = E.histerezis(r_dizi=[48.0], ham_dizi=[3], onceki_nihai=0, esikler=s.esikler, olcek_s=s.olcek_s, hacim_z=0)
    txt = E.aciklama_metni(r=48.0, nihai=h.nihai, ham=h.ham, esik=s, p_hat=0.0006, donus_saat=1625, hist=h)
    assert "Risk puanı 48.0/100" in txt and "yaklaşık 2 ayda bir" in txt
    # yeni kurum: yalnız önsel
    y = E.esik_hesapla(x[:5], (50, 75, 95), "sektor")
    assert y.kaynak == "sektor" and y.esikler == (50, 75, 95)


def test_etiket_duzeltmesi_yuksek_esigi_dusurur():
    r = random.Random(2)
    x = [min(100, max(0, r.gauss(30, 12))) for _ in range(1000)]
    onsuz = E.esik_hesapla(x, (50, 75, 95))
    gercek = [r.uniform(60, 100) for _ in range(15)]
    siradan = [r.uniform(45, 85) for _ in range(25)]
    s = E.esik_hesapla(x, (50, 75, 95), etiket_gercek=gercek, etiket_siradan=siradan)
    assert s.etiket_duzeltme and s.etiket_duzeltme["m"] == 40
    assert s.esikler[1] != onsuz.esikler[1]
    az = E.esik_hesapla(x, (50, 75, 95), etiket_gercek=gercek[:3], etiket_siradan=siradan[:5])
    assert az.etiket_duzeltme is None                # min. 20 etiket / sınıf başına 5


def test_tarama_araligi():
    assert E.tarama_araligi_dakika(0) == 60 and E.tarama_araligi_dakika(2) == 15
    assert E.tarama_araligi_dakika(3, taban_dakika=5) == 15 and E.tarama_araligi_dakika(1, taban_dakika=45) == 45
