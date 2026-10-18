from fastapi.testclient import TestClient

from app.main import app

SIFRE = "Guclu1234"


def test_saglik_ve_katalog():
    with TestClient(app) as c:
        assert c.get("/api/saglik").json()["katalog_hatalari"] == []
        lit = c.get("/api/literatur").json()
        assert "kaynaklar" in lit


def test_yetkisiz_erisim_ve_kayit_dogrulamalari():
    with TestClient(app) as c:
        for yol in ("/api/analiz/son", "/api/kaynaklar", "/api/tarama", "/api/beyin", "/api/alarmlar", "/api/kurum/profil"):
            assert c.get(yol).status_code == 401, yol
        assert c.get("/api/uzman/durum").status_code == 401
        govde = {"email": "api@ornek.com.tr", "sifre": SIFRE, "sifre_tekrar": SIFRE, "kurum": "Api Kurumu"}
        assert c.post("/api/auth/kayit", json={**govde, "sifre_tekrar": "farkli1234"}).status_code == 422
        assert c.post("/api/auth/kayit", json={**govde, "sifre": "kisa", "sifre_tekrar": "kisa"}).status_code == 422
        assert c.post("/api/auth/kayit", json=govde).status_code == 201
        assert c.post("/api/auth/kayit", json=govde).status_code == 409
        r = c.post("/api/auth/giris", data={"username": "api@ornek.com.tr", "password": "yanlis-sifre"})
        assert r.status_code == 401


def test_ilk_giris_bos_durum_ve_tarama_isi_kuyruga_alinir():
    with TestClient(app) as c:
        r = c.post("/api/auth/giris", data={"username": "api@ornek.com.tr", "password": SIFRE})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert c.get("/api/analiz/son", headers=h).json()["durum"] == "analiz_yok"
        j = c.post("/api/tarama", headers=h)
        assert j.status_code == 202 and j.json()["durum"] == "bekliyor"
        assert c.post("/api/tarama", headers=h).json()["id"] == j.json()["id"]          # tekrar tıklama mükerrer iş üretmez
        assert c.post(f"/api/tarama/{j.json()['id']}/iptal", headers=h).json()["durum"] == "iptal"
        kay = c.get("/api/kaynaklar", headers=h).json()
        durum = {x["kaynak"]: x["durum"] for x in kay["kaynaklar"]}
        assert durum["youtube"] == "baglanti_yok" and durum["google_news"] == "taranmadi"
        b = c.get("/api/beyin", headers=h).json()
        assert b["beyin2"]["etkin"] is False and b["beyin2"]["neden"] == "uzman_formu_yok"


def test_bilgi_profili_bos_kurumda_olagan_duzey_uretmez():
    with TestClient(app) as c:
        r = c.post("/api/auth/giris", data={"username": "api@ornek.com.tr", "password": SIFRE})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        p = c.get("/api/kurum/bilgi-profili", headers=h).json()
        assert p["toplam"] == 0 and p["olumsuz_oran"] is None and p["aralik"]["gun"] == 30
        assert len(p["gunluk"]) == 30 and p["sinirlama"]
