"""
Kriz anı PR stratejisi — Coombs (2007) SCCT strateji kılavuzunun (8 kural) uygulanması [COOMBS2007].

Girdi, sistemin veriden ürettiği SCCT sonucudur: baskın (yoğunlaştırıcılı) sorumluluk kümesi, baskın kriz
tipi, kriz geçmişi ve önceki itibar. Çıktıdaki strateji adları, tanımlar ve kural numaraları Coombs (2007)
tablosundandır; 'uygulama_notu' alanları operasyonelleştirmedir (Tasarım kararı 50).
"""
from __future__ import annotations

from typing import Iterable, Optional

from app.nlp.scct import KRIZ_TIPLERI, KUME_ADLARI, KUME_SEVIYE, KUME_TEHDIT
from app.pr import katalog as K

_KURAL = {r["no"]: r["metin"] for r in K.KURALLAR}


def _strateji(kod: str) -> dict:
    s = K.STRATEJILER[kod]
    return {"kod": kod, "ad": s["ad"], "durus": s["durus"], "tanim_tr": s["tanim_tr"], "tanim_en": s["tanim_en"],
            "benoit_karsiligi": s["benoit"]}


def kural_numaralari(baslangic_kume: Optional[str], efektif_kume: Optional[str], yogunlastirici: bool,
                     tip: Optional[str]) -> list[int]:
    """Uygulanan SCCT kılavuz kuralları."""
    kurallar: list[int] = []
    if baslangic_kume == "magdur":
        kurallar.append(3 if yogunlastirici else 1)
    elif baslangic_kume == "kaza":
        kurallar.append(5 if yogunlastirici else 4)
    elif baslangic_kume == "onlenebilir":
        kurallar.append(6)
    elif efektif_kume == "magdur":
        kurallar.append(1)
    elif efektif_kume == "kaza":
        kurallar += [3, 4]                     # kaza etkin küme: mağdur+yoğunlaştırıcı (3) ya da kaza (4)
    elif efektif_kume == "onlenebilir":
        kurallar += [5, 6]
    if tip in K.VICTIMAGE_TIPLERI:
        kurallar.append(2)
    if tip in K.INKAR_TIPLERI:
        kurallar += [7, 8]
    return kurallar


def kriz_stratejisi(*, efektif_kume: Optional[str], tip: Optional[str] = None, kriz_gecmisi: Iterable[str] = (),
                    onceki_itibar_olumsuz: bool = False, g11_yuksek: bool = False, alarm_acik: bool = True) -> dict:
    """Kriz için önerilen yanıt duruşu ve stratejiler."""
    kriz_gecmisi = list(kriz_gecmisi)
    temel = [dict(t) for t in K.TEMEL_YANIT]
    if efektif_kume not in K.KUME_DURUS:
        return {
            "durum": "tip_belirlenemedi", "kume": None, "tip": tip, "durus": K.DURUSLAR["temel"]["ad"],
            "temel_yanit": temel, "birincil": [], "destekleyici": [], "kosullu": [], "kurallar": [],
            "aciklama": ("İçeriklerden bir SCCT kriz tipi çıkarılamadı. Tip doğrulanana kadar Coombs (2007) temel yanıtı "
                         "(yönlendirici + uyarlayıcı bilgi) hazır tutulur; sorumluluk atfını belirleyen kriz tipi kurum içinde "
                         "doğrulanmalıdır."),
            "kaynaklar": ["COOMBS2007"],
        }
    baslangic = KRIZ_TIPLERI[tip]["kume"] if tip in KRIZ_TIPLERI else None
    yogun = bool(tip in kriz_gecmisi or onceki_itibar_olumsuz)
    durus = K.KUME_DURUS[efektif_kume]
    birincil: list[dict] = []
    if durus == "azaltma":
        birincil = [_strateji("mazeret"), _strateji("haklilastirma")]
    elif durus == "yeniden_insa":
        birincil = [_strateji("tazminat"), _strateji("ozur")]
    destek = [_strateji("hatirlatma"), _strateji("pohpohlama")]
    if tip in K.VICTIMAGE_TIPLERI:
        destek.append(_strateji("magduriyet"))
    kosullu = []
    if tip in K.INKAR_TIPLERI:
        kosullu.append({
            "kural": 7, "stratejiler": [_strateji("inkar"), _strateji("suclayana_karsi_cikma"), _strateji("sucu_baskasina_atma")],
            "kosul": "Yalnızca iddianın asılsız olduğu kurum içinde doğrulanırsa (mümkün olduğunda). "
                     "Doğrulanamıyorsa yukarıdaki küme duruşu uygulanır. İnkâr seçilirse azaltma/yeniden inşa ile karıştırılmaz (kural 8).",
        })
    kurallar_no = kural_numaralari(baslangic, efektif_kume, yogun, tip)
    kacin = []
    if durus in ("azaltma", "yeniden_insa"):
        kacin.append("İnkâr stratejilerini azaltma/yeniden inşa ile karıştırmayın (kural 8).")
    if durus == "yeniden_insa":
        kacin.append("Güçlü sorumluluk atfı olan krizde yalnız azaltma stratejileriyle yetinmeyin (kural 5–6).")
    if durus == "azaltma":
        kacin.append("Bu kümede tek başına inkâr önerilmez; inkâr yalnız söylenti/meydan okuma tiplerinde koşulludur (kural 7).")
    adimlar = ["1) Yönlendirici bilgi: olgu, etkilenenler, alınacak önlem.", "2) Uyarlayıcı bilgi: endişe ifadesi ve düzeltici eylem."]
    if birincil:
        adimlar.append(f"3) {K.DURUSLAR[durus]['ad']}: " + " / ".join(b["ad"] for b in birincil) + ".")
    adimlar.append(f"{len(adimlar) + 1}) Destekleme stratejileri yalnızca tamamlayıcıdır; birincil yanıtın yerine geçmez.")
    sonuc = {
        "durum": "tamam", "kume": efektif_kume, "kume_adi": KUME_ADLARI[efektif_kume], "tehdit": KUME_TEHDIT[efektif_kume],
        "tip": tip, "tip_adi": KRIZ_TIPLERI[tip]["ad"] if tip in KRIZ_TIPLERI else None,
        "baslangic_kume": baslangic, "yogunlastirici": yogun,
        "yogunlastirici_ayrinti": {"kriz_gecmisi_eslesti": bool(tip in kriz_gecmisi), "onceki_itibar_olumsuz": bool(onceki_itibar_olumsuz)},
        "durus": K.DURUSLAR[durus]["ad"], "durus_kodu": durus,
        "temel_yanit": temel, "birincil": birincil, "destekleyici": destek, "kosullu": kosullu,
        "kurallar": [{"no": n, "metin": _KURAL[n]} for n in dict.fromkeys(kurallar_no)],
        "kacinilacaklar": kacin, "adimlar": adimlar,
        "iskelet": K.ISKELET[durus],
        "zamanlama": K.ZAMANLAMA if alarm_acik else None,
        "kanal": K.KANAL if g11_yuksek else None,
        "kaynaklar": ["COOMBS2007", "COOMBS_HOLLADAY2002", "COOMBS2004", "COOMBS_HOLLADAY2001", "BENOIT1997"],
    }
    sonuc["aciklama"] = (f"{KUME_ADLARI[efektif_kume]} kümesi (sorumluluk atfı: {KUME_TEHDIT[efektif_kume].lower()} tehdit) → "
                         f"{K.DURUSLAR[durus]['ad'].lower()}. Uygulanan Coombs (2007) kuralları: "
                         f"{', '.join(str(n) for n in dict.fromkeys(kurallar_no))}.")
    return sonuc
