"""Krizyolda — FastAPI uygulaması."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import (routes_alarm, routes_analiz, routes_auth, routes_beyin, routes_bilgi, routes_esik, routes_icerik,
                     routes_itibar, routes_kaynak, routes_kurum, routes_pr, routes_profil, routes_tarama, routes_uzman)
from app.config import settings
from app.core.rate_limit import GuvenlikBasliklariMiddleware, limiter
from app.database import Base, baglanti_dogrula, engine, sema_guncelle

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("krizyolda")


@asynccontextmanager
async def lifespan(app: FastAPI):
    hatalar = settings.uretim_dogrula()
    if hatalar:
        raise RuntimeError("Üretim yapılandırması geçersiz: " + "; ".join(hatalar))
    baglanti_dogrula()
    from app.models import orm  # noqa: F401  (tabloları kaydeder)
    Base.metadata.create_all(bind=engine)
    eklenen = sema_guncelle()
    if eklenen:
        log.info("Şema güncellendi: %s", ", ".join(eklenen))
    gorev = None
    if settings.WORKER_GOMULU:
        from app.worker import dongu
        gorev = asyncio.create_task(dongu())
    yield
    if gorev:
        gorev.cancel()


app = FastAPI(title=settings.APP_NAME, version="6.0.0", lifespan=lifespan,
              description="Kriz erken uyarı ve itibar izleme: iki beyinli gösterge modeli, kuruma özgü eşik, PR danışmanlığı")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(GuvenlikBasliklariMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_listesi, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (routes_auth, routes_kurum, routes_profil, routes_kaynak, routes_tarama, routes_analiz, routes_beyin, routes_uzman, routes_alarm,
          routes_icerik, routes_bilgi, routes_esik, routes_pr, routes_itibar):
    app.include_router(r.router)
app.include_router(routes_alarm.acik_router)
