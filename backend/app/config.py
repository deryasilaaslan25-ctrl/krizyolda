"""Uygulama ayarları (ortam değişkenleri / .env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

_ORNEK_ANAHTARLAR = {"", "gelistirme-anahtari-uretimde-degistirin", "uretimde-uzun-rastgele-bir-anahtar-kullanin"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Krizyolda"
    ENV: str = "development"                       # development | production
    DATABASE_URL: str = "sqlite:///./krizyolda_dev.db"
    SECRET_KEY: str = "gelistirme-anahtari-uretimde-degistirin"
    ENCRYPTION_KEY: str = ""                       # kaynak kimlik bilgilerini şifreler; boşsa SECRET_KEY'den türetilir
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    YONETICI_EPOSTALARI: str = ""                  # virgülle ayrılmış; bu adresler kayıt olunca yönetici rolü alır
    WORKER_GOMULU: bool = False                    # True ise tarama işçisi API süreci içinde çalışır

    # Açık kaynaklar (anahtar gerektirmez)
    ERKIS_EK_RSS: str = ""                         # virgülle ayrılmış RSS adresleri (tüm kurumlar için)
    GOOGLE_TRENDS_ENABLED: bool = True             # pytrends: resmî değil; başarısızlık kaynak durumunda görünür
    REDDIT_ACIK_ARAMA: bool = True                 # kimlik doğrulamasız genel arama uç noktası (en iyi çaba)
    INSTAGRAM_GRAPH_SURUMU: str = "v21.0"

    # Yöntem seçenekleri
    ERKIS_SCCT_MOTORU: str = "tohum"               # tohum | sifir_atis
    ERKIS_DUYGU_MOTORU: str = "sozluk"             # sozluk | turkishbertweet
    ERKIS_DIL_FILTRESI: str = "0"
    ERKIS_Z_YONTEMI: str = "stouffer"              # stouffer | strube
    ERKIS_NRC_YOLU: str = ""

    # Tarama
    TARAMA_ARALIGI_MIN: int = 15                   # sistemin seçebileceği en kısa aralık (dk)
    TARAMA_ARALIGI_MAX: int = 360                  # sistemin seçebileceği en uzun aralık (dk)
    ISCI_BEKLEME_SN: int = 30                      # işçi döngüsünün uyanma aralığı
    EN_FAZLA_ANALIZ_GUN: int = 180                 # 6 ay

    # Bildirim
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True                     # 465 numaralı portta SSL kullanılır
    SLACK_WEBHOOK_URL: str = ""
    PANEL_URL: str = "http://localhost:5173"
    GERI_BILDIRIM_TOKEN_GUN: int = 14
    BILDIRIM_EN_FAZLA_DENEME: int = 6
    BILDIRIM_BEKLEME_SAAT_VARSAYILAN: int = 6      # aynı alarm için seviye-yükselme e-postaları arası en kısa süre

    @property
    def cors_listesi(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def yonetici_listesi(self) -> set[str]:
        return {e.strip().lower() for e in self.YONETICI_EPOSTALARI.split(",") if e.strip()}

    def uretim_dogrula(self) -> list[str]:
        """Üretimde eksik/güvensiz ayarları listeler; boş liste = uygun."""
        if self.ENV != "production":
            return []
        hatalar = []
        if self.SECRET_KEY in _ORNEK_ANAHTARLAR or len(self.SECRET_KEY) < 32:
            hatalar.append("SECRET_KEY en az 32 karakterlik rastgele bir değer olmalı")
        if self.DATABASE_URL.startswith("sqlite"):
            hatalar.append("DATABASE_URL üretimde PostgreSQL olmalı")
        if "localhost" in self.PANEL_URL or "127.0.0.1" in self.PANEL_URL:
            hatalar.append("PANEL_URL gerçek HTTPS adresi olmalı (e-posta bağlantıları buraya gider)")
        if not self.PANEL_URL.startswith("https://"):
            hatalar.append("PANEL_URL https:// ile başlamalı")
        if not (self.SMTP_HOST and (self.SMTP_FROM or self.SMTP_USER)):
            hatalar.append("SMTP_HOST ve SMTP_FROM tanımlı olmalı (kriz e-postaları için)")
        return hatalar


settings = Settings()
