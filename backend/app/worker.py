"""Arka plan işçisi: tarama işleri, zamanlanmış taramalar, bildirim kuyruğu ve haftalık brif.

Ayrı süreç olarak (`python -m app.worker`) ya da WORKER_GOMULU=true ile API sürecinde çalışır."""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.database import Base, SessionLocal, baglanti_dogrula, engine
from app.models import orm  # noqa: F401
from app.services import bildirim, isler

log = logging.getLogger("krizyolda.worker")


async def bir_tur() -> None:
    db = SessionLocal()
    try:
        isler.takili_isleri_kapat(db)
        isler.zamanlanmis_isleri_olustur(db)
        isler.haftalik_brifleri_kuyruga(db)
        while True:                                    # kuyruktaki tüm işleri sırayla bitir
            is_ = isler.siradaki_is_al(db)
            if is_ is None:
                break
            await isler.isi_calistir(db, is_)
            ozet = bildirim.kuyrugu_isle(db)            # kriz e-postası tarama biter bitmez gitsin
            if ozet["gonderilen"] or ozet["tekrar"] or ozet["kalici_hata"]:
                log.info("Bildirim kuyruğu: %s", ozet)
        bildirim.kuyrugu_isle(db)
    except Exception:
        log.exception("İşçi turu başarısız")
        db.rollback()
    finally:
        db.close()


async def dongu() -> None:
    while True:
        await bir_tur()
        await asyncio.sleep(settings.ISCI_BEKLEME_SN)


def baslat_semayi() -> None:
    from app.database import sema_guncelle
    baglanti_dogrula()
    Base.metadata.create_all(bind=engine)
    sema_guncelle()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    baslat_semayi()
    asyncio.run(dongu())
