"""Kriz yönetimi kontrol listesi ve yanıt hedefleri.

Evre yapısı (hazırlık, ilk 24 saat, çözüm, kriz sonrası) ve yanıt hedefi tablosu AlternaCX'in "Kriz Yönetimi ve CX"
yazısındaki çerçeveden uyarlanmıştır; maddeler bu projede yeniden yazılmıştır. Hedef süreler öneridir, kurum kendi
iletişim ve hukuk ekibinin onayıyla değiştirmelidir. Strateji seçimi (ne söylenecek) Coombs (2007) SCCT kılavuzundan gelir
(pr/strateji.py); bu liste süreci (kim, ne zaman, hangi sırayla) düzenler."""
from __future__ import annotations

KAYNAK = {"ad": "AlternaCX — Kriz Yönetimi ve CX", "url": "https://alternacx.com/kriz-yonetimi-ve-cx/"}

EVRELER = [
    {"kod": "hazirlik", "ad": "Hazırlık", "aciklama": "Kriz olmadan yapılacaklar. Genel hazırlık listesi alarmdan bağımsızdır."},
    {"kod": "ilk24", "ad": "İlk 24 saat", "aciklama": "Alarm açıldığında yapılacaklar; her alarm için ayrı işaretlenir."},
    {"kod": "cozum", "ad": "Çözüm", "aciklama": "Kriz sürerken kök neden, çözüm ve izleme."},
    {"kod": "sonrasi", "ad": "Kriz sonrası", "aciklama": "Kriz kapandıktan sonra telafi, öğrenme ve izleme."},
]

MADDELER = [
    ("h1", "hazirlik", "Sektöre özgü olası kriz senaryoları yazıldı"),
    ("h2", "hazirlik", "Kriz ekibi ve roller belirlendi (lider, sözcü, sosyal medya sorumlusu, hukuk)"),
    ("h3", "hazirlik", "İlk yanıt süresi ve kanal sırası belirlendi"),
    ("h4", "hazirlik", "Kriz türlerine göre mesaj taslakları hazırlandı ve hukuk onayından geçti"),
    ("h5", "hazirlik", "Hangi seviyede kimin kamuya konuşabileceğini gösteren yetki matrisi yazıldı"),
    ("h6", "hazirlik", "Bildirim alıcıları ve e-posta adresleri güncel"),
    ("h7", "hazirlik", "Kriz tatbikatı yapıldı ve playbook güncellendi"),
    ("a1", "ilk24", "Alarm değerlendirildi: gerçek kriz mi, önemsiz mi işaretlendi"),
    ("a2", "ilk24", "Kriz ekibi toplandı"),
    ("a3", "ilk24", "Krizin kapsamı ve etkilenenler değerlendirildi"),
    ("a4", "ilk24", "İlk kamuya açık yanıt yayımlandı (yanıt zamanı alarm kartına girildi)"),
    ("a5", "ilk24", "Tüm kanallarda tutarlı mesaj verildi (web, sosyal medya, e-posta)"),
    ("a6", "ilk24", "Müşteri hizmetleri ekibi bilgilendirildi, ortak yanıt metni verildi"),
    ("a7", "ilk24", "Üst yönetim bilgilendirildi"),
    ("a8", "ilk24", "Güncelleme takvimi belirlendi ve duyuruldu"),
    ("c1", "cozum", "Kök neden belirlendi"),
    ("c2", "cozum", "Çözüm planı ve süresi etkilenenlere bildirildi"),
    ("c3", "cozum", "Etkilenen grupların önceliklendirilmiş çözümleri sunuldu"),
    ("c4", "cozum", "Sosyal dinleme sürdürüldü; olumsuzluk ve hacim eğilimi izlendi"),
    ("s1", "sonrasi", "Kriz çözüldü, ilgili gruplara duyuruldu (çözüm zamanı alarm kartına girildi)"),
    ("s2", "sonrasi", "Telafi paketi sunuldu"),
    ("s3", "sonrasi", "Kök neden ve alınan önlemler paylaşıldı"),
    ("s4", "sonrasi", "Kriz sonrası değerlendirme toplantısı yapıldı"),
    ("s5", "sonrasi", "Playbook öğrenilenlerle güncellendi"),
    ("s6", "sonrasi", "30, 60 ve 90. günlerde olumsuzluk oranı ve hacim izlendi"),
]

# Kriz türü → önerilen ilk yanıt hedefi (kurum düzenler). Kaynak: AlternaCX yazısındaki tablo.
YANIT_HEDEFLERI = [
    {"tur": "Bireysel şikayet", "yaklasim": "Herkese açık özür, çözüm doğrudan mesajla", "hedef": "1-2 saat"},
    {"tur": "Viral şikayet", "yaklasim": "Herkese açık ayrıntılı açıklama ve eylem planı", "hedef": "30 dakika - 1 saat"},
    {"tur": "Yanlış bilgi / söylenti", "yaklasim": "Hızlı doğrulama ve kanıt paylaşımı", "hedef": "15-30 dakika"},
    {"tur": "İtibar krizi / skandal", "yaklasim": "Resmî açıklama ve üst yönetim mesajı", "hedef": "2-4 saat"},
    {"tur": "Operasyonel kriz", "yaklasim": "Durum güncellemeleri ve çözüm zaman çizelgesi", "hedef": "İlk yanıt 1-2 saat, sonra düzenli güncelleme"},
]

OLCUTLER = [
    {"kod": "ilk_yanit", "ad": "İlk yanıt süresi", "tanim": "Alarm başlangıcından kurumun ilk kamuya yanıtına kadar geçen süre"},
    {"kod": "cozum", "ad": "Çözüm süresi", "tanim": "Alarm başlangıcından krizin çözüldüğü ana kadar geçen süre"},
    {"kod": "olumsuzluk", "ad": "Alarm dönemi olumsuzluk oranı", "tanim": "Alarm süresince toplanan sosyal içeriklerin olumsuz oranı"},
    {"kod": "hacim", "ad": "Alarm dönemi içerik hacmi", "tanim": "Alarm süresince toplanan toplam içerik sayısı"},
]

KODLAR = {m[0] for m in MADDELER}


def katalog() -> dict:
    return {"kaynak": KAYNAK, "evreler": EVRELER,
            "maddeler": [{"kod": k, "evre": e, "metin": t} for k, e, t in MADDELER],
            "yanit_hedefleri": YANIT_HEDEFLERI, "olcutler": OLCUTLER}
