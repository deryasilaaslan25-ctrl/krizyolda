"""
"Kuruma Özgü Kriz Eşiği Metodolojisi" raporunun katalog karşılığı.

Bu dosya yalnızca VERİDİR (kaynaklar, parametre tablosu, kararlar, sınırlılıklar);
formüller app/detection/esik_kalibrasyonu.py içindedir. app/literatur.py bu veriyi
tek katalogda birleştirir ve /api/literatur ile panelin Literatür sekmesine sunar.

KAYNAK URL'LERİ: Raporun kendisi çoğu kaynak için yalnızca kısa atıf (yazar, yıl, dergi)
verir; bağlantı vermez. Bağlantısı doğrulanabilen kaynaklara URL yazılmıştır; diğerlerinde
"url" boştur ve "url_notu" alanı bunu açıkça belirtir. Hiçbir URL uydurulmamıştır.
"""
from __future__ import annotations

_YOK = "URL raporda verilmemiştir; yayımlanmış sürümünden doğrulanıp eklenmelidir."

ESIK_KAYNAKLARI: dict[str, dict[str, str]] = {
    # --- Bağlantısı doğrulanmış (kaynak sayfası/DOI kontrol edildi) ---------------------
    "SIFFER2017": {"atif": "Siffer, A., Fouque, P.-A., Termier, A., & Largouet, C. (2017). Anomaly detection in streams with extreme value theory. Proceedings of KDD 2017, 1067-1075.",
                   "url": "https://doi.org/10.1145/3097983.3098144"},
    "HOSKING_WALLIS1987": {"atif": "Hosking, J. R. M., & Wallis, J. R. (1987). Parameter and quantile estimation for the generalized Pareto distribution. Technometrics, 29(3), 339-349.",
                           "url": "https://doi.org/10.2307/1269343"},
    "BUHLMANN1967": {"atif": "Bühlmann, H. (1967). Experience rating and credibility. ASTIN Bulletin, 4(3), 199-207.",
                     "url": "https://doi.org/10.1017/S0515036100008989"},
    # --- Raporun Bölüm 16 tablosundaki kaynaklar; URL raporda yok -------------------------
    "IEC62682_2022": {"atif": "IEC 62682:2022. Management of alarm systems for the process industries (alarm yönetimi standardı; ANSI/ISA-18.2 ile uyumlu).", "url": "", "url_notu": _YOK},
    "YOUDEN1950": {"atif": "Youden, W. J. (1950). Index for rating diagnostic tests. Cancer, 3(1), 32-35.", "url": "", "url_notu": _YOK},
    "ALFIERI2019": {"atif": "Alfieri vd. (2019). J. Hydrol. X (GloFAS eşiklerinin her konum için ayrı, uç değer dağılımından hesaplanması).", "url": "", "url_notu": _YOK},
    "ROUSSEEUW_HUBERT2018": {"atif": "Rousseeuw & Hubert (2018). WIREs DMKD (medyan/MAD ile sağlam istatistik).", "url": "", "url_notu": _YOK},
    "YARO2024": {"atif": "Yaro vd. (2024). IEEE Access (sağlam istatistik).", "url": "", "url_notu": _YOK},
    "KIM2023": {"atif": "Kim vd. (2023). IEEE TNNLS (eğitim verisi kirlenmesi).", "url": "", "url_notu": _YOK},
    "SHOU2025": {"atif": "Shou vd. (2025). KDD 2025 (eğitim verisi kirlenmesi).", "url": "", "url_notu": _YOK},
    "MURPHY_TAWN_VARTY2025": {"atif": "Murphy, Tawn & Varty (2025). Technometrics (GPD eşik seçimi, EQD yöntemi).", "url": "", "url_notu": _YOK},
    "COLLINGS2025": {"atif": "Collings vd. (2025). NHESS (otomatik eşik seçimi).", "url": "", "url_notu": _YOK},
    "BELZILE2023": {"atif": "Belzile vd. (2023). Extremes (uç değer yazılımları için genel rehber).", "url": "", "url_notu": _YOK},
    "VIGNOTTO_ENGELKE2020": {"atif": "Vignotto & Engelke (2020). Extremes (GPD'nin sınıflandırma eşiği belirlemede kullanımına örnek).", "url": "", "url_notu": _YOK},
    "BAO_BOOTH2021": {"atif": "Bao & Booth (2021). Büzülme ve ampirik Bayes bağlantısı (güvenilirlik kuramı).", "url": "", "url_notu": _YOK},
    "LI_YAN_TSUNG2022": {"atif": "Li, Yan & Tsung (2022). ACM TKDD (benzer kaynaklardan bilgi aktarımıyla soğuk başlangıç anomali tespiti).", "url": "", "url_notu": _YOK},
    "NOCENTINI2024": {"atif": "Nocentini vd. (2024). Landslides (yanlış alarm azaltımına dayalı eşik optimizasyonu; heyelan erken uyarısı, dört kritiklik seviyesi).", "url": "", "url_notu": _YOK},
    "WU2026": {"atif": "Wu vd. (2026). npj Digital Medicine (kademeli erken uyarıda PPV/NPV hedefleriyle eşik seçimi).", "url": "", "url_notu": _YOK},
    "GYASI_WANG2022": {"atif": "Gyasi & Wang (2022). PSEP (ölü bant ile gecikme sayaçlarının birlikte tasarımı).", "url": "", "url_notu": _YOK},
    "RAHIMI2024": {"atif": "Rahimi, Rao & Chen (2024). Alarm eşiği/ölü bant karşılaştırması.", "url": "", "url_notu": _YOK},
    "AHMED2023": {"atif": "Ahmed vd. (2023). IJCIP (alarm yönetimi derlemesi).", "url": "", "url_notu": _YOK},
    "PERRY2019": {"atif": "Perry (2019). Journal of Quality Technology (sosyal ağ izlemede EWMA).", "url": "", "url_notu": _YOK},
    "HSU_WANG2024": {"atif": "Hsu & Wang (2024). Mathematics (sürveyansta EWMA uygulaması).", "url": "", "url_notu": _YOK},
    "LIN_DU_SUN2024": {"atif": "Lin, Du & Sun (2024). IEEE TKDE (uyarlamalı eşikleme).", "url": "", "url_notu": _YOK},
    "CORREIA2024": {"atif": "Correia, Goos & Klein (2024). EAAI (uyarlamalı eşikleme derlemesi).", "url": "", "url_notu": _YOK},
    "ARXIV_2404_13284": {"atif": "arXiv:2404.13284 (2024). Youden indeksi ve eşik seçimi üzerine güncel inceleme.", "url": "https://arxiv.org/abs/2404.13284"},
    "KOCH2021": {"atif": "Koch, Dippel & Schumann (2021). OSNEM (çevrimiçi firestorm/kriz tespiti).", "url": "", "url_notu": _YOK},
    "CHEN_HOLLADAY2022": {"atif": "Chen & Holladay (2022). CCIJ (kriz iletişimi/tespiti).", "url": "", "url_notu": _YOK},
    "NIU2026": {"atif": "Niu, Eng & Jin (2026). Journal of Public Relations Research (kriz tespiti).", "url": "", "url_notu": _YOK},
    "ISO31000_2018": {"atif": "ISO 31000:2018. Risk management — Guidelines.", "url": "", "url_notu": _YOK},
    "PICKANDS_BALKEMA_DEHAAN": {"atif": "Pickands–Balkema–de Haan teoremi (uç değer kuramı): yeterince yüksek eşiğin üstündeki aşımlar Genelleştirilmiş Pareto dağılımına yaklaşır (Rapor Bölüm 4.2).", "url": "", "url_notu": _YOK},
}

# Raporun Bölüm 13 tablosu — parametre, değer, tür, gerekçe, kalibrasyon planı
ESIK_PARAMETRELERI: list[dict] = [
    {"ad": "p_orta, p_yüksek, p_kritik", "deger": "0,05 / 0,01 / 0,001", "tur": "Politika", "gerekce": "Normal dönemdeki kabul edilebilir alarm sıklığı. Dönüş süreleri 20 / 100 / 1000 saat.", "plan": "Pilot kurumlarla alarm yükü ölçümü ve Delphi", "kaynaklar": ["IEC62682_2022"]},
    {"ad": "Pencere", "deger": "90 gün", "tur": "İstatistik/politika", "gerekce": "Kritik kademe için yaklaşık 2 bekleme aşımı + mevsimsellikten kaçınma.", "plan": "Duyarlılık analizi (30/60/90/180 gün)", "kaynaklar": ["THAYER2025"]},
    {"ad": "Blok", "deger": "1 saat", "tur": "Tasarım", "gerekce": "Uyarlamalı tarama yanlılığını giderir.", "plan": "—", "kaynaklar": []},
    {"ad": "Ampirik için min. aşım", "deger": "5", "tur": "İstatistik", "gerekce": "Binom varyansı.", "plan": "—", "kaynaklar": []},
    {"ad": "GPD eşiği u", "deger": "P90", "tur": "İstatistik", "gerekce": "Yaygın başlangıç. Yanlılık–varyans dengesi.", "plan": "EQD otomatik seçim (Murphy vd., 2025) ile karşılaştırma", "kaynaklar": ["SIFFER2017", "MURPHY_TAWN_VARTY2025"]},
    {"ad": "n0", "deger": "100 saat", "tur": "İstatistik", "gerekce": "Z = 0,5 yaklaşık 4 günde.", "plan": "Bühlmann k = v/a ile çok kurumlu veriden tahmin", "kaynaklar": ["BUHLMANN1967"]},
    {"ad": "Havuz minimumu", "deger": "2 kurum, 200 blok", "tur": "Tasarım", "gerekce": "Tek kurumun önseli belirlemesini önler.", "plan": "—", "kaynaklar": []},
    {"ad": "Uzman önseli", "deger": "50 / 75 / 95", "tur": "Politika", "gerekce": "Veri yokken başlangıç.", "plan": "Delphi paneli", "kaynaklar": []},
    {"ad": "Taban", "deger": "25 / 40 / 55", "tur": "Politika", "gerekce": "Sabit etki eşiği (WMO).", "plan": "Delphi paneli + etiketli veri", "kaynaklar": ["WMO2023"]},
    {"ad": "Tavan", "deger": "70 / 85 / 95", "tur": "Politika", "gerekce": "Kronik yüksek kurumda krizin olağanlaşmasını önler.", "plan": "Delphi paneli + etiketli veri", "kaynaklar": ["WMO2023"]},
    {"ad": "c_FN : c_FP", "deger": "5 : 1", "tur": "Politika", "gerekce": "Kaçırmanın maliyeti daha yüksek.", "plan": "Paydaş anketi / Delphi", "kaynaklar": ["YOUDEN1950"]},
    {"ad": "Min. etiket", "deger": "20 (sınıf başına 5)", "tur": "İstatistik", "gerekce": "Aşırı uyumu önler.", "plan": "—", "kaynaklar": []},
    {"ad": "Etiket n0", "deger": "30", "tur": "İstatistik", "gerekce": "Az etikette önsele büzülme.", "plan": "Çapraz doğrulama", "kaynaklar": []},
    {"ad": "Hacim Z", "deger": "3", "tur": "İstatistik", "gerekce": "3-sigma, EWMA.", "plan": "ROC ile doğrulama", "kaynaklar": ["ROBERTS1959"]},
    {"ad": "k_on, k_off", "deger": "2, 3", "tur": "Tasarım", "gerekce": "ISA-18.2 on/off-delay, dang humması 2 ardışık kuralı.", "plan": "Geriye dönük test: öncü süre / yanlış alarm dengesi", "kaynaklar": ["IEC62682_2022", "THAYER2025"]},
    {"ad": "Ölü bant", "deger": "max(2, 0,5·s)", "tur": "Tasarım", "gerekce": "Kurumun gürültüsüne orantılı bant.", "plan": "Gyasi & Wang (2022) yöntemiyle optimizasyon", "kaynaklar": ["GYASI_WANG2022"]},
]

# Rapor Bölüm 15 — sınırlılıklar (birebir) + uygulamaya özgü ek notlar
ESIK_SINIRLILIKLARI: list[str] = [
    "Bağımlılık: Ardışık saatlik bloklar birbirinden bağımsız değildir. Uç değerler kümelenebilir. Bu durum GPD tahminlerinde güven aralıklarını daraltır. Kümeden arındırma (declustering) ve uç değer indeksi (extremal index) ele alınmalıdır.",
    "Kirlenme döngüsü: Kaçırılmış ve etiketlenmemiş bir kriz, normal döneme karışabilir. Alarm seviyesindeki ölçümlerin dışlanması bu riski azaltır ama tamamen ortadan kaldırmaz.",
    "Sektör homojenliği: Sektör önseli, sektör içi kurumların benzer olduğunu varsayar. Kurum büyüklüğü ve takipçi sayısı gibi değişkenlerle alt gruplama bir iyileştirme seçeneğidir.",
    "Durağan olmama: 90 günlük pencere yavaş değişimlere uyum sağlar, ancak ani yapısal kırılmalarda (birleşme, marka değişikliği) gecikir.",
    "Risk puanının kendisi: Bu metodoloji puanın kademelere nasıl ayrılacağını belirler; puanı oluşturan bileşenlerin ağırlıklarının doğrulanması ayrı bir konudur. ERKİS'te puan, KRE'den türetilen Z'dir (Tasarım kararı 30).",
    "Sağlam z-puanı simetri varsayar. Bu nedenle yalnızca az veride kullanılır ve güçlü büzülmeyle birleştirilir.",
    "Etiketler yalnızca alarm üreten ölçümlerden gelir (kesilmiş örnek): kaçırılan krizler sistemce bilinemez; maliyet-optimal c* yalnızca etiketli puan aralığında anlamlıdır (Tasarım kararı 41).",
    "Politika türündeki parametreler (p_k, taban/tavan, uzman önseli, c_FN:c_FP) veriden türetilemez; bu sürümdeki değerler gerekçeli başlangıç değerleridir ve Delphi paneli ile etiketli veriyle belirlenmelidir.",
    "Bu sistemin gerçek krizlerdeki isabeti iddia edilmemektedir; raporun simülasyon sonuçları (hedef aşım oranları) yalnızca eşik kalibrasyonunun tutarlılığını gösterir.",
]

# Yeni tasarım kararları (numaralar app/literatur.py'de sıraya eklenir)
ESIK_KARARLARI: list[dict] = [
    {"kaynak": "esik", "baslik": "Eşik metodolojisinin uygulandığı risk puanı R",
     "aciklama": "Metodoloji 0–100 aralığında bir 'risk puanı' varsayar; ERKİS v4 raporunda böyle bir puan tanımlı değildir, KRE'den türetilen standart normal Z vardır. R = 100·min(max(Z,0), 6)/6 alınır (16,7 puan/σ). Yüzdelik eşikler tekdüze dönüşümlere karşı değişmez olduğundan bu seçim yalnızca mutlak korkulukları ve uzman önselini etkiler. 6σ ölçeğinin gerekçesi: (a) raporun taban değerleri 25/40/55, standart normal dağılımda p = 0,05/0,01/0,001 kuantillerine (1,64/2,33/3,09σ) 1,5/2,4/3,3σ ile yakındır; yani 'hiçbir kurumda bağımsız-normal varsayımının olağan sayacağı düzeyin altı alarm sayılmaz' anlamına gelir; (b) tavan değerleri (70/85/95 → 4,2/5,1/5,7σ) ve uzman önseli (50/75/95 → 3,0/4,5/5,7σ), Stouffer birleştirmesinin şişirdiği Z dağılımının (bağımsızlık varsayımı ihlali) üst kuyruğuna izin verir; 4σ gibi daha sıkı bir ölçek tavanların şişmiş Z'yi kronik alarma çevirmesine yol açar. Z ≤ 0 için R = 0 alınır. Kaynak atfedilmemiştir; Delphi paneliyle ölçek ve korkuluklar birlikte belirlenmelidir."},
    {"kaynak": "esik", "baslik": "Ölçüm birimi: 1 saatlik pencere",
     "aciklama": "Metodolojide 'ölçüm' bir taramadır ve saatlik bloklar blok maksimumuyla oluşturulur. ERKİS analizi tamamlanmış saatlik pencerelerle çalıştığından ölçüm = pencere kabul edilir; k_on = 2 ve k_off = 3 ardışık pencere (saat) sayısıdır. Aynı pencere birden çok taramada yeniden ölçülürse blok maksimumu alınır ve pencerenin kararı bir önceki pencerenin durumundan yeniden hesaplanır (aynı saatteki iki tarama teyit sayılmaz)."},
    {"kaynak": "esik", "baslik": "Hacim şoku Z_hacim",
     "aciklama": "Raporda 'son 24 saatin saatlik EWMA'sına göre standartlaştırılır' denir; formül verilmemiştir. Uygulama: içerik sayısının (sosyal+haber) son 24 saatlik değerlerinin EWMA'sı (λ = α = 0,125, TwitInfo ile aynı) referans ortalama alınır; ölçek olarak son 24 saatin örneklem standart sapması ile EWMA ortalamasının karekökünden büyük olanı alınır (sayım verisinde varyans en az ortalama kadar: Poisson tabanı). Z_hacim = (x_t − EWMA)/ölçek."},
    {"kaynak": "esik", "baslik": "Sağlam z-puanında MAD = 0",
     "aciklama": "R sıfırda kırpıldığından puanların yarıdan fazlası aynı (0) olabilir ve MAD = 0 çıkar. Bu durumda s, örneklem standart sapmasına eşitlenir; o da 0 ise sağlam-z eşiği tanımsız kabul edilir ve önsele dönülür."},
    {"kaynak": "esik", "baslik": "GPD uyum kabulü",
     "aciklama": "GPD kuyruk modeli 'uyduysa' kullanılır. Kabul ölçütü: en az 20 aşım, σ̂ > 0 ve −1 < ξ̂ < 0,5. Üst sınır Hosking & Wallis (1987) PWM tahmincilerinin asimptotik özellikleri için gereken ξ < 1/2 koşuludur; alt sınır tasarım seçimidir."},
    {"kaynak": "esik", "baslik": "Isınma ve tanımsız pencereler",
     "aciklama": "Isınma penceresindeki (ilk 28) ve Z'si tanımsız pencereler ölçüm üretmez, normal dönem dağılımına girmez (veri yokluğu 0 sayılmaz)."},
    {"kaynak": "esik", "baslik": "Geçmiş ölçümlerin yeniden oynatılması",
     "aciklama": "Kurumun saklı ölçümü olmayan pencereleri (ilk çalıştırma ya da tarama kesintisi) kronolojik sırayla, o ana kadarki veriyle, gerçek zamanlı çalışmış gibi hesaplanır ve 'geçmiş' işaretlenir. Geçmiş ölçümler tek başına bildirim üretmez; yalnızca son pencerede açık olan alarm bildirilir."},
    {"kaynak": "esik", "baslik": "Alarm (kriz kaydı) dönemi",
     "aciklama": "Metodolojiye göre nihai seviye Yüksek ya da Kritik olduğunda kriz kaydı açılır. Dönem, nihai seviyesi ≥ Yüksek olan ardışık pencerelerdir; önceki dönemin bitişinden en fazla 6 saat sonra başlayan dönem aynı krize ait sayılır ve birleştirilir. Alarma bağlı ölçümler alarm kimliğiyle işaretlenir (kirlenme kuralları için)."},
    {"kaynak": "esik", "baslik": "Bildirim kuralı",
     "aciklama": "E-posta, kriz kaydı açıldığında (varsayılan en düşük seviye: Yüksek) her alarm dönemi için bir kez gönderilir; alarm daha yüksek seviyeye çıkarsa tek bir güncelleme e-postası gönderilir. Bu bir tespit kuralı değil iletim tercihidir."},
    {"kaynak": "esik", "baslik": "Aynı krizin tanınması (parmak izi)",
     "aciklama": "Geri bildirimle öğrenme için iki alarmın 'aynı kriz' olup olmadığı şöyle belirlenir: alarm süresince toplanan negatif/kriz içeriklerinden TF-IDF ile en ayırt edici 8 sözcük gövdesi (5 karakterlik önek, Can vd. 2008) ve baskın SCCT kriz tipi saklanır. İki alarm, gövde kümelerinin Jaccard benzerliği ≥ 0,5 ise ya da baskın SCCT tipi aynı ve benzerlik ≥ 0,2 ise aynı kriz sayılır. Eşikler kaynaksızdır ve etiketli veriyle ayarlanmalıdır."},
    {"kaynak": "esik", "baslik": "Önemsiz işaretli krizin bastırılması",
     "aciklama": "Kurum bir alarmı 'önemsiz' işaretlediğinde aynı alarm dönemi için başka e-posta gönderilmez ve daha sonra ortaya çıkan aynı kriz (parmak izi eşleşmesi) e-posta üretmez; alarm panelde yine kayıtlıdır. İstisna: alarm, önemsiz işaretlenen benzer alarmın ulaştığı en yüksek seviyeden daha yüksek bir seviyeye çıkarsa bildirilir. Bu istisna, metodolojinin kaçırmayı (c_FN = 5) yanlış alarmdan (c_FP = 1) pahalı sayan politikasıyla tutarlıdır."},
    {"kaynak": "esik", "baslik": "Etiket için alarm puanı",
     "aciklama": "Maliyet-duyarlı eşik düzeltmesinde (Metodoloji Bölüm 6) her etiketli kriz kaydı, dönemindeki en yüksek R değeriyle temsil edilir. Etiketler yalnızca alarm üreten ölçümlerden geldiği için örnek kesiktir (Sınırlılıklar)."},
    {"kaynak": "esik", "baslik": "Uyarlamalı tarama aralığı",
     "aciklama": "Metodoloji 5–60 dakikalık uyarlamalı tarama öngörür (tarama_araligi.py). Varsayılan: Düşük 60, Orta 30, Yüksek 15, Kritik 15 dakika; alt sınır TARAMA_ARALIGI_MIN ile 5 dakikaya indirilebilir. YouTube search.list gibi kotalı kaynaklar nedeniyle 5 dakika varsayılan değildir. Ölçüm birimi pencere olduğundan sık tarama yalnızca geç gelen içeriği yakalar."},
    {"kaynak": "esik", "baslik": "WECO katmanının rolü",
     "aciklama": "v5'te WECO kuralları karar verirdi. Kuruma özgü eşik metodolojisi entegre edildiğinden karar (kriz kaydı, bildirim) eşik katmanındadır; WECO kuralları (özellikle Kural 4, 'sessiz birikim' / prodromal evre) açıklayıcı ve erken sinyal göstergesi olarak paneldedir ve PR danışmanlığı brifine girer. Bu, v5 Tasarım kararı 22'nin yerini alır."},
    {"kaynak": "esik", "baslik": "Sektör/platform önselinin kaynağı",
     "aciklama": "Önsel havuzu, aynı veritabanındaki diğer kurumların normal dönem blokları olduğundan havuz ancak yeterli sayıda gerçek kurum ve blok biriktikten sonra devreye girer; öncesinde uzman önseli (50/75/95) kullanılır."},
    {"kaynak": "esik", "baslik": "Etiketsiz alarm ölçümlerinin karantinası (kararlılık düzeltmesi)",
     "aciklama": "Metodoloji Bölüm 3.3 kural 2 nihai seviyesi Yüksek/Kritik olan ölçümleri normal dönemden dışlar. Bu kural tek başına uygulanırsa eşik bir 'tırmanma çarkına' girer: her hesapta eşiği aşan ölçümler dışlanır, kalan verinin P99'u bir öncekinden düşük çıkar, eşik zamanla düşer ve alarm sıklığı hedeflenen %1'in çok üzerine çıkar (kararlı nokta yoktur; korkuluk tabanı dışında bir durdurucu bulunmaz). Bu nedenle etiketsiz alarm ölçümleri yalnızca son 14 gün dışlanır (analistin geri bildirim vermesi için süre); daha eskileri, analist 'gerçek kriz' işaretlemediyse normal dönem verisine geri döner. 'Gerçek kriz' işaretli alarmlara bağlı ölçümler her zaman dışlanır (kural 1), 'önemsiz' işaretliler her zaman geri alınır (kural 3). 14 günlük süre kaynaksızdır ve duyarlılık analiziyle sınanmalıdır; raporun 'kaçırılmış ve etiketlenmemiş kriz normal döneme karışabilir' sınırlılığını kısmen yeniden açar."},
]
