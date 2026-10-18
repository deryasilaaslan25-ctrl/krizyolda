"""Yalnızca testler için sentetik içerik üreticisi. Ürün kodunda sentetik veri üretilmez.

Sabit tohumlu 30 günlük saatlik akış; senaryo son saatlerde olumsuz içerik artışı enjekte eder."""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.orm import Alarm, Analiz, Icerik, KaynakKapsam, Kullanici, RiskOlcumu, TrendDegeri
from app.services.nlp_hatti import icerige_uygula

OLAGAN = [
    "{k} yeni ürününü tanıttı, merak ediyorum",
    "{k} hakkında bilgi arıyorum, önerisi olan var mı",
    "bugün {k} ile ilgili bir etkinliğe katıldım, güzel bir deneyimdi",
    "{k} müşteri hizmetleri hızlı yanıt verdi, teşekkürler",
    "{k} kampanyası başlamış",
    "{k} için sıra bekliyorum",
    "{k} fiyatları biraz arttı galiba",
    "{k} ile ilgili haberi okudum",
]
HABER_OLAGAN = ["{k} yeni yatırım planını açıkladı", "{k} yıl sonu hedeflerini paylaştı",
                "{k} sosyal sorumluluk projesine destek verdi", "{k} yöneticisi basın toplantısı düzenledi"]
KRIZ = {
    "onlenebilir": {
        "sosyal": ["{k} ürününden zehirlendik, rezalet", "{k} bozuk ürün satıyor, çok öfkeliyim",
                   "{k} tarihi geçmiş ürün, iğrenç, bir daha almam", "herkesi uyarıyorum {k} ürünlerini almayın",
                   "{k} boykot edilmeli, çocuğum hastanelik oldu", "{k} hijyensiz üretim, korkunç ve tehlikeli"],
        "haber": ["{k} ürünlerinde zehirlenme şüphesi, soruşturma başlatıldı",
                  "{k} bozuk ürün iddiaları sonrası toplatma kararı", "{k} ürünü tüketen çok sayıda kişi hastaneye kaldırıldı"],
        "sessiz": ["{k} ürününün tadı garip geldi", "{k} ürününde bir sorun mu var", "{k} ürününden sonra midem bulandı"],
    },
    "kaza": {
        "sosyal": ["{k} su kesintisi yine sürüyor, bıktık", "{k} teknik arıza nedeniyle hizmet yok, sinir bozucu",
                   "{k} sistem çöktü, başvurular yapılamıyor", "{k} erişim kesintisi ne zaman bitecek"],
        "haber": ["{k} teknik arıza nedeniyle hizmet veremedi", "{k} bölgesinde uzun süreli kesinti"],
        "sessiz": ["{k} sitesi yavaş açılıyor", "{k} hizmetinde gecikme var"],
    },
}


def _poisson(r: random.Random, lam: float) -> int:
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= L:
            return k
        k += 1


def veri_uret(db: Session, k: Kullanici, senaryo: str, simdi: datetime, tohum: int, gun: int = 30) -> int:
    r = random.Random(tohum)
    ad = k.kurum
    bitis = simdi.replace(minute=0, second=0, microsecond=0)
    n = gun * 24 + 1
    bas = bitis - timedelta(hours=n)
    platformlar = ["reddit"]
    say = 0
    kriz_bas = n - 6          # son 6 saat patlama
    sessiz_bas = n - 18       # öncesinde 12 saat sessiz birikim
    for h in range(n):
        t0 = bas + timedelta(hours=h)
        gunluk = 1.0 + 0.5 * math.sin(2 * math.pi * ((t0.hour + 3) % 24 - 8) / 24)
        lam_sosyal, lam_haber = 3.0 * gunluk, 0.25
        sablon_s, sablon_h = OLAGAN, HABER_OLAGAN
        kriz_orani, etkilesim = 0.0, 1.0
        if senaryo in KRIZ and h >= sessiz_bas:
            if h >= kriz_bas:
                carpan = 6.0 if senaryo == "onlenebilir" else 3.0
                lam_sosyal *= carpan
                lam_haber = 2.0 if senaryo == "onlenebilir" else 0.8
                kriz_orani, etkilesim = 0.85, 5.0
                sablon_s, sablon_h = KRIZ[senaryo]["sosyal"], KRIZ[senaryo]["haber"]
            else:
                lam_sosyal *= 1.4
                kriz_orani, etkilesim = 0.5, 1.6
                sablon_s = KRIZ[senaryo]["sessiz"]
        for j in range(_poisson(r, lam_sosyal)):
            metin = r.choice(sablon_s if r.random() < max(kriz_orani, 0.0) else OLAGAN).format(k=ad)
            if kriz_orani == 0.0:
                metin = r.choice(OLAGAN).format(k=ad)
            plat = r.choice(platformlar)
            ic = Icerik(kurum_id=k.id, platform=plat, tur="sosyal", dis_id=f"s-{h}-{j}", yazar=f"kullanici{r.randint(1, 5000)}",
                        metin=metin, url="", tarih=t0 + timedelta(minutes=r.randint(0, 59)),
                        begeni=_poisson(r, 4 * etkilesim), yorum=_poisson(r, 1 * etkilesim),
                        paylasim=_poisson(r, 0.5 * etkilesim) if plat == "x" else 0)
            icerige_uygula(ic, ad)
            db.add(ic)
            say += 1
        for j in range(_poisson(r, lam_haber)):
            sab = sablon_h if (kriz_orani >= 0.85 and r.random() < 0.9) else HABER_OLAGAN
            metin = r.choice(sab).format(k=ad)
            ic = Icerik(kurum_id=k.id, platform=r.choice(["google_news", "bing_news"]), tur="haber", dis_id=f"s-h-{h}-{j}",
                        yazar=r.choice(["Ajans A", "Gazete B", "Portal C"]), baslik=metin, metin=metin, url="",
                        tarih=t0 + timedelta(minutes=r.randint(0, 59)))
            icerige_uygula(ic, ad)
            db.add(ic)
            say += 1
        trend = 20 + 10 * gunluk + r.gauss(0, 3)
        if senaryo in KRIZ and h >= kriz_bas:
            trend = 85 + r.gauss(0, 5) if senaryo == "onlenebilir" else 55 + r.gauss(0, 5)
        db.add(TrendDegeri(kurum_id=k.id, zaman=t0, deger=max(0.0, min(100.0, round(trend))), kaynak="test"))
    kapsam = db.query(KaynakKapsam).filter_by(kurum_id=k.id)
    kapsam.delete(synchronize_session=False)
    for ad in ("google_news", "bing_news", "reddit"):
        db.add(KaynakKapsam(kurum_id=k.id, kaynak=ad, bas=bas, bit=bitis))
    db.commit()
    return say


def sifirla(db: Session, k: Kullanici, simdi: datetime, senaryo: str = "yok", gun: int = 30) -> int:
    for model in (RiskOlcumu, Icerik, TrendDegeri, Analiz, Alarm):
        db.query(model).filter(model.kurum_id == k.id).delete(synchronize_session=False)
    db.commit()
    return veri_uret(db, k, senaryo, simdi, tohum=1000 + k.id, gun=gun)
