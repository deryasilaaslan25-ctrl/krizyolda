"""Kurum bilgi profili: seçilen aralıktaki hacim, duygu, kaynak ve olağan düzey özeti."""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.collectors.base import KAYNAK_ADI
from app.core.security import gecerli_kullanici_al
from app.database import get_db
from app.models.orm import Icerik, Kullanici
from app.services import kaynaklar

router = APIRouter(prefix="/api/kurum", tags=["kurum"])
GUN_ADI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
SINIRLAMA = ("Sayılar yalnızca erişilebilen kaynaklara ve kapsanan tarihlere aittir. Kaynaklar aynı kapsamı sunmaz; "
             "kampanya, tatil, haber gündemi ve kaynak değişimi ayrıştırılmadan 'olağan düzey' kesin kabul edilmemelidir.")


def _medyan_iqr(v: list[float]) -> dict | None:
    if len(v) < 4:
        return None
    q = statistics.quantiles(v, n=4, method="inclusive")
    return {"medyan": statistics.median(v), "q1": q[0], "q3": q[2]}


@router.get("/bilgi-profili")
def bilgi_profili(k: Kullanici = Depends(gecerli_kullanici_al), db: Session = Depends(get_db)):
    bas, bit = kaynaklar.aralik_coz(k)
    satirlar = db.query(Icerik).filter(Icerik.kurum_id == k.id, Icerik.tarih >= bas, Icerik.tarih < bit).all()
    gunluk: dict = defaultdict(lambda: {"sosyal": 0, "haber": 0, "olumsuz": 0, "olumlu": 0, "notr": 0, "etkilesim": 0})
    platform, duygu, konu = Counter(), Counter(), Counter()
    for i in satirlar:
        g = gunluk[i.tarih.date()]
        g[i.tur] += 1
        g[i.duygu_etiketi or "notr"] += 1
        g["etkilesim"] += (i.begeni or 0) + (i.yorum or 0) + (i.paylasim or 0)
        platform[i.platform] += 1
        duygu[i.duygu_etiketi or "belirsiz"] += 1
        tip = (i.scct or {}).get("tip_adi")
        if tip and i.duygu_etiketi == "olumsuz":
            konu[tip] += 1
    gun_sayisi = max((bit - bas).days, 1)
    gunler, d = [], bas.date()
    while d < bit.date():
        g = gunluk.get(d, {"sosyal": 0, "haber": 0, "olumsuz": 0, "olumlu": 0, "notr": 0, "etkilesim": 0})
        gunler.append({"tarih": d.isoformat(), **g, "toplam": g["sosyal"] + g["haber"]})
        d = d.fromordinal(d.toordinal() + 1)
    sayilar = [g["toplam"] for g in gunler]
    hafta_ritmi = []
    for w in range(7):
        v = [g["toplam"] for g in gunler if _gun(g["tarih"]) == w]
        hafta_ritmi.append({"gun": GUN_ADI[w], "ortalama": (sum(v) / len(v)) if v else None, "gun_sayisi": len(v)})
    haftalik: dict = defaultdict(lambda: [0, 0])
    for g in gunler:
        y, h, _ = _iso(g["tarih"])
        haftalik[f"{y}-H{h:02d}"][0] += g["toplam"]
        haftalik[f"{y}-H{h:02d}"][1] += g["olumsuz"]
    toplam = len(satirlar)
    olumsuz = duygu.get("olumsuz", 0)
    ozet = kaynaklar.kaynak_ozeti(db, k, bas, bit)
    kapsam_ort = (sum(x["kapsam_orani"] for x in ozet if x["etkin"]) / max(sum(1 for x in ozet if x["etkin"]), 1))
    return {
        "aralik": {"bas": bas.isoformat(), "bit": bit.isoformat(), "gun": gun_sayisi},
        "toplam": toplam, "gunluk_ortalama": toplam / gun_sayisi, "haftalik_ortalama": toplam / gun_sayisi * 7,
        "duygu": {a: duygu.get(a, 0) for a in ("olumlu", "olumsuz", "notr")} | {"belirsiz": duygu.get("belirsiz", 0)},
        "olumsuz_oran": (olumsuz / toplam) if toplam else None,
        "olagan_duzey": _medyan_iqr([float(s) for s in sayilar]),
        "hafta_ritmi": hafta_ritmi,
        "gunluk": gunler,
        "haftalik": [{"hafta": h, "toplam": v[0], "olumsuz": v[1], "olumsuz_oran": (v[1] / v[0]) if v[0] else None}
                     for h, v in sorted(haftalik.items())],
        "kaynak_dagilimi": [{"kaynak": p, "ad": KAYNAK_ADI.get(p, p), "adet": n} for p, n in platform.most_common()],
        "konular": [{"konu": t, "adet": n} for t, n in konu.most_common(8)],
        "kaynak_ozeti": ozet,
        "kapsam_orani": kapsam_ort,
        "sinirlama": SINIRLAMA,
    }


def _gun(iso: str) -> int:
    from datetime import date
    return date.fromisoformat(iso).weekday()


def _iso(iso: str):
    from datetime import date
    return date.fromisoformat(iso).isocalendar()
