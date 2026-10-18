"""
Sözlük tabanlı duygu ve yüksek uyarılmışlık ölçümü.

  * Olumsuz içerik kuralı: olumsuz sözcük sayısı > olumlu sözcük sayısı;
    olumsuzlama tersine çevirir [HERHAUSEN2019]. Nötr: olumlu = olumsuz
    [DEEPHOUSE2000].
  * Olumsuzlayıcılar "değil", "yok" sözcükten sonra gelir [GOKSEL_KERSLAKE2005];
    kapsam: hemen önceki duygu sözcüğü (Tasarım kararı 12).
  * Yüksek uyarılmışlık: öfke / korku / iğrenme sözcükleri ÷ toplam sözcük
    (NRC 'anger', 'fear', 'disgust') [HERHAUSEN2019; MOHAMMAD_TURNEY2013].
  * Kurum adındaki sözcükler hesaptan çıkarılır (Tasarım kararı 8).
  * İsteğe bağlı: ERKIS_DUYGU_MOTORU=turkishbertweet → G6 etiketi
    TurkishBERTweet + LoRA duygu adaptöründen [NAJAFI_VAROL2024]; duygu
    kategorileri (G8–G10) yine NRC'den gelir.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, Optional

from app.literatur import OLUMSUZLAYICILAR
from app.nlp.lexicon import Sozluk, sozcuk_eslesir, sozluk_al
from app.nlp.normalize import sozcukler

log = logging.getLogger(__name__)


@dataclass
class DuyguSonucu:
    olumlu: int = 0
    olumsuz: int = 0
    ofke: int = 0
    korku: int = 0
    igrenme: int = 0
    toplam_sozcuk: int = 0
    etiket: Optional[str] = None      # "olumsuz" | "olumlu" | "notr" | None (sözlük yok)
    motor: str = "yok"
    kanitlar: list[dict] = field(default_factory=list)

    def sozluk(self) -> dict:
        return self.__dict__.copy()


def olumsuzlayici_mi(sozcuk: str) -> bool:
    return any(sozcuk_eslesir(sozcuk, n) for n in OLUMSUZLAYICILAR)


def kurum_sozcukleri(kurum_adi: str | None, ek_terimler: Iterable[str] = ()) -> set[str]:
    s: set[str] = set()
    for metin in [kurum_adi or "", *ek_terimler]:
        s.update(sozcukler(metin))
    return s


def sozluk_analizi(metin: str, sozluk: Sozluk, haric: set[str] | None = None) -> DuyguSonucu:
    haric = haric or set()
    tokenler = [t for t in sozcukler(metin) if t not in haric]
    sonuc = DuyguSonucu(toplam_sozcuk=len(tokenler), motor="nrc_sozluk")
    i = 0
    while i < len(tokenler):
        e = sozluk.eslestir(tokenler, i)
        if e is None:
            i += 1
            continue
        son = i + e.uzunluk
        olumlu = "positive" in e.etiketler
        olumsuz = "negative" in e.etiketler
        cevrildi = False
        if (olumlu or olumsuz) and son < len(tokenler) and olumsuzlayici_mi(tokenler[son]):
            olumlu, olumsuz = olumsuz, olumlu
            cevrildi = True
        sonuc.olumlu += int(olumlu)
        sonuc.olumsuz += int(olumsuz)
        sonuc.ofke += int("anger" in e.etiketler)
        sonuc.korku += int("fear" in e.etiketler)
        sonuc.igrenme += int("disgust" in e.etiketler)
        if e.etiketler:
            sonuc.kanitlar.append({"sozcuk": " ".join(tokenler[i:son]), "girdi": e.girdi,
                                   "etiketler": sorted(e.etiketler), "olumsuzlandi": cevrildi})
        i = son + (1 if cevrildi else 0)
    if sonuc.olumsuz > sonuc.olumlu:
        sonuc.etiket = "olumsuz"
    elif sonuc.olumlu > sonuc.olumsuz:
        sonuc.etiket = "olumlu"
    else:
        sonuc.etiket = "notr"
    return sonuc


@lru_cache(maxsize=1)
def _turkishbertweet():
    """[NAJAFI_VAROL2024] model kartındaki kullanım: VRLLab/TurkishBERTweet-Lora-SA."""
    import torch  # noqa: F401
    from peft import PeftConfig, PeftModel
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    adaptor = "VRLLab/TurkishBERTweet-Lora-SA"
    cfg = PeftConfig.from_pretrained(adaptor)
    tok = AutoTokenizer.from_pretrained(cfg.base_model_name_or_path, padding_side="right")
    if getattr(tok, "pad_token_id") is None:
        tok.pad_token_id = tok.eos_token_id
    id2label = {0: "negative", 2: "positive", 1: "neutral"}
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.base_model_name_or_path, return_dict=True, num_labels=len(id2label), id2label=id2label)
    model = PeftModel.from_pretrained(model, adaptor)
    model.eval()
    return tok, model, id2label


def _bertweet_etiketi(metin: str) -> Optional[str]:
    try:
        import torch
        tok, model, id2label = _turkishbertweet()
        with torch.no_grad():
            ids = tok.encode_plus(metin[:2000], return_tensors="pt", truncation=True)
            etiket = id2label[int(model(**ids).logits.argmax(-1).item())]
        return {"negative": "olumsuz", "positive": "olumlu", "neutral": "notr"}[etiket]
    except Exception as hata:  # model/ağ yoksa sözlüğe dönülür
        log.warning("TurkishBERTweet kullanılamadı, sözlük kuralına dönülüyor: %s", hata)
        return None


def analiz_et(metin: str, haric: set[str] | None = None, sozluk: Sozluk | None = None) -> DuyguSonucu:
    sozluk = sozluk if sozluk is not None else sozluk_al()
    if sozluk is None:
        sonuc = DuyguSonucu(toplam_sozcuk=len([t for t in sozcukler(metin) if t not in (haric or set())]))
    else:
        sonuc = sozluk_analizi(metin, sozluk, haric)
    if os.environ.get("ERKIS_DUYGU_MOTORU", "sozluk") == "turkishbertweet":
        etiket = _bertweet_etiketi(metin)
        if etiket is not None:
            sonuc.etiket = etiket
            sonuc.motor = "turkishbertweet"
    return sonuc
