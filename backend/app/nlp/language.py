"""İsteğe bağlı dil filtresi: langdetect [SHUYO2010]. ERKIS_DIL_FILTRESI=1 ise
yalnız 'tr' tespit edilen içerik analize girer."""
from __future__ import annotations

import os


def filtre_acik() -> bool:
    return os.environ.get("ERKIS_DIL_FILTRESI", "0") == "1"


def turkce_mi(metin: str) -> bool:
    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 0
        return detect(metin) == "tr"
    except Exception:
        return True   # tespit edilemezse içerik dışlanmaz
