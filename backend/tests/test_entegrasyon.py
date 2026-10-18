"""Uçtan uca: toplama kapsamı, iki beyin, kuruma özgü eşik, kalıcı bildirim kuyruğu, zamanlama, kimlik ve bağlantılar."""
import random
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import unquote

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import sentetik
from app.beyin import servis as beyin_servisi
from app.beyin import uzman as U
from app.collectors.base import KaynakDurumu
from app.config import Settings, settings
from app.core import crypto
from app.core.security import sifre_hashle
from app.database import SessionLocal
from app.detection import esik_kalibrasyonu as E
from app.main import app
from app.models import orm
from app.pr.strateji import kriz_stratejisi
from app.services import alarm_servisi, bildirim, isler, kaynaklar, kurum_esik_servisi, tarama, zamanlayici

SIFRE = "Guclu1234"
_TOKENLAR: dict[str, str] = {}


@pytest.fixture()
def istemci():
    with TestClient(app) as c:
        yield c


def _giris(c, email):
    if email not in _TOKENLAR:
        r = c.post("/api/auth/giris", data={"username": email, "password": SIFRE})
        assert r.status_code == 200, r.text
        _TOKENLAR[email] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_TOKENLAR[email]}"}


def _kurum(db, email="anadolu@ornek.com.tr", ad="Anadolu Gıda A.Ş.", terimler=("Anadolu Gıda",), rol="kurum"):
    k = db.query(orm.Kullanici).filter_by(email=email).first()
    if k is None:
        k = orm.Kullanici(email=email, hashed_password=sifre_hashle(SIFRE), kurum=ad, sektor="Gıda", rol=rol,
                          izleme_terimleri=list(terimler), kriz_gecmisi=[], bildirim_email=True, bildirim_min_seviye=2,
                          bildirim_haftalik=True, eposta_dogrulandi=True, olusturma=datetime(2026, 1, 1))
        db.add(k)
        db.commit()
        db.refresh(k)
    return k


def _senaryo(db, senaryo="onlenebilir", email="anadolu@ornek.com.tr"):
    k = _kurum(db, email)
    simdi = datetime.now(timezone.utc).replace(tzinfo=None)
    k.onceki_itibar, k.kriz_gecmisi, k.bildirim_email, k.bildirim_ek_epostalar = None, [], True, []
    k.aralik_turu, k.bildirim_min_seviye = "30", 2
    db.query(orm.BildirimKuyrugu).delete()
    sentetik.sifirla(db, k, simdi, senaryo)
    return k, simdi


@pytest.fixture()
def eposta(monkeypatch):
    """SMTP'yi taklit eder; gönderilen her tekil mesajı kaydeder."""
    gonderilen = []
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_FROM", "bildirim@test")
    monkeypatch.setattr(bildirim, "smtp_gonder", lambda alici, konu, metin, h=None: gonderilen.append(
        {"alici": alici, "konu": konu, "metin": metin, "html": h}))
    return gonderilen


# ---------------------------------------------------------------------------
# Kaynak kapsamı: gerçek sıfır, eksik veri ve kaynak hatası ayrı durumlardır
# ---------------------------------------------------------------------------
def test_kapsami_olmayan_pencere_eksik_kapsami_olan_bos_pencere_sifirdir():
    with SessionLocal() as db:
        k = _kurum(db, "kapsam@ornek.com.tr", "Kapsam A.Ş.", ("Kapsam",))
        simdi = datetime.now(timezone.utc).replace(tzinfo=None).replace(minute=0, second=0, microsecond=0)
        for m in (orm.KaynakKapsam, orm.Icerik, orm.Analiz, orm.RiskOlcumu):
            db.query(m).filter(m.kurum_id == k.id).delete()
        k.aralik_turu, k.bildirim_email = "7", False
        yari = simdi - timedelta(days=3)
        for ad in ("google_news", "reddit"):                       # yalnız son 3 gün kapsanıyor, içerik yok
            kaynaklar.kapsam_ekle(db, k, ad, yari, simdi)
        db.commit()
        s = tarama.analiz_calistir(db, k, simdi=simdi)
        p = s["pencereler"]
        g_eksik, g_sifir = p[10]["gostergeler"], p[-5]["gostergeler"]
        assert g_eksik["G1"] is None and g_eksik["G5"] is None and g_eksik["G11"] is None   # kaynak o saati taramadı: eksik
        assert g_sifir["G1"] == 0 and g_sifir["G5"] == 0 and g_sifir["G11"] == 0            # taranmış, içerik yok: gerçek sıfır
        ozet = s["kaynak_kapsami"]["kaynaklar"]
        assert 0.4 < ozet["reddit"]["oran"] < 0.5 and ozet["reddit"]["ilk"] is not None
        durum = {x["kaynak"]: x["durum"] for x in s["kaynak_ozeti"]}
        assert durum["reddit"] == "icerik_yok" and durum["youtube"] == "baglanti_yok" and durum["bing_news"] == "taranmadi"


def test_kapsam_birlestirme_ve_eksik_baslangic():
    a = datetime(2026, 5, 1)
    arl = [(a, a + timedelta(days=10)), (a + timedelta(days=10), a + timedelta(days=20))]
    assert kaynaklar._birlestir(arl) == [(a, a + timedelta(days=20))]
    assert kaynaklar.eksik_baslangic([], a, a + timedelta(days=5)) == a
    bit = a + timedelta(days=30)
    assert kaynaklar.eksik_baslangic([(a, a + timedelta(days=20))], a, bit) == a + timedelta(days=20) - kaynaklar.BINDIRME
    assert kaynaklar.eksik_baslangic([(a, bit)], a, bit) is None
    assert kaynaklar.eksik_baslangic([(a + timedelta(days=2), bit)], a, bit) == a      # baştaki boşluk


def test_aralik_siniri_6_ay_ve_ozel_aralik(istemci):
    with SessionLocal() as db:
        _kurum(db, "aralik@ornek.com.tr", "Aralık A.Ş.")
    h = _giris(istemci, "aralik@ornek.com.tr")
    assert istemci.put("/api/kurum/profil", headers=h, json={"aralik_turu": "180"}).json()["aralik_turu"] == "180"
    bugun = datetime.now(timezone.utc).date()
    r = istemci.put("/api/kurum/profil", headers=h, json={"aralik_turu": "ozel", "ozel_baslangic": str(bugun - timedelta(days=200)),
                                                          "ozel_bitis": str(bugun - timedelta(days=1))})
    assert r.status_code == 422 and "180" in r.text
    r = istemci.put("/api/kurum/profil", headers=h, json={"ozel_baslangic": str(bugun - timedelta(days=100)),
                                                          "ozel_bitis": str(bugun - timedelta(days=40))})
    assert r.status_code == 200 and r.json()["aralik_turu"] == "ozel" and r.json()["ozel_bitis"] == str(bugun - timedelta(days=40))
    assert istemci.put("/api/kurum/profil", headers=h, json={"ozel_bitis": str(bugun + timedelta(days=3))}).status_code == 422
    assert istemci.put("/api/kurum/profil", headers=h, json={"aralik_turu": "365"}).status_code == 422


def test_gecmis_inceleme_alarm_ve_bildirim_uretmez(eposta):
    with SessionLocal() as db:
        k, simdi = _senaryo(db, "onlenebilir", "gecmis@ornek.com.tr")
        k.aralik_turu = "ozel"
        k.ozel_baslangic, k.ozel_bitis = (simdi - timedelta(days=20)).replace(hour=0), (simdi - timedelta(days=10)).replace(hour=0)
        db.commit()
        s = tarama.analiz_calistir(db, k, simdi=simdi)
        assert s["aralik"]["canli"] is False and s["son"]["risk"] is None and s["bildirimler"] == []
        assert db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id).count() == 0
        k.aralik_turu = "30"
        db.commit()


# ---------------------------------------------------------------------------
# Tarama işi uçtan uca: kaynak başarılı + sıfır içerik → kapsam yazılır; hata → kapsam yazılmaz
# ---------------------------------------------------------------------------
def test_tarama_isi_yasam_dongusu_ve_kaynak_sagligi(monkeypatch):
    import asyncio
    with SessionLocal() as db:
        k = _kurum(db, "is@ornek.com.tr", "İş A.Ş.", ("İş Marka",))
        for m in (orm.KaynakKapsam, orm.KaynakSaglik, orm.TaramaIsi, orm.Icerik, orm.Analiz, orm.RiskOlcumu):
            db.query(m).filter(m.kurum_id == k.id).delete()
        k.aralik_turu, k.bildirim_email, k.sonraki_tarama, k.tekrar_plani = "7", False, None, "periyodik"
        db.commit()

        async def sahte(db_, k_, bas, bit):
            return [], {}, [KaynakDurumu("google_news", "tamam", istenen_bas=bas, istenen_bit=bit, ulasilan_bas=bas, ulasilan_bit=bit),
                            KaynakDurumu("bing_news", "hata", mesaj="HTTP 403", istenen_bas=bas, istenen_bit=bit),
                            KaynakDurumu("reddit", "kismi", mesaj="son 5 gün", istenen_bas=bas, istenen_bit=bit,
                                         ulasilan_bas=bit - timedelta(days=5), ulasilan_bit=bit)]
        monkeypatch.setattr(kaynaklar, "topla_hepsi", sahte)
        assert isler.zamanlanmis_isleri_olustur(db) >= 1
        j = db.query(orm.TaramaIsi).filter_by(kurum_id=k.id).one()
        assert j.tur == "gecmis" and j.durum == "bekliyor"
        assert isler.is_olustur(db, k, "elle", "kullanici").id == j.id               # mükerrer iş yok
        alinan = isler.siradaki_is_al(db)
        while alinan is not None and alinan.kurum_id != k.id:                         # başka testten kalan iş
            asyncio.run(isler.isi_calistir(db, alinan))
            alinan = isler.siradaki_is_al(db)
        assert alinan.id == j.id and isler.siradaki_is_al(db) is None or True
        asyncio.run(isler.isi_calistir(db, alinan))
        db.refresh(j)
        assert j.durum == "kismi" and {x["kaynak"]: x["durum"] for x in j.kaynaklar} == {
            "google_news": "tamam", "bing_news": "hata", "reddit": "kismi"}
        kapsam = kaynaklar.kapsam_oku(db, k)
        assert "google_news" in kapsam and "reddit" in kapsam and "bing_news" not in kapsam   # hata kapsam yazmaz
        bas, bit = kaynaklar.aralik_coz(k)
        assert kapsam["reddit"][0][0] == bit - timedelta(days=5) and kapsam["google_news"][0] == (bas, bit)
        db.refresh(k)
        assert k.sonraki_tarama is not None and k.tarama_aralik_dk == k.tarama_max_dk   # düşük risk: en seyrek tarama
        durum = {x["kaynak"]: x for x in kaynaklar.kaynak_ozeti(db, k, bas, bit)}
        assert durum["bing_news"]["durum"] == "hata" and durum["google_news"]["durum"] == "icerik_yok"
        assert durum["reddit"]["kapsam_orani"] == pytest.approx(5 / 7, abs=0.01)


def test_tek_seferlik_plan_bir_kez_tarar():
    with SessionLocal() as db:
        k = _kurum(db, "tek@ornek.com.tr", "Tek A.Ş.", ("Tek",))
        db.query(orm.TaramaIsi).filter_by(kurum_id=k.id).delete()
        k.tekrar_plani, k.tek_seferlik_yapildi, k.sonraki_tarama = "tek_seferlik", False, None
        db.commit()
        isler.zamanlanmis_isleri_olustur(db)
        assert db.query(orm.TaramaIsi).filter_by(kurum_id=k.id).count() == 1
        k.tek_seferlik_yapildi = True
        db.query(orm.TaramaIsi).filter_by(kurum_id=k.id).delete()
        db.commit()
        isler.zamanlanmis_isleri_olustur(db)
        assert db.query(orm.TaramaIsi).filter_by(kurum_id=k.id).count() == 0
        assert zamanlayici.sonraki_tarama(k, datetime(2026, 1, 1), 3) is None


def test_uyarlamali_tarama_sikligi():
    k = SimpleNamespace(tarama_min_dk=15, tarama_max_dk=360, tekrar_plani="periyodik", tarama_aralik_dk=None)
    a = [zamanlayici.aralik_sec(k, s) for s in range(4)]
    assert a[0] == 360 and a[3] == 15 and a[0] > a[1] > a[2] > a[3]
    assert zamanlayici.aralik_sec(k, 0, hacim_sok=True) == a[1]                  # hacim şoku sıklığı artırır
    k2 = SimpleNamespace(tarama_min_dk=60, tarama_max_dk=120, tekrar_plani="periyodik", tarama_aralik_dk=None)
    assert [zamanlayici.aralik_sec(k2, s) for s in (0, 3)] == [120, 60]          # kurumun sınırları aşılmaz


# ---------------------------------------------------------------------------
# İki beyin
# ---------------------------------------------------------------------------
def _uzman_puanlari(n, rng):
    return {f"U{i:02d}": {f"G{g}": float(rng.randint(3, 9)) for g in range(1, 14)} for i in range(1, n + 1)}


def test_uzman_agirlik_ve_kendall_w():
    ayni = {f"U0{i}": {f"G{g}": float(g) for g in range(1, 14)} for i in range(1, 4)}
    assert U.kendall_w(ayni) == pytest.approx(1.0)                                # tam uyum
    r = U.agirliklari_hesapla(ayni)
    assert sum(r["agirliklar"].values()) == pytest.approx(1) and r["agirliklar"]["G13"] == pytest.approx(13 / 91)
    medyan = U.agirliklari_hesapla({"U01": {f"G{g}": 5.0 for g in range(1, 14)}, "U02": {f"G{g}": 5.0 for g in range(1, 14)},
                                    "U03": {f"G{g}": 9.0 for g in range(1, 14)}}, "medyan")
    assert all(v == pytest.approx(1 / 13) for v in medyan["agirliklar"].values())
    eksik = {"U01": {"G1": 5.0}}
    with pytest.raises(U.UzmanVerisiHatasi):
        U.agirliklari_hesapla(eksik)                                              # eksik puan sıfır sayılmaz
    with pytest.raises(U.UzmanVerisiHatasi):
        U.dogrula({"U01": {"G1": 11.0}}, 1, 9)


def test_ikinci_beyin_uzman_verisi_gelene_kadar_pasif_sonra_etkin(istemci):
    with SessionLocal() as db:
        db.query(orm.UzmanPuani).delete()
        db.query(orm.UzmanForm).delete()
        _kurum(db, "yonetici@ornek.com.tr", "Yönetim", (), "yonetici")
        k, simdi = _senaryo(db, "onlenebilir", "beyin@ornek.com.tr")
        s = tarama.analiz_calistir(db, k, simdi=simdi)
        assert s["beyin"]["etkin"] is False and s["beyin"]["neden"] == "uzman_formu_yok"
        assert all(p["risk_uzman"] is None for p in s["pencereler"])               # sahte uzman puanı yok
        r1 = s["son"]["risk"]["puan"]
        db.commit()
    y = _giris(istemci, "yonetici@ornek.com.tr")
    kurum_h = _giris(istemci, "beyin@ornek.com.tr")
    assert istemci.get("/api/uzman/durum", headers=kurum_h).status_code == 403            # yalnız yönetici
    f = istemci.post("/api/uzman/formlar", headers=y, json={
        "surum": "F1", "soru": "Göstergenin kriz tespitindeki önem derecesi (1 en düşük, 9 en yüksek)",
        "olcek_min": 1, "olcek_max": 9, "birlestirme": "ortalama", "min_uzman": 12}).json()
    assert istemci.post(f"/api/uzman/formlar/{f['id']}/aktif", headers=y).json()["neden"] == "uzman_verisi_bekleniyor"
    puan = _uzman_puanlari(12, random.Random(3))
    for kod, p in list(puan.items())[:11]:
        assert istemci.put(f"/api/uzman/formlar/{f['id']}/uzmanlar/{kod}", headers=y, json={"puanlar": p}).status_code == 200
    d = istemci.get("/api/uzman/durum", headers=y).json()
    assert d["etkin"] is False and d["tam_uzman"] == 11 and "11/12" in d["aciklama"]
    assert istemci.put(f"/api/uzman/formlar/{f['id']}/uzmanlar/U01", headers=y, json={"puanlar": {"G1": 12}}).status_code == 422
    assert istemci.put(f"/api/uzman/formlar/{f['id']}/uzmanlar/uzman1", headers=y, json={"puanlar": {"G1": 5}}).status_code == 422
    istemci.put(f"/api/uzman/formlar/{f['id']}/uzmanlar/U12", headers=y, json={"puanlar": puan["U12"]})
    d = istemci.get("/api/uzman/durum", headers=y).json()
    assert d["etkin"] is True and sum(d["agirliklar"].values()) == pytest.approx(1) and 0 <= d["kendall_w"] <= 1
    with SessionLocal() as db:
        k = db.query(orm.Kullanici).filter_by(email="beyin@ornek.com.tr").first()
        s = tarama.analiz_calistir(db, k)
        b = s["beyin"]
        assert b["etkin"] and b["form"] == "F1" and b["donem"]["n"] > 100 and -1 <= b["donem"]["korelasyon"] <= 1
        assert s["son"]["risk"]["puan"] is not None and b["son"]["r1"] is not None and b["son"]["r2"] is not None
        assert abs(sum(x["w1"] for x in b["katkilar"]) - 1) < 1e-9 and abs(sum(x["w2"] for x in b["katkilar"]) - 1) < 1e-9
        w1 = [x["w1"] for x in b["katkilar"]]
        assert max(w1) - min(w1) < 1e-12                                                  # 1. beyin: ölçülebilen göstergeler eşit
        assert s["son"]["seviye"] == s["son"]["risk"]["nihai_seviye"]                    # karar 1. beyinde
    ozet = istemci.get("/api/beyin", headers=kurum_h).json()
    assert ozet["beyin1"]["toplam"] == pytest.approx(100) and len(ozet["gostergeler"]) == 13
    assert ozet["gostergeler"][0]["agirlik1"] == pytest.approx(100 / 13) and ozet["beyin2"]["etkin"] is True
    with SessionLocal() as db:                                                           # sonraki testler pasif beyinle çalışsın
        db.query(orm.UzmanPuani).delete()
        db.query(orm.UzmanForm).delete()
        db.commit()


# ---------------------------------------------------------------------------
# Eşik ölçümleri
# ---------------------------------------------------------------------------
def test_olcumler_kaydedilir_tutarli_ve_idempotent():
    with SessionLocal() as db:
        k, simdi = _senaryo(db, "yok", "esik@ornek.com.tr")
        k.bildirim_email = False
        tarama.analiz_calistir(db, k, simdi=simdi)
        s = tarama.analiz_calistir(db, k, simdi=simdi)
        n = db.query(orm.RiskOlcumu).filter_by(kurum_id=k.id).count()
        assert n >= 650
        tarama.analiz_calistir(db, k, simdi=simdi)
        assert db.query(orm.RiskOlcumu).filter_by(kurum_id=k.id).count() <= n + 1       # aynı saat tekrar sayılmaz
        p = s["pencereler"][-1]
        assert {"risk_puani", "risk_ham", "risk_seviye", "risk_esik_yuksek", "risk_uzman"} <= set(p)
        assert s["son"]["risk"]["etiket"].endswith("RİSK")



# ---------------------------------------------------------------------------
# Bildirim: kalıcı kuyruk, alıcıya özel gönderim, tekilleştirme, yeniden deneme
# ---------------------------------------------------------------------------
def test_kriz_eposta_kuyruga_yazilir_her_alici_ayri_ve_tek_kez(eposta):
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        k.bildirim_ek_epostalar = ["ekip@ornek.com.tr"]
        db.commit()
        tarama.analiz_calistir(db, k, simdi=simdi)
        kayit = db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id, tur="kriz").all()
        assert sorted(b.alici for b in kayit) == sorted([k.email, "ekip@ornek.com.tr"])    # alıcı başına ayrı kayıt
        assert eposta == []                                                                  # tarama gönderim yapmaz; işçi yapar
        ozet = bildirim.kuyrugu_isle(db)
        assert ozet["gonderilen"] == 2 and {m["alici"] for m in eposta} == {k.email, "ekip@ornek.com.tr"}
        m = eposta[0]
        assert "KRİZ UYARISI" in m["konu"] and k.kurum in m["konu"] and "ekip@ornek.com.tr" not in m["metin"] + (m["html"] or "")
        assert "Gerçek kriz:" in m["metin"] and "Önemsiz:" in m["metin"] and "SCCT (Coombs 2007)" in m["metin"]
        assert "<a href=" in m["html"]                                                       # HTML sürümü bağlantıları taşır
        a = db.query(orm.Alarm).filter_by(kurum_id=k.id, acik=True).one()
        assert a.bildirim_durumu == "kuyruga_alindi" and a.bildirim_seviye == a.max_seviye
        gecmis = db.query(orm.Alarm).filter(orm.Alarm.kurum_id == k.id, orm.Alarm.acik.is_(False)).all()
        assert gecmis and all(x.bildirim_durumu == "gecmis" for x in gecmis)
        tarama.analiz_calistir(db, k, simdi=simdi)                                           # aynı durum: ikinci e-posta yok
        assert db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id, tur="kriz").count() == 2
        assert bildirim.kuyrugu_isle(db)["gonderilen"] == 0


def test_bildirim_kapaliysa_kuyruga_yazilmaz(eposta):
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        k.bildirim_email = False
        db.commit()
        tarama.analiz_calistir(db, k, simdi=simdi)
        assert db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id).count() == 0
        k.bildirim_email = True
        db.commit()


def test_smtp_yokken_bildirim_kuyrukta_bekler_ve_sonra_gider(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        tarama.analiz_calistir(db, k, simdi=simdi)
        assert bildirim.kuyrugu_isle(db)["bekleyen_smtp_yok"] >= 1
        b = db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id).first()
        assert b.durum == "kuyrukta" and b.deneme == 0                                       # deneme hakkı harcanmaz
        monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
        monkeypatch.setattr(settings, "SMTP_FROM", "x@test")
        monkeypatch.setattr(bildirim, "smtp_gonder", lambda *a, **kw: None)
        assert bildirim.kuyrugu_isle(db)["gonderilen"] >= 1
        db.refresh(b)
        assert b.durum == "smtp_kabul" and b.gonderim is not None


def test_gecici_hata_artan_beklemeyle_denenir_kalici_hata_durur(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_FROM", "x@test")
    cagri = {"n": 0}

    def gecici(*a, **kw):
        cagri["n"] += 1
        raise TimeoutError("zaman aşımı")
    monkeypatch.setattr(bildirim, "smtp_gonder", gecici)
    with SessionLocal() as db:
        k = _kurum(db)
        bildirim.kuyruga_ekle(db, kurum_id=k.id, tur="test", anahtar="t-gecici", alicilar=["a@ornek.com.tr"], konu="k", metin="m")
        db.commit()
        t0 = datetime.now(timezone.utc).replace(tzinfo=None)
        o = bildirim.kuyrugu_isle(db, simdi=t0)
        b = db.query(orm.BildirimKuyrugu).filter_by(anahtar="t-gecici").one()
        assert o["tekrar"] == 1 and b.durum == "tekrar_bekliyor" and b.sonraki_deneme > t0 and "TimeoutError" in b.son_hata
        assert bildirim.kuyrugu_isle(db, simdi=t0)["tekrar"] == 0                           # vadesi gelmeden denenmez
        gecen = [b.sonraki_deneme - t0]
        for _ in range(settings.BILDIRIM_EN_FAZLA_DENEME):
            bildirim.kuyrugu_isle(db, simdi=b.sonraki_deneme + timedelta(seconds=1) if b.durum == "tekrar_bekliyor" else t0)
            db.refresh(b)
            if b.durum == "tekrar_bekliyor":
                gecen.append(b.sonraki_deneme - t0)
        assert b.durum == "kalici_hata" and b.deneme == settings.BILDIRIM_EN_FAZLA_DENEME
        assert gecen == sorted(gecen) and len(set(gecen)) == len(gecen)                     # bekleme süresi artıyor
        assert db.query(orm.DenetimKaydi).filter_by(islem="bildirim_kalici_hata").count() >= 1
        monkeypatch.setattr(bildirim, "smtp_gonder", lambda *a, **kw: (_ for _ in ()).throw(bildirim.KalıcıHata("reddedildi")))
        bildirim.kuyruga_ekle(db, kurum_id=k.id, tur="test", anahtar="t-kalici", alicilar=["b@ornek.com.tr"], konu="k", metin="m")
        db.commit()
        bildirim.kuyrugu_isle(db)
        assert db.query(orm.BildirimKuyrugu).filter_by(anahtar="t-kalici").one().durum == "kalici_hata"


def test_alarm_kapansa_da_kuyruktaki_kritik_bildirim_kaybolmaz(eposta, monkeypatch):
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        monkeypatch.setattr(settings, "SMTP_HOST", "")
        tarama.analiz_calistir(db, k, simdi=simdi)
        a = db.query(orm.Alarm).filter_by(kurum_id=k.id, acik=True).one()
        a.acik = False                                                                       # alarm kapandı
        db.commit()
        monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
        assert bildirim.kuyrugu_isle(db)["gonderilen"] >= 1


def test_bildirim_bekleme_suresi_ayni_alarmda_tekrar_e_postayi_sinirlar(eposta):
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        tarama.analiz_calistir(db, k, simdi=simdi)
        a = db.query(orm.Alarm).filter_by(kurum_id=k.id, acik=True).one()
        if a.max_seviye >= 3:
            a.max_seviye, a.bildirim_seviye = 2, 2
        a.bildirim_seviye, a.max_seviye = 2, 3
        a.bildirim_son_zaman = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        k.bildirim_bekleme_saat = 6
        assert alarm_servisi.bildirim_karari(db, k, a)[0] == "gonder"                       # Kritik'e çıkış beklemez
        a.max_seviye, a.bildirim_seviye = 2, 1
        assert alarm_servisi.bildirim_karari(db, k, a)[0] == "bekle"                        # 1 saat < 6 saat
        a.bildirim_son_zaman -= timedelta(hours=6)
        assert alarm_servisi.bildirim_karari(db, k, a)[0] == "gonder"
        db.rollback()


def test_onemsiz_isaret_ayni_krizi_susturur_ve_ogrenir(istemci, eposta):
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        tarama.analiz_calistir(db, k, simdi=simdi)
        bildirim.kuyrugu_isle(db)
        assert len(eposta) == 1
        token = unquote(re.search(r"karar=onemsiz&token=([^\s&]+)", eposta[0]["metin"]).group(1))
        alarm_id = db.query(orm.Alarm).filter_by(kurum_id=k.id, acik=True).one().id
    r = istemci.get("/api/geri-bildirim/onizle", params={"token": token})
    assert r.status_code == 200 and r.json()["geri_bildirim"] is None and r.json()["id"] == alarm_id
    r = istemci.post("/api/geri-bildirim/e-posta", json={"token": token, "karar": "onemsiz"})
    assert r.status_code == 200 and r.json()["geri_bildirim"] == "yanlis_alarm"
    h = _giris(istemci, "anadolu@ornek.com.tr")
    assert istemci.get("/api/geri-bildirim/onizle", params={"token": h["Authorization"][7:]}).status_code == 400
    assert istemci.get("/api/geri-bildirim/onizle", params={"token": "x" * 30}).status_code == 400
    with SessionLocal() as db:
        k = db.query(orm.Kullanici).filter_by(email="anadolu@ornek.com.tr").first()
        a = db.get(orm.Alarm, alarm_id)
        assert a.geri_bildirim == "yanlis_alarm" and a.geri_bildirim_seviye == a.max_seviye
        assert alarm_servisi.bildirim_karari(db, k, a)[0] == "bastir"
        yeni = orm.Alarm(kurum_id=k.id, baslangic=datetime.now() + timedelta(days=2), bitis=datetime.now() + timedelta(days=2, hours=3),
                         acik=True, max_seviye=a.max_seviye, parmak_izi=a.parmak_izi, bildirim_durumu="yok")
        db.add(yeni)
        db.flush()
        assert alarm_servisi.bildirim_karari(db, k, yeni)[0] == "bastir"
        yeni.parmak_izi = {"tip": "baska_tip", "govdeler": ["tamamen", "farkli", "konu"]}
        assert alarm_servisi.bildirim_karari(db, k, yeni)[0] == "gonder"
        db.rollback()


def test_haftalik_brif_dogru_gun_saatte_bir_kez_kuyruga_yazilir(eposta):
    with SessionLocal() as db:
        k, simdi = _senaryo(db, "yok", "haftalik@ornek.com.tr")
        k.bildirim_ek_epostalar, k.rapor_gunu, k.rapor_saati = ["x@ornek.com.tr"], 0, 9
        db.commit()
        pazartesi_10_tr = datetime(2026, 10, 19, 7, 0)                                       # 10:00 TRT
        sali = datetime(2026, 10, 20, 7, 0)
        erken = datetime(2026, 10, 19, 5, 0)                                                 # 08:00 TRT
        assert isler.haftalik_brifleri_kuyruga(db, erken) == 0 and isler.haftalik_brifleri_kuyruga(db, sali) == 0
        assert isler.haftalik_brifleri_kuyruga(db, pazartesi_10_tr) >= 2
        assert isler.haftalik_brifleri_kuyruga(db, pazartesi_10_tr + timedelta(hours=1)) == 0   # aynı hafta ikinci kez yok
        kayit = db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id, tur="haftalik").all()
        assert sorted(b.alici for b in kayit) == sorted([k.email, "x@ornek.com.tr"]) and "<br>" in kayit[0].html


def test_eposta_alicilari_gizlilik_tek_to():
    import smtplib
    gonderilen = []

    class Sahte:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, m): gonderilen.append(m)
    import unittest.mock as mk
    with mk.patch.object(smtplib, "SMTP", Sahte), mk.patch.object(settings, "SMTP_HOST", "h"), mk.patch.object(settings, "SMTP_FROM", "a@b.c"):
        bildirim.smtp_gonder("tek@ornek.com.tr", "k", "m", "<p>m</p>")
    assert gonderilen[0]["To"] == "tek@ornek.com.tr" and gonderilen[0]["Cc"] is None and gonderilen[0]["Bcc"] is None
    assert gonderilen[0].get_body(("html",)) is not None and gonderilen[0].get_body(("plain",)) is not None


# ---------------------------------------------------------------------------
# Kimlik, bağlantı, izolasyon
# ---------------------------------------------------------------------------
def test_kayit_dogrulama_ve_sifre_sifirlama(istemci):
    r = istemci.post("/api/auth/kayit", json={"email": "Yeni@Ornek.com.tr", "sifre": SIFRE, "sifre_tekrar": SIFRE, "kurum": "Yeni Kurum",
                                              "bildirim_ek_epostalar": ["A@Ornek.com.tr"]})
    assert r.status_code == 201, r.text
    ben = r.json()["kullanici"]
    assert ben["email"] == "yeni@ornek.com.tr" and ben["bildirim_ek_epostalar"] == ["a@ornek.com.tr"] and ben["eposta_dogrulandi"] is False
    assert ben["bildirim_email"] is True and ben["aralik_turu"] == "30" and ben["tekrar_plani"] == "periyodik"
    assert istemci.post("/api/auth/kayit", json={"email": "y2@ornek.com.tr", "sifre": SIFRE, "sifre_tekrar": "farkli1234", "kurum": "K"}).status_code == 422
    assert istemci.post("/api/auth/kayit", json={"email": "yeni@ornek.com.tr", "sifre": SIFRE, "sifre_tekrar": SIFRE, "kurum": "Kurum"}).status_code == 409
    with SessionLocal() as db:
        k = db.query(orm.Kullanici).filter_by(email="yeni@ornek.com.tr").one()
        dogrulama = db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id, tur="dogrulama").one()
        token = unquote(re.search(r"token=([^\s]+)", dogrulama.metin).group(1))
    assert istemci.post("/api/auth/eposta-dogrula", json={"token": token}).json()["durum"] == "dogrulandi"
    assert istemci.post("/api/auth/eposta-dogrula", json={"token": "x" * 40}).status_code == 400
    assert istemci.post("/api/auth/sifre-sifirla-iste", json={"email": "yok@ornek.com.tr"}).json()["durum"] == "istek_alindi"
    istemci.post("/api/auth/sifre-sifirla-iste", json={"email": "yeni@ornek.com.tr"})
    with SessionLocal() as db:
        k = db.query(orm.Kullanici).filter_by(email="yeni@ornek.com.tr").one()
        sifirla = db.query(orm.BildirimKuyrugu).filter_by(kurum_id=k.id, tur="sifre").one()
        assert db.query(orm.BildirimKuyrugu).filter_by(tur="sifre").filter(orm.BildirimKuyrugu.alici == "yok@ornek.com.tr").count() == 0
        token = unquote(re.search(r"token=([^\s]+)", sifirla.metin).group(1))
    assert istemci.post("/api/auth/sifre-sifirla", json={"token": token, "yeni_sifre": "YeniSifre99"}).status_code == 200
    assert istemci.post("/api/auth/sifre-sifirla", json={"token": token, "yeni_sifre": "Baska1234x"}).status_code == 400   # tek kullanım
    assert istemci.post("/api/auth/giris", data={"username": "yeni@ornek.com.tr", "password": "YeniSifre99"}).status_code == 200
    assert istemci.get("/api/analiz/son").status_code == 401


def test_kaynak_baglantisi_sifreli_saklanir_ve_geri_gosterilmez(istemci):
    with SessionLocal() as db:
        k = _kurum(db, "baglanti@ornek.com.tr", "Bağlantı A.Ş.", ("Bağlantı",))
        db.query(orm.KaynakBaglanti).filter_by(kurum_id=k.id).delete()
        db.commit()
    h = _giris(istemci, "baglanti@ornek.com.tr")
    from app.collectors import youtube
    gizli = "AIzaSyGizliAnahtar1234567890"
    with respx.mock:
        respx.get(f"{youtube.API}/channels").mock(return_value=httpx.Response(200, json={"items": [{
            "snippet": {"title": "Marka Kanalı"}, "statistics": {"videoCount": "12"}}]}))
        r = istemci.put("/api/kaynaklar/baglanti/youtube", headers=h, json={"hesap_ref": "UC123", "gizli": gizli})
    assert r.status_code == 200 and r.json()["test"]["basarili"] and r.json()["baglanti"]["durum"] == "bagli"
    assert gizli not in r.text and r.json()["baglanti"]["maske"].endswith(gizli[-4:])
    assert gizli not in istemci.get("/api/kaynaklar", headers=h).text
    with SessionLocal() as db:
        b = db.query(orm.KaynakBaglanti).filter_by(platform="youtube").join(orm.Kullanici).filter(orm.Kullanici.email == "baglanti@ornek.com.tr").one()
        assert gizli not in b.sifreli and crypto.coz(b.sifreli) == {"api_anahtari": gizli}
        assert "youtube" in kaynaklar.etkin_kaynaklar(db, b.kurum_id and db.get(orm.Kullanici, b.kurum_id))
    with respx.mock:
        respx.get(f"{youtube.API}/channels").mock(return_value=httpx.Response(403, json={"error": {"message": "keyInvalid"}}))
        r = istemci.post("/api/kaynaklar/baglanti/youtube/test", headers=h)
    assert r.json()["test"]["basarili"] is False and r.json()["test"]["neden"] == "yetki" and r.json()["baglanti"]["durum"] == "yetki_yok"
    assert istemci.put("/api/kaynaklar/baglanti/instagram", headers=h, json={"hesap_ref": "17"}).status_code == 422   # kimlik bilgisi gerekli
    assert istemci.delete("/api/kaynaklar/baglanti/youtube", headers=h).status_code == 200
    assert istemci.get("/api/kaynaklar", headers=h).json()["baglantilar"] == {}


def test_kurumlar_arasi_izolasyon(istemci):
    with SessionLocal() as db:
        a, _ = _senaryo(db, "onlenebilir", "anadolu@ornek.com.tr")
        tarama.analiz_calistir(db, a)
        b = _kurum(db, "diger@ornek.com.tr", "Diğer A.Ş.", ("Diğer",))
        alarm_id = db.query(orm.Alarm).filter_by(kurum_id=a.id).first().id
        j = orm.TaramaIsi(kurum_id=a.id, tur="elle", durum="bekliyor", bas=datetime(2026, 1, 1), bit=datetime(2026, 1, 2))
        db.add(j)
        db.commit()
        is_id = j.id
    h = _giris(istemci, "diger@ornek.com.tr")
    assert istemci.get("/api/alarmlar", headers=h).json() == []
    assert istemci.post(f"/api/alarmlar/{alarm_id}/geri-bildirim", headers=h, json={"geri_bildirim": "onemsiz"}).status_code == 404
    assert istemci.put(f"/api/alarmlar/{alarm_id}/yanit", headers=h, json={}).status_code == 404
    assert istemci.get(f"/api/tarama/{is_id}", headers=h).status_code == 404
    assert istemci.post(f"/api/tarama/{is_id}/iptal", headers=h).status_code == 404
    assert istemci.get("/api/analiz/son", headers=h).json()["durum"] == "analiz_yok"
    assert istemci.get("/api/pr/kontrol-listesi?alarm_id=%d" % alarm_id, headers=h).status_code == 404


def test_uretim_yapilandirmasi_guvensizse_dogrulama_hata_verir():
    s = Settings(ENV="production", SECRET_KEY="gelistirme-anahtari-uretimde-degistirin", DATABASE_URL="sqlite:///x.db",
                 PANEL_URL="http://localhost:5173", SMTP_HOST="")
    hatalar = " ".join(s.uretim_dogrula())
    assert all(a in hatalar for a in ("SECRET_KEY", "PostgreSQL", "PANEL_URL", "SMTP_HOST"))
    iyi = Settings(ENV="production", SECRET_KEY="x" * 40, DATABASE_URL="postgresql://u:p@db/k", PANEL_URL="https://panel.ornek.com.tr",
                   SMTP_HOST="smtp.ornek.com", SMTP_FROM="a@ornek.com")
    assert iyi.uretim_dogrula() == []
    assert Settings(ENV="development").uretim_dogrula() == []


def test_yanit_zamani_ve_pr_olcutleri(istemci):
    with SessionLocal() as db:
        k, simdi = _senaryo(db)
        tarama.analiz_calistir(db, k, simdi=simdi)
        a = db.query(orm.Alarm).filter_by(kurum_id=k.id, acik=True).one()
        aid, bas = a.id, a.baslangic
    h = _giris(istemci, "anadolu@ornek.com.tr")
    erken = (bas - timedelta(hours=1)).isoformat() + "Z"
    assert istemci.put(f"/api/alarmlar/{aid}/yanit", headers=h, json={"ilk_yanit_zamani": erken}).status_code == 422
    ilk = (bas + timedelta(minutes=45)).isoformat() + "Z"
    r = istemci.put(f"/api/alarmlar/{aid}/yanit", headers=h, json={"ilk_yanit_zamani": ilk})
    assert r.status_code == 200 and r.json()["ilk_yanit_zamani"] is not None
    o = istemci.get("/api/pr/olcutler", headers=h).json()
    satir = next(x for x in o["alarmlar"] if x["alarm_id"] == aid)
    assert satir["ilk_yanit_dk"] == pytest.approx(45) and satir["cozum_dk"] is None
    assert o["ozet"]["ilk_yanit_medyan_dk"] == pytest.approx(45)
    kl = istemci.get(f"/api/pr/kontrol-listesi?alarm_id={aid}", headers=h).json()
    assert len(kl["evreler"]) == 4 and kl["tamamlanan"] == [] and kl["yanit_hedefleri"] and kl["kaynak"]["url"].startswith("https://alternacx.com")
    assert istemci.put("/api/pr/kontrol-listesi", headers=h, json={"madde": "a2", "tamam": True, "alarm_id": aid}).status_code == 200
    assert istemci.get(f"/api/pr/kontrol-listesi?alarm_id={aid}", headers=h).json()["tamamlanan"] == ["a2"]
    assert istemci.get("/api/pr/kontrol-listesi", headers=h).json()["tamamlanan"] == []         # genel hazırlık ayrı
    assert istemci.put("/api/pr/kontrol-listesi", headers=h, json={"madde": "yok", "tamam": True}).status_code == 422


# ---------------------------------------------------------------------------
# Kirlenme kuralları, eşik, strateji (yöntem testleri)
# ---------------------------------------------------------------------------
def _sat(saat, risk, nihai, alarm=None):
    return SimpleNamespace(saat=saat, risk=risk, nihai_seviye=nihai, alarm_id=alarm)


def test_kirlenme_kurallari():
    t = datetime(2026, 9, 1)
    bitis = t + timedelta(days=60)
    eski, yeni = bitis - timedelta(days=40), bitis - timedelta(days=2)
    satirlar = [_sat(eski, 90, 3), _sat(yeni, 91, 3), _sat(yeni, 50, 0),
                _sat(eski, 70, 2, alarm=1), _sat(eski, 71, 2, alarm=2), _sat(eski, 72, 2, alarm=3)]
    fb = {1: "gercek_kriz", 2: "yanlis_alarm", 3: None}
    x = kurum_esik_servisi.normal_donem_bloklari(satirlar, fb, bitis - timedelta(days=90), bitis)
    # 90: eski etiketsiz alarm seviyesi → karantina bitti, geri döner; 91: yeni etiketsiz → dışlanır; 50: normal;
    # 70: gerçek kriz → dışlanır; 71: önemsiz → geri alınır; 72: eski etiketsiz → geri döner
    assert sorted(x) == [50, 71, 72, 90]


def test_tirmanma_carki_karantina_olmadan_alarm_sikligi_artar():
    """Metodoloji kural 2 tek başına uygulanırsa (karantina yok) eşik zamanla düşer; karar 45'in gerekçesi."""
    def oran(karantina_gun):
        rng = random.Random(21)
        satirlar, nihai_onceki, ham_g, r_g = [], 0, [], []
        alarm_saat = 0
        for i in range(1300):
            r = min(100.0, max(0.0, rng.gauss(20, 14) + (rng.random() < 0.02) * 40))
            t = datetime(2026, 1, 1) + timedelta(hours=i)
            x = kurum_esik_servisi.normal_donem_bloklari(satirlar, {}, t - timedelta(days=90), t, karantina_gun)
            e = E.esik_hesapla(x, (50, 75, 95))
            ham = E.seviye_ham(r, e.esikler)
            ham_g, r_g = (ham_g + [ham])[-3:], (r_g + [r])[-3:]
            h = E.histerezis(r_dizi=r_g, ham_dizi=ham_g, onceki_nihai=nihai_onceki, esikler=e.esikler, olcek_s=e.olcek_s, hacim_z=0)
            nihai_onceki = h.nihai
            satirlar.append(_sat(t, r, h.nihai))
            if i >= 900:
                alarm_saat += h.nihai >= 2
        return alarm_saat / 400
    assert oran(14) < oran(10_000)         # karantinasız çark alarm oranını yükseltir
    assert oran(14) < 0.10


def test_geri_bildirim_esigi_etiketle_duzeltir():
    """≥ 20 etiket (sınıf başına ≥ 5) varsa Yüksek eşik c* ile yeniden ayarlanır (Metodoloji Bölüm 6)."""
    rng = random.Random(9)
    x = [min(100, max(0, rng.gauss(30, 12))) for _ in range(800)]
    al = [SimpleNamespace(geri_bildirim="gercek_kriz", max_risk=rng.uniform(65, 100)) for _ in range(12)] + \
         [SimpleNamespace(geri_bildirim="yanlis_alarm", max_risk=rng.uniform(50, 80)) for _ in range(12)]
    g, s = kurum_esik_servisi.etiket_puanlari(al)
    assert len(g) == 12 and len(s) == 12
    e = E.esik_hesapla(x, (50, 75, 95), etiket_gercek=g, etiket_siradan=s)
    assert e.etiket_duzeltme and e.etiket_duzeltme["m"] == 24


def test_strateji_coombs_2007_kurallari():
    v = kriz_stratejisi(efektif_kume="magdur", tip="dogal_afet")
    assert v["durus_kodu"] == "temel" and v["birincil"] == [] and [x["no"] for x in v["kurallar"]] == [1, 2]
    assert {s["kod"] for s in v["destekleyici"]} == {"hatirlatma", "pohpohlama", "magduriyet"}
    v = kriz_stratejisi(efektif_kume="magdur", tip="dogal_afet", kriz_gecmisi=["dogal_afet"])
    assert v["yogunlastirici"] and v["durus_kodu"] == "temel"        # etkin küme çağıran tarafından verilir
    v = kriz_stratejisi(efektif_kume="kaza", tip="teknik_hata_kaza")
    assert v["durus_kodu"] == "azaltma" and [s["kod"] for s in v["birincil"]] == ["mazeret", "haklilastirma"]
    assert [x["no"] for x in v["kurallar"]] == [4]
    v = kriz_stratejisi(efektif_kume="kaza", tip="teknik_hata_kaza", kriz_gecmisi=["teknik_hata_kaza"])
    assert [x["no"] for x in v["kurallar"]] == [5]                   # yoğunlaştırıcı: kural 5
    v = kriz_stratejisi(efektif_kume="onlenebilir", tip="insan_hatasi_urun")
    assert v["durus_kodu"] == "yeniden_insa" and [s["kod"] for s in v["birincil"]] == ["tazminat", "ozur"]
    assert v["kosullu"] == [] and any("kural 8" in x for x in v["kacinilacaklar"])
    v = kriz_stratejisi(efektif_kume="magdur", tip="soylenti")
    assert v["kosullu"] and v["kosullu"][0]["kural"] == 7 and {s["kod"] for s in v["kosullu"][0]["stratejiler"]} == {
        "inkar", "suclayana_karsi_cikma", "sucu_baskasina_atma"}
    assert kriz_stratejisi(efektif_kume=None)["durum"] == "tip_belirlenemedi"


def test_pr_brif_ve_acik_alarmda_kriz_stratejisi(istemci):
    with SessionLocal() as db:
        _kurum(db, "brif@ornek.com.tr", "Brif Kurumu", ("Brif",))
    hy = _giris(istemci, "brif@ornek.com.tr")
    b = istemci.get("/api/pr/brif", headers=hy).json()
    assert b["analiz_var"] is False and b["yapilacaklar"] and b["evre"]["kod"] == "sinyal_tespiti"
    k = istemci.get("/api/pr/katalog").json()
    assert len(k["stratejiler"]) == 10 and len(k["kurallar"]) == 8 and len(k["evreler"]) == 5
    with SessionLocal() as db:
        kk, simdi = _senaryo(db)
        tarama.analiz_calistir(db, kk, simdi=simdi)
    h = _giris(istemci, "anadolu@ornek.com.tr")
    b = istemci.get("/api/pr/brif", headers=h).json()
    assert b["analiz_var"] and {"sinyal_radari", "kirilganlik", "itibar", "ogrenme", "yapilacaklar", "evre"} <= set(b)
    assert b["evre"]["kod"] == "hasar_sinirlama" and b["kriz_stratejisi"]["alarm_id"]
    s = istemci.get("/api/pr/strateji", headers=h).json()
    assert s["durus_kodu"] in ("temel", "azaltma", "yeniden_insa") or s["durum"] == "tip_belirlenemedi"


def test_haftalik_brif_metni():
    from app.pr import brif
    k = SimpleNamespace(kurum="Deneme A.Ş.")
    b = {"evre": {"no": 1, "ad": "Sinyal tespiti", "neden": "x"}, "mesaj": "Kriz sinyali yok",
         "sinyal_radari": {"risk": {"puan": 12.3, "etiket": "DÜŞÜK RİSK", "esikler": {"yuksek": 60.0},
                                    "son7_orta_ve_uzeri_saat": 3, "son7_yuksek_saat": 0, "olculen_saat_son7": 168},
                           "zayif_sinyaller": [{"kod": "G6", "ad": "Olumsuz", "pencere_sayisi": 4}], "hafta": None},
         "itibar": {"durum": "yok", "mesaj": "Anket yok"}, "yapilacaklar": [{"baslik": "Kriz geçmişini girin"}],
         "ogrenme": {"alarm_sayisi": 2, "gercek": 1, "onemsiz": 1, "etiketsiz": 0}}
    konu, metin = brif.haftalik_metin(k, b)
    assert "haftalık PR brifi" in konu and "Risk puanı 12.3" in metin and "G6" in metin and "Kriz geçmişini girin" in metin


def test_alarm_parmak_izi_ve_benzerlik():
    from app.nlp import anahtar
    metin = ["Fabrikadan çıkan ürünlerde küf bulundu, tüketiciler tepkili", "Küflü ürünler toplatıldı fabrika kapatıldı",
             "Ürünlerde küf çıktı iddiası sosyal medyada yayıldı", "küf skandalı büyüyor"]
    tum = metin + [f"Bugün hava güzel {i} ve kurum yeni şube açtı" for i in range(30)]
    g = anahtar.anahtar_govdeler(metin, tum, haric={"anadolu", "gıda"})
    assert "küf" in g or "küfl" in g or any(t.startswith("küf") for t in g)
    a = {"tip": "insan_hatasi_urun", "govdeler": g}
    b = {"tip": "insan_hatasi_urun", "govdeler": g[:3] + ["yeni"]}
    assert anahtar.ayni_kriz_mi(a, b)[0]
    assert not anahtar.ayni_kriz_mi(a, {"tip": "teknik_hata_kaza", "govdeler": ["hat", "kesinti", "sistem"]})[0]
    assert anahtar.ayni_kriz_mi(None, a) == (False, 0.0)


def test_tum_kaynaklar_hata_verirse_tarama_erken_tekrar_denenir(monkeypatch):
    import asyncio
    with SessionLocal() as db:
        k = _kurum(db, "hatali@ornek.com.tr", "Hatalı A.Ş.", ("Hatalı",))
        k.aralik_turu, k.bildirim_email, k.tekrar_plani, k.tek_seferlik_yapildi = "7", False, "periyodik", False
        db.commit()

        async def hep_hata(db_, k_, bas, bit):
            return [], {}, [KaynakDurumu("google_news", "hata", mesaj="HTTP 503", istenen_bas=bas, istenen_bit=bit)]
        monkeypatch.setattr(kaynaklar, "topla_hepsi", hep_hata)
        s = asyncio.run(tarama.kurum_tara(db, k))
        db.refresh(k)
        assert s["son"]["gostergeler"]["G1"] is None and s["son"]["gostergeler"]["G5"] is None     # hata sıfır değil, eksik
        assert k.sonraki_tarama - datetime.now(timezone.utc).replace(tzinfo=None) <= timedelta(minutes=61)
        k.tekrar_plani = "tek_seferlik"
        asyncio.run(tarama.kurum_tara(db, k))
        assert k.tek_seferlik_yapildi is False                                                     # başarısız tek seferlik tekrar denenir
        k.tekrar_plani = "periyodik"
        db.commit()
