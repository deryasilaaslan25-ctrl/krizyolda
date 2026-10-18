"""Kaynak kimlik bilgilerinin (API anahtarı, token) şifreli saklanması. Fernet (AES-128-CBC + HMAC-SHA256)."""
from __future__ import annotations

import base64
import hashlib
import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    ham = settings.ENCRYPTION_KEY.strip()
    if ham:
        try:
            return Fernet(ham.encode())
        except ValueError:
            pass                                      # geçerli Fernet anahtarı değilse türetilir
    kaynak = ham or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("krizyolda-kimlik:" + kaynak).encode()).digest()))


def sifrele(deger: dict) -> str:
    return _fernet().encrypt(json.dumps(deger, ensure_ascii=False).encode()).decode()


def coz(metin: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(metin.encode()).decode())
    except (InvalidToken, ValueError) as e:
        raise ValueError("Kimlik bilgisi çözülemedi (ENCRYPTION_KEY/SECRET_KEY değişmiş olabilir)") from e


def maskele(deger: str, son: int = 4) -> str:
    if not deger:
        return ""
    return "•" * max(len(deger) - son, 4) + deger[-son:] if len(deger) > son else "•" * len(deger)
