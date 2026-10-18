"""Testler için ortak ayarlar. Sentetik sözlük NRC DEĞİLDİR; yalnız kural testleri içindir."""
import os
import sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "sentetik_sozluk.txt"
os.environ["DATABASE_URL"] = "sqlite:///./test_krizyolda.db"
os.environ["ENV"] = "development"
os.environ["ERKIS_NRC_YOLU"] = str(FIXTURE)
os.environ["GOOGLE_TRENDS_ENABLED"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if os.path.exists("test_krizyolda.db"):
    os.remove("test_krizyolda.db")

from app.core.rate_limit import limiter  # noqa: E402

limiter.enabled = False

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _tablolar():
    from app.database import Base, engine
    from app.models import orm  # noqa: F401
    Base.metadata.create_all(bind=engine)
