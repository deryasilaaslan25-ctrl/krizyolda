"""ORM modelleri."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database import Base


def _simdi() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Kullanici(Base):
    """Her kullanıcı bir kurumu temsil eder; eşikler bu kuruma özgü akıştan çıkar."""
    __tablename__ = "kullanicilar"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    kurum = Column(String(255), nullable=False)
    sektor = Column(String(120), default="")
    rol = Column(String(30), default="kurum")
    izleme_terimleri = Column(JSON, default=list)       # kurum adı dışındaki arama terimleri
    kriz_gecmisi = Column(JSON, default=list)           # SCCT tip anahtarları [COOMBS2007]
    onceki_itibar = Column(String(20), nullable=True)   # None | olumlu | notr | olumsuz
    bildirim_email = Column(Boolean, default=True)      # kayıt e-postasına kriz uyarısı (Tasarım kararı 38)
    bildirim_ek_epostalar = Column(JSON, default=list)  # kayıt e-postasına ek alıcılar
    bildirim_slack = Column(Boolean, default=False)
    bildirim_min_seviye = Column(Integer, default=2)    # 2 = YÜKSEK RİSK (Tasarım kararı 38)
    bildirim_haftalik = Column(Boolean, default=True)   # haftalık PR brifi (Tasarım kararı 52)
    son_haftalik_brif = Column(DateTime, nullable=True)
    sonraki_tarama = Column(DateTime, nullable=True)    # uyarlamalı tarama aralığı (Tasarım kararı 42)
    olusturma = Column(DateTime, default=_simdi)
    eposta_dogrulandi = Column(Boolean, default=False)
    # Marka profili
    web_sitesi = Column(String(255), default="")
    resmi_hesaplar = Column(JSON, default=list)         # [{"platform": "x", "hesap": "@marka"}]
    haric_terimler = Column(JSON, default=list)         # yanlış eşleşmeyi azaltan terimler
    ek_rss = Column(JSON, default=list)                 # kurumun izlenmesini istediği RSS adresleri
    # Veri toplama kapsamı
    acik_kaynak = Column(Boolean, default=True)         # anahtarsız, herkese açık kaynaklar
    aralik_turu = Column(String(10), default="30")      # 7 | 30 | 90 | 180 | ozel
    ozel_baslangic = Column(DateTime, nullable=True)
    ozel_bitis = Column(DateTime, nullable=True)
    # Tekrarlama planı
    tekrar_plani = Column(String(12), default="periyodik")   # periyodik | tek_seferlik
    tarama_min_dk = Column(Integer, default=15)         # sistemin seçebileceği en kısa aralık
    tarama_max_dk = Column(Integer, default=360)        # sistemin seçebileceği en uzun aralık
    tarama_aralik_dk = Column(Integer, nullable=True)   # sistemin son seçtiği aralık
    tek_seferlik_yapildi = Column(Boolean, default=False)
    # Bildirim ayarları
    bildirim_bekleme_saat = Column(Integer, default=6)  # seviye yükselme e-postaları arası en kısa süre
    rapor_gunu = Column(Integer, default=0)             # 0 = Pazartesi
    rapor_saati = Column(Integer, default=9)            # Türkiye saati

    icerikler = relationship("Icerik", back_populates="kurum_ref", cascade="all, delete-orphan")


class Icerik(Base):
    __tablename__ = "icerikler"
    __table_args__ = (UniqueConstraint("kurum_id", "platform", "dis_id", name="uq_icerik"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True)
    platform = Column(String(40), nullable=False)       # google_news | rss | reddit | youtube | x
    tur = Column(String(10), nullable=False)            # sosyal | haber (Tasarım kararı 11)
    dis_id = Column(String(255), nullable=False)
    yazar = Column(String(255), nullable=True)
    baslik = Column(Text, default="")
    metin = Column(Text, default="")
    url = Column(Text, default="")
    tarih = Column(DateTime, index=True, nullable=False)   # UTC (tz'siz saklanır)
    begeni = Column(Integer, default=0)
    yorum = Column(Integer, default=0)
    paylasim = Column(Integer, default=0)
    toplama_zamani = Column(DateTime, default=_simdi)
    erisim = Column(String(10), default="acik")         # acik (anahtarsız) | bagli (kurumun API bağlantısı)
    icerik_turu = Column(String(12), default="bahsetme")  # bahsetme | yorum | gonderi | haber
    # NLP çıktıları
    duygu_etiketi = Column(String(10), nullable=True)
    duygu = Column(JSON, default=dict)
    scct = Column(JSON, default=dict)
    niyet = Column(JSON, default=list)

    kurum_ref = relationship("Kullanici", back_populates="icerikler")


class TrendDegeri(Base):
    __tablename__ = "trend_degerleri"
    __table_args__ = (UniqueConstraint("kurum_id", "zaman", name="uq_trend"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True)
    zaman = Column(DateTime, nullable=False)
    deger = Column(Float, nullable=False)
    kaynak = Column(String(20), default="pytrends")     # pytrends | csv


class Analiz(Base):
    __tablename__ = "analizler"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True)
    zaman = Column(DateTime, default=_simdi, index=True)
    seviye = Column(Integer, default=0)
    z = Column(Float, nullable=True)
    sonuc = Column(JSON, nullable=False)


class Alarm(Base):
    """Alarm dönemi (Tasarım kararı 18)."""
    __tablename__ = "alarmlar"
    __table_args__ = (UniqueConstraint("kurum_id", "baslangic", name="uq_alarm"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True)
    baslangic = Column(DateTime, nullable=False)
    bitis = Column(DateTime, nullable=False)
    acik = Column(Boolean, default=True)
    max_seviye = Column(Integer, nullable=False)
    kurallar = Column(JSON, default=list)
    baskin_kume = Column(String(20), nullable=True)
    tehdit = Column(String(20), nullable=True)
    max_z = Column(Float, nullable=True)
    geri_bildirim = Column(String(20), nullable=True)   # gercek_kriz | yanlis_alarm (arayüzde "önemsiz")
    geri_bildirim_zamani = Column(DateTime, nullable=True)
    geri_bildirim_seviye = Column(Integer, nullable=True)   # işaretlendiği andaki en yüksek seviye
    not_metni = Column(Text, default="")
    bildirildi = Column(Boolean, default=False)
    bildirim_seviye = Column(Integer, default=0)        # bildirilen en yüksek seviye
    bildirim_durumu = Column(String(30), default="yok") # yok|gonderildi|gecmis|bastirildi|smtp_yok|kapali
    bildirim_son_zaman = Column(DateTime, nullable=True)
    ilk_yanit_zamani = Column(DateTime, nullable=True)  # kurumun ilk kamuya yanıt zamanı (elle girilir)
    cozum_zamani = Column(DateTime, nullable=True)
    bastirma_nedeni = Column(Text, default="")
    benzer_alarm_id = Column(Integer, nullable=True)
    max_risk = Column(Float, nullable=True)             # dönemdeki en yüksek R (etiketli düzeltme için)
    saat_sayisi = Column(Integer, default=0)
    parmak_izi = Column(JSON, default=dict)             # aynı krizin tanınması (Tasarım kararı 39)


class DenetimKaydi(Base):
    __tablename__ = "denetim_kayitlari"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, nullable=True)
    islem = Column(String(80))
    ayrinti = Column(JSON, default=dict)
    zaman = Column(DateTime, default=_simdi)


class RiskOlcumu(Base):
    """Saatlik pencere başına bir kayıt (Metodoloji Bölüm 12: her karar sonradan denetlenebilir)."""
    __tablename__ = "risk_olcumleri"
    __table_args__ = (UniqueConstraint("kurum_id", "saat", name="uq_risk_olcum"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    saat = Column(DateTime, nullable=False, index=True)      # pencere başlangıcı (UTC, tz'siz)
    risk = Column(Float, nullable=False)                     # R (0–100)
    z = Column(Float, nullable=True)
    kre = Column(Float, nullable=True)
    risk_uzman = Column(Float, nullable=True)                # 2. beyin (uzman ağırlıklı) risk puanı
    z_uzman = Column(Float, nullable=True)
    hacim_z = Column(Float, nullable=True)
    ham_seviye = Column(Integer, default=0)
    nihai_seviye = Column(Integer, default=0)
    esikler = Column(JSON, default=list)                     # [orta, yüksek, kritik]
    esik_kaynagi = Column(String(30), default="uzman")
    yontemler = Column(JSON, default=dict)
    guvenilirlik_z = Column(Float, default=0.0)
    n_blok = Column(Integer, default=0)
    olcek_s = Column(Float, default=0.0)
    p_asim = Column(Float, nullable=True)
    donus_saat = Column(Float, nullable=True)
    korkuluk = Column(JSON, default=list)
    histerezis = Column(JSON, default=dict)
    ayrinti = Column(JSON, default=dict)                     # GPD parametreleri, önsel, etiket düzeltmesi
    aciklama = Column(Text, default="")
    alarm_id = Column(Integer, ForeignKey("alarmlar.id", ondelete="SET NULL"), nullable=True, index=True)
    gecmis = Column(Boolean, default=False)                  # yeniden oynatılan ölçüm (Tasarım kararı 36)
    olusturma = Column(DateTime, default=_simdi)


# ---------------------------------------------------------------------------
# L-PTİ (Literatür-Temelli Paydaş İtibar Endeksi) — Rapor Bölüm 10.1 tabloları
# ---------------------------------------------------------------------------
class ItibarArac(Base):
    __tablename__ = "reputation_instruments"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    version = Column(String(40), nullable=False)
    language = Column(String(10), default="tr")
    license_status = Column(String(40), default="dogrulanmadi")   # dogrulanmadi | lisansli | serbest
    source_citations = Column(JSON, default=list)
    scoring_spec_hash = Column(String(64), default="")
    aciklama = Column(Text, default="")
    olusturma = Column(DateTime, default=_simdi)
    maddeler = relationship("ItibarMadde", back_populates="arac", cascade="all, delete-orphan")


class ItibarMadde(Base):
    __tablename__ = "reputation_items"
    __table_args__ = (UniqueConstraint("instrument_id", "item_code", name="uq_itibar_madde"),)
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("reputation_instruments.id", ondelete="CASCADE"), index=True, nullable=False)
    construct = Column(String(10), nullable=False)          # pulse | driver
    driver = Column(String(40), nullable=True)
    item_code = Column(String(40), nullable=False)
    wording = Column(Text, default="")
    reverse = Column(Boolean, default=False)
    scale_min = Column(Float, nullable=False)
    scale_max = Column(Float, nullable=False)
    arac = relationship("ItibarArac", back_populates="maddeler")


class ItibarDalga(Base):
    __tablename__ = "survey_waves"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    instrument_id = Column(Integer, ForeignKey("reputation_instruments.id"), nullable=False)
    name = Column(String(200), default="")
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    sampling_frame = Column(Text, default="")
    mode = Column(String(40), default="")
    status = Column(String(20), default="taslak")            # taslak | acik | kapali
    familiarity_min = Column(Integer, nullable=True)         # K1: ön kayıtlı aşinalık eşiği
    olusturma = Column(DateTime, default=_simdi)


class PaydasYaniti(Base):
    __tablename__ = "stakeholder_responses"
    __table_args__ = (UniqueConstraint("wave_id", "respondent_pseudo_id", name="uq_paydas_yanit"),)
    id = Column(Integer, primary_key=True)
    wave_id = Column(Integer, ForeignKey("survey_waves.id", ondelete="CASCADE"), index=True, nullable=False)
    respondent_pseudo_id = Column(String(80), nullable=False)
    stakeholder_group = Column(String(60), nullable=False)
    language = Column(String(10), default="tr")
    familiarity = Column(Float, nullable=True)               # ham aşinalık yanıtı (K1)
    familiarity_eligible = Column(Boolean, default=True)
    design_weight = Column(Float, default=1.0)
    nonresponse_weight = Column(Float, default=1.0)
    final_weight = Column(Float, nullable=True)
    strata = Column(JSON, default=dict)                      # raking değişkenleri (ör. {"yas": "18-29"})
    answers = relationship("ItibarCevap", back_populates="response", cascade="all, delete-orphan")


class ItibarCevap(Base):
    __tablename__ = "reputation_answers"
    __table_args__ = (UniqueConstraint("response_id", "item_id", name="uq_itibar_cevap"),)
    id = Column(Integer, primary_key=True)
    response_id = Column(Integer, ForeignKey("stakeholder_responses.id", ondelete="CASCADE"), index=True, nullable=False)
    item_id = Column(Integer, ForeignKey("reputation_items.id", ondelete="CASCADE"), nullable=False)
    raw_value = Column(Float, nullable=True)
    normalized_value = Column(Float, nullable=True)
    missing_reason = Column(String(30), nullable=True)       # dont_know | skipped
    response = relationship("PaydasYaniti", back_populates="answers")


class NufusMarji(Base):
    __tablename__ = "population_margins"
    id = Column(Integer, primary_key=True)
    wave_id = Column(Integer, ForeignKey("survey_waves.id", ondelete="CASCADE"), index=True, nullable=False)
    stakeholder_group = Column(String(60), nullable=False)
    stratum = Column(String(120), nullable=False)            # "değişken=değer"
    population_share = Column(Float, nullable=False)
    source = Column(String(200), default="")


class ItibarDogrulama(Base):
    """Harici CFA/ω/değişmezlik sonuçları (Rapor Bölüm 7; K9–K11)."""
    __tablename__ = "reputation_validations"
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("reputation_instruments.id", ondelete="CASCADE"), index=True, nullable=False)
    stakeholder_group = Column(String(60), nullable=True)    # None = tüm gruplar
    scoring_spec_hash = Column(String(64), nullable=False)
    cfa_supports_one_factor = Column(Boolean, nullable=False)
    estimator = Column(String(40), default="")
    omega = Column(Float, nullable=True)
    cfa_fit = Column(JSON, default=dict)
    dfi_cutoffs = Column(JSON, default=dict)
    invariance_level = Column(String(30), nullable=True)     # configural|metric|scalar|partial_scalar|strict
    kaynak = Column(String(20), default="harici")
    not_metni = Column(Text, default="")
    olusturma = Column(DateTime, default=_simdi)


class ItibarKosu(Base):
    __tablename__ = "reputation_score_runs"
    id = Column(Integer, primary_key=True)
    wave_id = Column(Integer, ForeignKey("survey_waves.id", ondelete="CASCADE"), index=True, nullable=False)
    model_version = Column(String(40), default="L-PTI-1.0")
    code_commit = Column(String(60), default="")
    weighting_method = Column(String(60), default="")
    missing_method = Column(String(60), default="proration")
    ci_method = Column(String(60), default="linearization")
    min_items = Column(Integer, default=3)
    precision_target = Column(Float, default=5.0)
    params = Column(JSON, default=dict)
    sonuc = Column(JSON, default=dict)                       # API sözleşmesindeki tam çıktı
    olusturma = Column(DateTime, default=_simdi)


class ItibarSkor(Base):
    __tablename__ = "reputation_scores"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("reputation_score_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    stakeholder_group = Column(String(60), nullable=False)
    score = Column(Float, nullable=True)
    estimate = Column(Float, nullable=True)
    se = Column(Float, nullable=True)
    ci_low = Column(Float, nullable=True)
    ci_high = Column(Float, nullable=True)
    n = Column(Integer, default=0)
    n_eff = Column(Float, nullable=True)
    status = Column(String(40), nullable=False)
    reason = Column(String(80), nullable=True)


class ItibarSurucuSkor(Base):
    __tablename__ = "reputation_driver_scores"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("reputation_score_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    stakeholder_group = Column(String(60), nullable=False)
    driver = Column(String(40), nullable=False)
    score = Column(Float, nullable=True)
    se = Column(Float, nullable=True)
    ci_low = Column(Float, nullable=True)
    ci_high = Column(Float, nullable=True)
    n = Column(Integer, default=0)
    n_eff = Column(Float, nullable=True)


class OlcumKalitesi(Base):
    __tablename__ = "measurement_quality"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("reputation_score_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    group = Column(String(60), nullable=True)
    omega = Column(Float, nullable=True)
    estimator = Column(String(40), default="")
    cfa_fit = Column(JSON, default=dict)
    dfi_cutoffs = Column(JSON, default=dict)
    invariance_level = Column(String(30), nullable=True)
    missing_rate = Column(Float, nullable=True)
    ayrinti = Column(JSON, default=dict)


# ---------------------------------------------------------------------------
# Kaynak bağlantıları, kapsam ve sağlık
# ---------------------------------------------------------------------------
class KaynakBaglanti(Base):
    """Kurumun kendi hesabına ait API bağlantısı. Kimlik bilgisi yalnız şifreli saklanır."""
    __tablename__ = "kaynak_baglantilari"
    __table_args__ = (UniqueConstraint("kurum_id", "platform", name="uq_baglanti"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    platform = Column(String(20), nullable=False)       # youtube | x | instagram
    hesap_ref = Column(String(255), default="")         # kanal kimliği / kullanıcı adı / Instagram işletme hesabı kimliği
    sifreli = Column(Text, nullable=False)
    durum = Column(String(20), default="dogrulanmadi")  # dogrulanmadi | bagli | yetki_yok | hata
    son_test = Column(DateTime, nullable=True)
    son_basari = Column(DateTime, nullable=True)
    son_hata = Column(Text, default="")
    kapsam = Column(JSON, default=dict)                 # test sonucu: erişilebilen veri türleri, tarihsel sınır
    olusturma = Column(DateTime, default=_simdi)


class KaynakKapsam(Base):
    """Bir kaynağın başarıyla tarandığı zaman aralığı. Pencerede sıfır içerik ancak bu aralık içindeyse gerçek sıfırdır."""
    __tablename__ = "kaynak_kapsami"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    kaynak = Column(String(30), nullable=False)
    bas = Column(DateTime, nullable=False)
    bit = Column(DateTime, nullable=False)


class KaynakSaglik(Base):
    """Her tarama işinde kaynak başına sonuç: içerik hacminden ayrı, kaynağın gerçek durumu."""
    __tablename__ = "kaynak_sagligi"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    is_id = Column(Integer, nullable=True, index=True)
    kaynak = Column(String(30), nullable=False)
    zaman = Column(DateTime, default=_simdi, index=True)
    durum = Column(String(12), nullable=False)          # tamam | kismi | atlandi | hata
    adet = Column(Integer, default=0)
    istenen_bas = Column(DateTime, nullable=True)
    istenen_bit = Column(DateTime, nullable=True)
    ulasilan_bas = Column(DateTime, nullable=True)
    ulasilan_bit = Column(DateTime, nullable=True)
    mesaj = Column(Text, default="")


class TaramaIsi(Base):
    """Kalıcı iş kuyruğu: geçmiş tarama ve rutin tarama ayrı iş türleridir."""
    __tablename__ = "tarama_isleri"
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    tur = Column(String(10), nullable=False)            # gecmis | rutin | elle
    durum = Column(String(12), default="bekliyor", index=True)   # bekliyor | calisiyor | tamam | kismi | hata | iptal
    bas = Column(DateTime, nullable=False)
    bit = Column(DateTime, nullable=False)
    olusturma = Column(DateTime, default=_simdi)
    baslama = Column(DateTime, nullable=True)
    bitis = Column(DateTime, nullable=True)
    yeni_icerik = Column(Integer, default=0)
    kaynaklar = Column(JSON, default=list)              # kaynak başına sonuç özeti
    mesaj = Column(Text, default="")
    tetikleyen = Column(String(20), default="sistem")   # sistem | kullanici | kayit


# ---------------------------------------------------------------------------
# Bildirim kuyruğu (kalıcı, tekrar denemeli)
# ---------------------------------------------------------------------------
class BildirimKuyrugu(Base):
    __tablename__ = "bildirim_kuyrugu"
    __table_args__ = (UniqueConstraint("anahtar", "alici", name="uq_bildirim_anahtar"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=True)
    alarm_id = Column(Integer, nullable=True, index=True)
    tur = Column(String(20), nullable=False)            # kriz | kriz_guncelleme | haftalik | dogrulama | sifre | test
    anahtar = Column(String(160), nullable=False)       # tekilleştirme anahtarı
    alici = Column(String(255), nullable=False)
    konu = Column(String(300), nullable=False)
    metin = Column(Text, nullable=False)
    html = Column(Text, nullable=True)
    durum = Column(String(20), default="kuyrukta", index=True)  # kuyrukta | gonderiliyor | smtp_kabul | tekrar_bekliyor | kalici_hata | bastirildi
    deneme = Column(Integer, default=0)
    sonraki_deneme = Column(DateTime, default=_simdi, index=True)
    son_hata = Column(Text, default="")
    olusturma = Column(DateTime, default=_simdi)
    gonderim = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# 2. beyin: uzman değerlendirmeleri
# ---------------------------------------------------------------------------
class UzmanForm(Base):
    """Uzman puanlama formunun sürümü. Ölçek ve birleştirme yöntemi araştırmacı kararıdır; sürümle saklanır."""
    __tablename__ = "uzman_formlari"
    id = Column(Integer, primary_key=True)
    surum = Column(String(20), unique=True, nullable=False)
    soru = Column(Text, nullable=False)                 # uzmana sorulan soru (puanın anlamı)
    olcek_min = Column(Float, nullable=False, default=1)
    olcek_max = Column(Float, nullable=False, default=9)
    birlestirme = Column(String(10), default="ortalama")  # ortalama | medyan
    min_uzman = Column(Integer, default=12)
    aktif = Column(Boolean, default=False)
    olusturma = Column(DateTime, default=_simdi)


class UzmanPuani(Base):
    __tablename__ = "uzman_puanlari"
    __table_args__ = (UniqueConstraint("form_id", "uzman_kodu", "gosterge", name="uq_uzman_puan"),)
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey("uzman_formlari.id", ondelete="CASCADE"), index=True, nullable=False)
    uzman_kodu = Column(String(20), nullable=False)     # kodlanmış kimlik (U01…); ad/soyad saklanmaz
    gosterge = Column(String(4), nullable=False)        # G1…G13
    puan = Column(Float, nullable=False)
    gerekce = Column(Text, default="")
    olusturma = Column(DateTime, default=_simdi)


# ---------------------------------------------------------------------------
# PR danışmanı: kontrol listesi
# ---------------------------------------------------------------------------
class PRKontrol(Base):
    __tablename__ = "pr_kontrol"
    __table_args__ = (UniqueConstraint("kurum_id", "alarm_id", "madde", name="uq_pr_kontrol"),)
    id = Column(Integer, primary_key=True)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id", ondelete="CASCADE"), index=True, nullable=False)
    alarm_id = Column(Integer, nullable=False, default=0)   # 0 = genel hazırlık
    madde = Column(String(40), nullable=False)
    tamam = Column(Boolean, default=False)
    zaman = Column(DateTime, default=_simdi)
