# Krizyolda

Kurumlar için kriz erken uyarı ve itibar izleme sistemi. Haber ve sosyal medya içeriklerini sürekli toplar, 13 literatür göstergesiyle
kuruma özgü risk düzeyini hesaplar, eşik aşıldığında kurumun kayıtlı e-posta adreslerine uyarı gönderir ve PR danışmanlığı çıktıları üretir.

## Temel işleyiş

- **Veri kaynakları.** *Açık kaynak* modu anahtar gerektirmez: Google Haber RSS, Bing Haber RSS, Reddit genel arama, Google Trends ve kurumun tanımladığı RSS adresleri.
  Kurum ayrıca kendi YouTube, X ve Instagram hesabının API bilgisini bağlayabilir (Kaynaklar sayfası); bilgiler şifreli saklanır, geri gösterilmez.
- **Analiz aralığı.** 7, 30, 90, 180 gün (6 ay) ya da kurumun seçtiği özel tarih aralığı. İlk tarama aralığın tamamını çeker, sonrakiler yalnız eksik kısmı tamamlar.
  Geçmişte biten özel aralık "geriye dönük inceleme"dir: alarm ve e-posta üretmez.
- **Tekrarlama planı.** Periyodik (sistem aralığı risk düzeyine göre kurumun belirlediği alt-üst sınır içinde seçer: düşük riskte seyrek, kriz sırasında sık) ya da tek seferlik.
  Tarama sıklığı e-posta sıklığından bağımsızdır: bir alarm için ilk e-posta bir kez gider, sonrakiler yalnız seviye yükselirse ve bekleme süresi dolduysa (Kritik'e çıkış beklemez).
- **Eksik veri ≠ sıfır.** Bir pencerede sıfır içerik, yalnızca kaynak o pencereyi başarıyla taramışsa gerçek sıfırdır. Taranmamış, yapılandırılmamış ya da hata veren kaynakta ilgili gösterge
  "veri yok" sayılır. G11 (platformlar arası yayılım) paydası, pencereyi kapsayan kaynakların sayısıdır.
- **İki beyin.** 1. beyin 13 göstergeye eşit ağırlık verir (100/13 puan) ve alarmları belirler. 2. beyin ağırlıkları uzman puanlarından alır (Kendall W ile uyum raporlanır);
  uzman verisi gelene kadar pasiftir ve hiçbir sonucu etkilemez. İkisi aynı z-skorlarıyla hesaplanıp yan yana raporlanır (İki Beyin sayfası).
- **Bildirim.** E-postalar kalıcı kuyruğa yazılır; her alıcıya ayrı mesaj gider, tekilleştirme anahtarı ikinci gönderimi engeller, geçici hatalarda artan beklemeyle yeniden denenir.
  SMTP kabulü "gönderim kabul edildi" olarak adlandırılır, gelen kutusu teslimi anlamına gelmez. Haftalık rapor kurumun seçtiği gün ve saatte (Türkiye saati) haftada bir kez kuyruğa alınır.
- **PR danışmanı.** Haftalık brif, SCCT (Coombs 2007) tabanlı yanıt stratejisi, evre bazlı kriz kontrol listesi ve ölçülen süreç göstergeleri. Hiçbir öneri otomatik yayımlanmaz.

## Mimari

| Bileşen | Açıklama |
|---|---|
| `backend/app` | FastAPI, SQLAlchemy. `collectors` (kaynak adaptörleri), `indicators` (13 gösterge), `detection` (TwitInfo normalleştirme, kuruma özgü eşik, WECO), `beyin` (uzman ağırlıkları ve karşılaştırma), `services` (tarama, kaynak kapsamı, zamanlayıcı, bildirim, alarm), `pr`, `reputation` |
| `backend/app/worker.py` | Tarama işleri, zamanlanmış taramalar, bildirim kuyruğu ve haftalık brif. Ayrı süreç ya da `WORKER_GOMULU=true` |
| `frontend` | React, Vite, Tailwind, Recharts |
| `docs` | Yöntem, gösterge tanımları, tasarım kararları, kaynakça (`python -m scripts.belge_uret` ile koddaki kataloğdan üretilir) |

## Kurulum

Yerel geliştirme:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # SECRET_KEY girin
WORKER_GOMULU=true uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Üretim (Docker, PostgreSQL):

```bash
cp .env.example .env && cp backend/.env.example backend/.env    # iki dosyayı doldurun
docker compose up -d --build
```

`ENV=production` iken uygulama şu koşullar sağlanmadan açılmaz: 32+ karakterlik `SECRET_KEY`, PostgreSQL, https `PANEL_URL`, tanımlı SMTP.
Veritabanına ulaşılamazsa sessizce başka bir veritabanına geçilmez. TLS için önüne bir ters vekil koyun. İlk yönetici için kayıttan önce
`YONETICI_EPOSTALARI` ayarlanmalıdır; bu adresle kayıt olan hesap Uzman Paneli'ne erişir.

## 2. beyin nasıl devreye alınır

1. Yönetici hesabıyla **Uzman Paneli**'nde form sürümü oluşturun: uzmana sorulan soru, puan ölçeği, birleştirme yöntemi (ortalama/medyan) ve gerekli uzman sayısı (varsayılan 12).
2. Her uzman için kod (U01…U12) ile 13 göstergenin puanını girin. Eksik puan sıfır sayılmaz; 13 göstergeyi tamamlamayan uzman hesaba katılmaz.
3. Formu etkinleştirin. Gerekli sayıda tam uzman yoksa 2. beyin pasif kalır ve nedeni arayüzde yazar.

## Testler

```bash
cd backend && python -m pytest -q      # 165 test
cd frontend && npm run typecheck && npm run build
```

Testler sabit tohumlu sentetik içerik kullanır (`backend/tests/sentetik.py`); ürün kodunda örnek ya da sentetik veri üretilmez. Toplayıcı testleri HTTP yanıtlarını taklit eder.

## Sınırlar ve açık kararlar

- **Canlı doğrulama yapılmadı.** Toplayıcılar taklit edilmiş yanıtlarla test edildi; gerçek Google, Bing, Reddit, YouTube, X ve Instagram erişimi, kota ve SMTP teslimi sizin ortamınızda doğrulanmalıdır.
  Google Haber, Bing Haber, Reddit ve Google Trends resmî ve garantili API değildir; biçim ya da erişim değişebilir, bu durumda kaynak "hata" olarak görünür, sıfır içerik sayılmaz.
- **Geçmiş sınırı kaynağa bağlıdır.** Bing yalnız güncel öğeleri döndürür; X arşiv aramasına erişim yetkisi yoksa yalnız son 7 gün; Google Trends saatlik veriyi yalnız son 7 gün için verir;
  Instagram son 50 gönderiyi tarar; YouTube kanalın son 50 videosunu tarar. Ulaşılan aralık Kaynaklar sayfasında yazar.
- **TikTok** için adaptör yoktur; resmî erişim kapsamı doğrulanmadan eklenmedi.
- **Uzman puan ölçeği ve birleştirme yöntemi** araştırmacı kararıdır; sistem varsayım dayatmaz, form sürümünde saklar.
- **OMS başlangıcı** (TwitInfo) orijinal yayıma uygun şekilde ilk p değerin varyansıdır; birim uyuşmazlığı bulunduğundan birincil kaynakla doğrulanmalıdır (Tasarım kararları).
- **Şema güncellemesi** eksik sütunları `ALTER TABLE ADD COLUMN` ile ekler; sütun silme ya da yeniden adlandırma için sürümlü bir migrasyon aracı (Alembic) henüz yoktur.
- **E-posta doğrulama** bilgilendiricidir: kriz uyarıları doğrulanmamış adreslere de gönderilir ki uyarı kaybolmasın.
- **L-PTİ (itibar anketi)** verisi API ile girilir; arayüzde anket oluşturma ekranı yoktur.
- Sistem gerçek krizlerdeki isabeti kanıtlamaz; anomali sinyali insan incelemesi gerektiren bir erken uyarıdır.
