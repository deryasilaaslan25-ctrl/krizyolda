"""
SCCT kriz tipi sınıflandırması (G13) [COOMBS2007, Tablo 1; COOMBS_HOLLADAY2002].

Kod: 0 kriz dışı, 1 mağdur, 2 kaza, 3 önlenebilir.
Yoğunlaştırıcılar: kriz geçmişi (benzer tipte önceki kriz) veya olumsuz
önceki ilişkisel itibar → mağdur→kaza, kaza→önlenebilir [COOMBS2007].

Tohum gövdeler (Rapor Bölüm 2.5) Coombs (2007) tanımlarından türetilmiş
Türkçe operasyonelleştirmedir (Tasarım kararı 1). Gövde, metinde bir
sözcük başında başlamalıdır; son sözcüğü önek olarak eşleşir.
Birden çok tip eşleşirse en yüksek sorumluluk seçilir (Tasarım kararı 3).

ERKIS_SCCT_MOTORU=sifir_atis: Coombs'un İngilizce tanımları hipotez olarak
çok dilli NLI modeliyle sınıflandırılır [LAURER2024]; kabul sınırı Tasarım
kararı 19.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Iterable, Optional

from app.nlp.normalize import duz_metin, sozcukler

log = logging.getLogger(__name__)

KUME_SEVIYE = {"magdur": 1, "kaza": 2, "onlenebilir": 3}
SEVIYE_KUME = {0: None, 1: "magdur", 2: "kaza", 3: "onlenebilir"}
KUME_TEHDIT = {"magdur": "Hafif", "kaza": "Orta", "onlenebilir": "Şiddetli"}
KUME_ADLARI = {"magdur": "Mağdur", "kaza": "Kaza", "onlenebilir": "Önlenebilir"}

# Rapor Bölüm 2.5 — birebir
KRIZ_TIPLERI: dict[str, dict] = {
    "dogal_afet": {"kume": "magdur", "ad": "Doğal afet",
                   "tanim_en": "Acts of nature damage an organization such as an earthquake.",
                   "tanim_tr": "doğa olayları (ör. deprem) kuruma zarar veriyor",
                   "tohumlar": ["deprem", "sel felaket", "doğal afet", "heyelan", "kasırga"]},
    "soylenti": {"kume": "magdur", "ad": "Söylenti",
                 "tanim_en": "False and damaging information about an organization is being circulated.",
                 "tanim_tr": "kurum hakkında yanlış ve zarar verici bilgi dolaşıyor",
                 "tohumlar": ["asılsız", "yalan haber", "sahte haber", "dezenformasyon", "söylenti", "gerçeği yansıtm", "yalanla"]},
    "isyeri_siddeti": {"kume": "magdur", "ad": "İşyeri şiddeti",
                       "tanim_en": "Current or former employee attacks current employees onsite.",
                       "tanim_tr": "mevcut ya da eski bir çalışan iş yerinde çalışanlara saldırıyor",
                       "tohumlar": ["iş yerinde saldır", "işyerinde saldır", "çalışanına saldır", "silahlı saldır"]},
    "kurcalama": {"kume": "magdur", "ad": "Ürün kurcalama / kötü niyet",
                  "tanim_en": "External agent causes damage to an organization.",
                  "tanim_tr": "dışarıdan bir kişi ya da grup kuruma kasıtlı zarar veriyor",
                  "tohumlar": ["sabotaj", "siber saldır", "hacklen", "fidye yazılım", "kurcalan"]},
    "meydan_okuma": {"kume": "kaza", "ad": "Meydan okuma",
                     "tanim_en": "Stakeholders claim an organization is operating in an inappropriate manner.",
                     "tanim_tr": "paydaşlar kurumun uygunsuz biçimde faaliyet gösterdiğini iddia ediyor",
                     "tohumlar": ["protesto", "imza kampanya", "tepki yağ", "etik değil", "tepki göster", "kınıyor"]},
    "teknik_hata_kaza": {"kume": "kaza", "ad": "Teknik hata kazası",
                         "tanim_en": "A technology or equipment failure causes an industrial accident.",
                         "tanim_tr": "bir teknoloji ya da ekipman arızası endüstriyel bir kazaya yol açıyor",
                         "tohumlar": ["teknik arıza", "ekipman arıza", "sistem çök", "erişim kesinti", "arıza nedeniyle"]},
    "teknik_hata_urun": {"kume": "kaza", "ad": "Teknik hata ürün zararı",
                         "tanim_en": "A technology or equipment failure causes a product to be recalled.",
                         "tanim_tr": "bir teknoloji ya da ekipman arızası nedeniyle ürün geri çağrılıyor",
                         "tohumlar": ["geri çağır", "geri çağrıl", "toplatıl", "toplatma", "üretim hata", "yazılım hata"]},
    "insan_hatasi_kaza": {"kume": "onlenebilir", "ad": "İnsan hatası kazası",
                          "tanim_en": "Human error causes an industrial accident.",
                          "tanim_tr": "insan hatası endüstriyel bir kazaya yol açıyor",
                          "tohumlar": ["insan hata", "ihmal", "iş kaza", "dikkatsizlik"]},
    "insan_hatasi_urun": {"kume": "onlenebilir", "ad": "İnsan hatası ürün zararı",
                          "tanim_en": "Human error causes a product to be recalled.",
                          "tanim_tr": "insan hatası nedeniyle ürün geri çağrılıyor ya da zarar veriyor",
                          "tohumlar": ["zehirlen", "bozuk ürün", "tarihi geçmiş", "hijyensiz", "hijyen skandal", "hijyen rezalet", "böcek çık", "yabancı madde", "küflü", "küflen"]},
    "suistimal_yaralanmasiz": {"kume": "onlenebilir", "ad": "Kurumsal suistimal (yaralanmasız)",
                               "tanim_en": "Stakeholders are deceived without injury.",
                               "tanim_tr": "paydaşlar yaralanma olmaksızın aldatılıyor",
                               "tohumlar": ["dolandırıcı", "dolandırıl", "aldatıcı", "kandırıl", "tüketiciyi yanılt", "gizli ücret", "fahiş fiyat", "mağdur edil"]},
    "yonetim_suistimali": {"kume": "onlenebilir", "ad": "Yönetim suistimali",
                           "tanim_en": "Laws or regulations are violated by management.",
                           "tanim_tr": "yönetim yasaları ya da düzenlemeleri ihlal ediyor",
                           "tohumlar": ["yolsuzluk", "rüşvet", "vergi kaçır", "usulsüzlük", "kara para", "soruşturma başlat", "gözaltına alın", "ayrımcılık"]},
    "suistimal_yaralanmali": {"kume": "onlenebilir", "ad": "Kurumsal suistimal (yaralanmalı)",
                              "tanim_en": "Stakeholders are placed at risk by management and injuries occur.",
                              "tanim_tr": "yönetim paydaşları bile bile riske atıyor ve yaralanmalar oluyor",
                              "tohumlar": ["bile bile", "göz göre göre", "önlem alınma", "uyarılara rağmen", "denetimsiz"]},
}


def _tohum_eslesir(duz: str, tohum: str) -> bool:
    kalip = " " + " ".join(sozcukler(tohum))
    return kalip in duz


def tohum_tipleri(metin: str) -> list[str]:
    duz = duz_metin(metin)
    return [tip for tip, t in KRIZ_TIPLERI.items() if any(_tohum_eslesir(duz, s) for s in t["tohumlar"])]


@lru_cache(maxsize=1)
def _nli():
    from transformers import pipeline
    return pipeline("zero-shot-classification",
                    model="MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")


def sifir_atis_tipleri(metin: str) -> Optional[list[str]]:
    try:
        clf = _nli()
        tipler = list(KRIZ_TIPLERI)
        hipotezler = [KRIZ_TIPLERI[t]["tanim_en"] for t in tipler]
        r = clf(metin[:1500], candidate_labels=hipotezler, hypothesis_template="{}", multi_label=True)
        skor = dict(zip(r["labels"], r["scores"]))
        return [t for t, h in zip(tipler, hipotezler) if skor.get(h, 0.0) > 0.5]
    except Exception as hata:
        log.warning("Sıfır-atış SCCT kullanılamadı, tohum ifadelerine dönülüyor: %s", hata)
        return None


def siniflandir(metin: str, kriz_gecmisi: Iterable[str] = (), onceki_itibar_olumsuz: bool = False) -> dict:
    """Tek içerik için SCCT seviyesi (G13 girdisi)."""
    tipler: Optional[list[str]] = None
    motor = "tohum"
    if os.environ.get("ERKIS_SCCT_MOTORU", "tohum") == "sifir_atis":
        tipler = sifir_atis_tipleri(metin)
        if tipler is not None:
            motor = "sifir_atis"
    if tipler is None:
        tipler = tohum_tipleri(metin)
    if not tipler:
        return {"seviye": 0, "baslangic_seviye": 0, "tip": None, "kume": None, "tipler": [],
                "yogunlastirici": False, "motor": motor}
    tip = max(tipler, key=lambda t: KUME_SEVIYE[KRIZ_TIPLERI[t]["kume"]])
    baslangic = KUME_SEVIYE[KRIZ_TIPLERI[tip]["kume"]]
    gecmis = set(kriz_gecmisi)
    yogun = onceki_itibar_olumsuz or tip in gecmis
    seviye = min(baslangic + 1, 3) if yogun and baslangic < 3 else baslangic
    return {"seviye": seviye, "baslangic_seviye": baslangic, "tip": tip, "kume": SEVIYE_KUME[seviye],
            "tipler": tipler, "yogunlastirici": bool(yogun and baslangic < 3), "motor": motor}
