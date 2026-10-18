"""
Veritabanı katmanı. Üretimde PostgreSQL zorunludur; bağlantı kurulamazsa uygulama açılmaz.
Yerel geliştirmede DATABASE_URL açıkça bir SQLite dosyasına verilebilir.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import CreateColumn

from app.config import settings

Base = declarative_base()


def _motor():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20,
                         connect_args={"connect_timeout": 5} if url.startswith("postgresql") else {})


engine = _motor()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def baglanti_dogrula() -> None:
    """Açılışta çağrılır; veritabanına ulaşılamıyorsa istisna fırlatır (sessiz yedek veritabanı yoktur)."""
    with engine.connect() as bag:
        bag.execute(text("SELECT 1"))


def sema_guncelle() -> list[str]:
    """create_all mevcut tablolara sütun eklemez; yalnız eksik sütunları ADD COLUMN ile ekler.
    Sütun silme/yeniden adlandırma gerektiren değişiklikler elle migrasyon ister."""
    eklenen: list[str] = []
    insp = inspect(engine)
    for tablo in Base.metadata.sorted_tables:
        if not insp.has_table(tablo.name):
            continue
        var = {c["name"] for c in insp.get_columns(tablo.name)}
        for kolon in tablo.columns:
            if kolon.name in var or kolon.primary_key:
                continue
            ddl = str(CreateColumn(kolon).compile(dialect=engine.dialect))
            with engine.begin() as bag:
                bag.execute(text(f'ALTER TABLE "{tablo.name}" ADD COLUMN {ddl}'))
            eklenen.append(f"{tablo.name}.{kolon.name}")
    return eklenen
