"""Tek içeriğin NLP'den geçirilmesi ve ORM ↔ analiz dönüşümü."""
from __future__ import annotations

import os
from typing import Optional

from app.indicators.compute import IslenmisIcerik
from app.models.orm import Icerik
from app.nlp import behavioral, scct, sentiment
from app.nlp.lexicon import sozluk_al


def duygu_motoru_var() -> bool:
    return sozluk_al() is not None or os.environ.get("ERKIS_DUYGU_MOTORU", "sozluk") == "turkishbertweet"


def isle(metin: str, kurum: str) -> dict:
    haric = sentiment.kurum_sozcukleri(kurum)          # Tasarım kararı 8
    d = sentiment.analiz_et(metin, haric=haric)
    s = scct.siniflandir(metin)                        # yoğunlaştırıcılar analizde uygulanır
    return {
        "duygu_etiketi": d.etiket,
        "duygu": {k: v for k, v in d.sozluk().items() if k != "etiket"},
        "scct": s,
        "niyet": behavioral.niyet_tespit(metin),
    }


def icerige_uygula(ic: Icerik, kurum: str) -> None:
    for k, v in isle(ic.metin or ic.baslik or "", kurum).items():
        setattr(ic, k, v)


def yeniden_isle_gerekli(ic: Icerik) -> bool:
    return (ic.duygu or {}).get("motor", "yok") == "yok" and sozluk_al() is not None


def islenmis(ic: Icerik) -> IslenmisIcerik:
    d = ic.duygu or {}
    s = ic.scct or {}
    return IslenmisIcerik(
        kimlik=f"{ic.platform}:{ic.dis_id}", platform=ic.platform, tur=ic.tur, yazar=ic.yazar,
        metin=ic.metin or "", tarih=ic.tarih, begeni=ic.begeni or 0, yorum=ic.yorum or 0,
        paylasim=ic.paylasim or 0, duygu_etiketi=ic.duygu_etiketi,
        olumlu=d.get("olumlu", 0), olumsuz=d.get("olumsuz", 0), ofke=d.get("ofke", 0),
        korku=d.get("korku", 0), igrenme=d.get("igrenme", 0), toplam_sozcuk=d.get("toplam_sozcuk", 0),
        scct_seviye=s.get("baslangic_seviye", 0), scct_kume=s.get("kume"), scct_tip=s.get("tip"),
        niyet=list(ic.niyet or []),
    )
