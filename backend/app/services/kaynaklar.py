"""Kaynak orkestrasyonu: hangi kaynaklar etkin, hangi aralık eksik, toplama, kapsam ve sağlık kaydı."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.collectors import bing_news, google_news, google_trends, instagram, reddit_acik, rss, x, youtube
from app.collectors.base import KAYNAK_ADI, KAYNAK_TURU, KaynakDurumu, Toplanan, atlandi, sorgu_terimleri, utc_simdi
from app.config import settings
from app.core import crypto
from app.models.orm import KaynakBaglanti, KaynakKapsam, KaynakSaglik, Kullanici

log = logging.getLogger(__name__)
ACIK_KAYNAKLAR = ("google_news", "bing_news", "rss", "reddit")
BAGLI_PLATFORMLAR = ("youtube", "x", "instagram")
BINDIRME = timedelta(hours=2)            # ardışık taramalar arasında örtüşme (gecikmeli yayınlanan içerik için)


class AralikHatasi(ValueError):
    pass


def aralik_coz(k: Kullanici, simdi: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Kurumun seçtiği analiz aralığı [bas, bit). Bit, tamamlanmış son saattir (özel aralıkta kurumun seçtiği gün sonu)."""
    simdi = simdi or utc_simdi()
    bit = simdi.replace(minute=0, second=0, microsecond=0)
    if k.aralik_turu == "ozel":
        if not k.ozel_baslangic or not k.ozel_bitis:
            raise AralikHatasi("Özel aralık için başlangıç ve bitiş tarihi gerekli")
        bas = k.ozel_baslangic.replace(minute=0, second=0, microsecond=0)
        bit = min(bit, (k.ozel_bitis + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))
    else:
        gun = int(k.aralik_turu or 30)
        bas = bit - timedelta(days=gun)
    if bit <= bas:
        raise AralikHatasi("Bitiş tarihi başlangıçtan sonra olmalı")
    if (bit - bas) > timedelta(days=settings.EN_FAZLA_ANALIZ_GUN):
        raise AralikHatasi(f"Aralık en fazla {settings.EN_FAZLA_ANALIZ_GUN} gün olabilir")
    return bas, bit


def canli_aralik(k: Kullanici, bit: datetime) -> bool:
    """Aralık bugüne dayanıyorsa canlı izleme; geçmişte bitiyorsa geriye dönük inceleme (alarm/bildirim üretmez)."""
    return k.aralik_turu != "ozel" or (utc_simdi() - bit) < timedelta(days=1)


def etkin_kaynaklar(db: Session, k: Kullanici) -> list[str]:
    liste: list[str] = []
    if k.acik_kaynak:
        liste += ["google_news", "bing_news", "reddit"]
        if k.ek_rss or settings.ERKIS_EK_RSS.strip():
            liste.append("rss")
    for b in db.query(KaynakBaglanti).filter(KaynakBaglanti.kurum_id == k.id).all():
        if b.durum != "dogrulanmadi" or b.son_test:
            liste.append(b.platform)
    return liste


# ---------------------------------------------------------------------------
# Kapsam
# ---------------------------------------------------------------------------
def _birlestir(araliklar: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    sonuc: list[tuple[datetime, datetime]] = []
    for a, b in sorted(araliklar):
        if sonuc and a <= sonuc[-1][1] + timedelta(minutes=1):
            sonuc[-1] = (sonuc[-1][0], max(sonuc[-1][1], b))
        else:
            sonuc.append((a, b))
    return sonuc


def kapsam_oku(db: Session, k: Kullanici, kaynaklar: Optional[list[str]] = None) -> dict[str, list[tuple[datetime, datetime]]]:
    q = db.query(KaynakKapsam).filter(KaynakKapsam.kurum_id == k.id)
    if kaynaklar is not None:
        q = q.filter(KaynakKapsam.kaynak.in_(kaynaklar))
    ham: dict[str, list[tuple[datetime, datetime]]] = {}
    for r in q.all():
        ham.setdefault(r.kaynak, []).append((r.bas, r.bit))
    return {s: _birlestir(v) for s, v in ham.items()}


def kapsam_ekle(db: Session, k: Kullanici, kaynak: str, bas: datetime, bit: datetime) -> None:
    mevcut = db.query(KaynakKapsam).filter_by(kurum_id=k.id, kaynak=kaynak).all()
    birlesik = _birlestir([(r.bas, r.bit) for r in mevcut] + [(bas, bit)])
    for r in mevcut:
        db.delete(r)
    for a, b in birlesik:
        db.add(KaynakKapsam(kurum_id=k.id, kaynak=kaynak, bas=a, bit=b))


def eksik_baslangic(araliklar: list[tuple[datetime, datetime]], bas: datetime, bit: datetime) -> Optional[datetime]:
    """[bas, bit) içinde kapsanmamış en erken an; tamamen kapsanmışsa None (örtüşme payı bit'ten düşülür)."""
    imleç = bas
    for a, b in araliklar:
        if a > imleç:
            return imleç
        imleç = max(imleç, b)
        if imleç >= bit:
            return None
    return max(bas, imleç - BINDIRME) if imleç < bit else None


# ---------------------------------------------------------------------------
# Toplama
# ---------------------------------------------------------------------------
def _kimlik(db: Session, k: Kullanici, platform: str) -> Optional[tuple[KaynakBaglanti, dict]]:
    b = db.query(KaynakBaglanti).filter_by(kurum_id=k.id, platform=platform).first()
    if b is None:
        return None
    try:
        return b, crypto.coz(b.sifreli)
    except ValueError as e:
        b.durum, b.son_hata = "hata", str(e)
        return None


async def _bagli_topla(platform: str, terimler: list[str], bas: datetime, bit: datetime, kimlik: dict, hesap: str):
    if platform == "youtube":
        return await youtube.topla(terimler, bas, bit, kimlik.get("api_anahtari", ""), hesap)
    if platform == "x":
        return await x.topla(terimler, bas, bit, kimlik.get("bearer_token", ""), hesap)
    return await instagram.topla(terimler, bas, bit, kimlik.get("erisim_belirteci", ""), hesap)


async def topla_hepsi(db: Session, k: Kullanici, bas: datetime, bit: datetime) -> tuple[list[Toplanan], dict[datetime, float], list[KaynakDurumu]]:
    """Etkin her kaynak için yalnız kapsanmamış aralığı toplar. Bir kaynağın hatası diğerlerini etkilemez."""
    terimler = sorgu_terimleri(k.kurum, k.izleme_terimleri)
    kapsam = kapsam_oku(db, k)
    gorevler, adlar, araliklar = [], [], []

    def ekle(ad: str, fonk):
        e = eksik_baslangic(kapsam.get(ad, []), bas, bit)
        if e is None:
            return
        adlar.append(ad)
        araliklar.append((e, bit))
        gorevler.append(fonk(e))

    if k.acik_kaynak:
        ekle("google_news", lambda e: google_news.topla(terimler, e, bit))
        ekle("bing_news", lambda e: bing_news.topla(terimler, e, bit))
        ekle("reddit", lambda e: reddit_acik.topla(terimler, e, bit) if settings.REDDIT_ACIK_ARAMA
             else _async(atlandi("reddit", "Reddit genel arama kapalı", e, bit)))
        adresler = list(k.ek_rss or []) + [a.strip() for a in settings.ERKIS_EK_RSS.split(",") if a.strip()]
        if adresler:
            ekle("rss", lambda e: rss.topla(adresler, terimler, e, bit))
    for platform in BAGLI_PLATFORMLAR:
        kim = _kimlik(db, k, platform)
        if kim is None:
            continue
        b, kimlik = kim
        ekle(platform, lambda e, p=platform, kk=kimlik, h=b.hesap_ref: _bagli_topla(p, terimler, e, bit, kk, h))

    sonuclar = await asyncio.gather(*gorevler, return_exceptions=True)
    ogeler: list[Toplanan] = []
    durumlar: list[KaynakDurumu] = []
    for ad, (e, _), s in zip(adlar, araliklar, sonuclar):
        if isinstance(s, Exception):
            log.exception("%s toplayıcısı beklenmeyen hata verdi", ad, exc_info=s)
            durumlar.append(KaynakDurumu(ad, "hata", mesaj=f"Beklenmeyen hata: {type(s).__name__}", istenen_bas=e, istenen_bit=bit))
            continue
        liste, durum = s
        ogeler += liste
        durumlar.append(durum)

    trends: dict[datetime, float] = {}
    if k.acik_kaynak:
        trends, td = await asyncio.to_thread(google_trends.pytrends_topla, k.kurum, settings.GOOGLE_TRENDS_ENABLED)
        td.istenen_bas, td.istenen_bit = bas, bit
        durumlar.append(td)
    haric = [h.lower() for h in (k.haric_terimler or []) if h.strip()]
    if haric:
        ogeler = [o for o in ogeler if not any(h in (o.metin or o.baslik).lower() for h in haric)]
    return ogeler, trends, durumlar


async def _async(deger):
    return deger


def durumlari_kaydet(db: Session, k: Kullanici, durumlar: list[KaynakDurumu], is_id: Optional[int]) -> None:
    for d in durumlar:
        db.add(KaynakSaglik(kurum_id=k.id, is_id=is_id, kaynak=d.kaynak, durum=d.durum, adet=d.adet,
                            istenen_bas=d.istenen_bas, istenen_bit=d.istenen_bit, ulasilan_bas=d.ulasilan_bas,
                            ulasilan_bit=d.ulasilan_bit, mesaj=d.mesaj or ""))
        if d.kaynak in KAYNAK_TURU and d.ulasilan_bas and d.ulasilan_bit and d.ulasilan_bit == d.istenen_bit:
            kapsam_ekle(db, k, d.kaynak, d.ulasilan_bas, d.ulasilan_bit)
        if d.kaynak in BAGLI_PLATFORMLAR:
            b = db.query(KaynakBaglanti).filter_by(kurum_id=k.id, platform=d.kaynak).first()
            if b is not None and d.durum != "atlandi":
                if d.durum in ("tamam", "kismi"):
                    b.durum, b.son_basari = "bagli", utc_simdi()
                    b.son_hata = d.mesaj if d.durum == "kismi" else ""
                else:
                    b.durum = "yetki_yok" if "yetki" in d.mesaj.lower() or "HTTP 40" in d.mesaj else "hata"
                    b.son_hata = d.mesaj


def kaynak_ozeti(db: Session, k: Kullanici, bas: datetime, bit: datetime) -> list[dict]:
    """Panel için kaynak başına durum: bağlı değil / hata / kapsanıyor-içerik yok (gerçek sıfır) / içerik var."""
    from sqlalchemy import func
    from app.models.orm import Icerik
    etkin = etkin_kaynaklar(db, k)
    kapsam = kapsam_oku(db, k)
    adet = dict(db.query(Icerik.platform, func.count(Icerik.id)).filter(
        Icerik.kurum_id == k.id, Icerik.tarih >= bas, Icerik.tarih < bit).group_by(Icerik.platform).all())
    son: dict[str, KaynakSaglik] = {}
    for s in db.query(KaynakSaglik).filter(KaynakSaglik.kurum_id == k.id).order_by(KaynakSaglik.zaman, KaynakSaglik.id).all():
        son[s.kaynak] = s
    liste = []
    for ad in (*ACIK_KAYNAKLAR, *BAGLI_PLATFORMLAR):
        s = son.get(ad)
        araliklar = kapsam.get(ad, [])
        kapsanan = sum((min(b, bit) - max(a, bas)).total_seconds() for a, b in araliklar if min(b, bit) > max(a, bas))
        oran = kapsanan / max((bit - bas).total_seconds(), 1)
        n = adet.get(ad, 0)
        if ad not in etkin:
            durum = "baglanti_yok" if ad in BAGLI_PLATFORMLAR else "kapali"
        elif s is None and oran <= 0:
            durum = "taranmadi"
        elif s is not None and s.durum == "hata":
            durum = "hata"
        elif oran <= 0:
            durum = "kapsam_yok"
        elif n == 0:
            durum = "icerik_yok"
        else:
            durum = "icerik_var"
        liste.append({"kaynak": ad, "ad": KAYNAK_ADI[ad], "tur": KAYNAK_TURU[ad], "durum": durum, "etkin": ad in etkin,
                      "icerik": n, "kapsam_orani": round(oran, 4),
                      "son_tarama": s.zaman.isoformat() if s else None, "son_durum": s.durum if s else None,
                      "mesaj": (s.mesaj if s else "") or "",
                      "ulasilan_bas": s.ulasilan_bas.isoformat() if s and s.ulasilan_bas else None})
    return liste


def trend_kaynak_adi() -> str:
    return KAYNAK_ADI["google_trends"]


__all__ = ["aralik_coz", "canli_aralik", "etkin_kaynaklar", "kapsam_oku", "topla_hepsi", "durumlari_kaydet", "kaynak_ozeti",
           "AralikHatasi", "math"]
