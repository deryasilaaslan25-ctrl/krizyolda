"""
NRC Word-Emotion Association Lexicon (EmoLex) Türkçe dosyasını indirir
[MOHAMMAD_TURNEY2013; NRC_EMOLEX].

LİSANS: Sözlük araştırma ve eğitim amaçlı ücretsizdir; ticari kullanım için
NRC Kanada'dan lisans gerekir. Bu nedenle ERKİS paketine gömülmez.
Türkçe sürüm İngilizce sözlüğün makine çevirisidir (Rapor Bölüm 8).

Kullanım:  python scripts/indir_nrc.py
Hedef:     backend/data/nrc/Turkish-NRC-EmoLex.txt
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import httpx

URL = "https://saifmohammad.com/WebDocs/Lexicons/NRC-Emotion-Lexicon.zip"
ICERIK = "NRC-Emotion-Lexicon/OneFilePerLanguage/Turkish-NRC-EmoLex.txt"
HEDEF = Path(__file__).resolve().parents[1] / "data" / "nrc" / "Turkish-NRC-EmoLex.txt"
# Sunucu tarayıcı dışı User-Agent'larla 406 döndürebildiği için
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def main() -> int:
    print("NRC EmoLex indiriliyor:", URL)
    r = httpx.get(URL, headers={"User-Agent": UA}, follow_redirects=True, timeout=120)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        ad = next((n for n in z.namelist() if n.endswith("OneFilePerLanguage/Turkish-NRC-EmoLex.txt")), None)
        if ad is None:
            print("Arşivde Türkçe dosya bulunamadı:", ICERIK, file=sys.stderr)
            return 1
        HEDEF.parent.mkdir(parents=True, exist_ok=True)
        HEDEF.write_bytes(z.read(ad))
    satir = sum(1 for _ in HEDEF.open(encoding="utf-8"))
    print(f"Yazıldı: {HEDEF} ({satir} satır). Lisans koşullarını okuyun: https://nrc.canada.ca/en/research-development/products-services/technical-advisory-services/sentiment-emotion-lexicons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
