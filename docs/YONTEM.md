# ERKİS v5 — Yöntem ve Kuruma Özgü Kriz Eşiği

Bu belge sistemin bir kurum için kriz seviyesini nasıl hesapladığını adım adım anlatır. Köşeli parantez içindeki
kimlikler (ör. [MARCUS2011]) `docs/KAYNAKCA.md` dosyasındaki tam künye ve bağlantıya karşılık gelir; belgenin sonunda
bu belgede kullanılan kaynakların bağlantıları ayrıca listelenmiştir. Literatürden doğrudan gelmeyen her seçim
`docs/TASARIM_KARARLARI.md` dosyasında numarasıyla listelenmiştir ve bu seçimlere kaynak atfedilmemiştir.

Göstergeler, sabitler ve formüller ERKİS v4 Literatür ve Göstergeler Raporu'ndan alınmıştır. v5'te rapora eklenen tek
katman "kuruma özgü eşik istatistikleri"dir (Bölüm 7); bu katman karar kuralını değiştirmez (Tasarım kararı 22).

## 1. Zaman penceresi

Akış 1 saatlik pencerelere bölünür; son 30 günün yalnız tamamlanmış pencereleri analiz edilir (720 pencere). Saatlik
toplama TwitInfo'nun bin (kutu) yaklaşımından gelir [MARCUS2011]; 30 günlük analiz aralığı ve "yalnız tamamlanmış
pencere" kuralı tasarım kararıdır (Tasarım kararları 9 ve 26).

## 2. Göstergeler

Her pencerede 13 gösterge ölçülür; altı boyuta ayrılır. Tam ölçüm tanımları, gerekçeler ve kaynaklar
`docs/GOSTERGELER.md` dosyasındadır.

| Boyut | Göstergeler | Temel kaynaklar |
|---|---|---|
| Dikkat | G1 sosyal hacim, G2 tekil yazar, G4 Google Trends, G5 haber hacmi | [PFEFFER2014], [MARCUS2011], [CHOI_VARIAN2012], [DEEPHOUSE2000] |
| Tonalite | G6 sosyal olumsuzluk oranı, G7 haber olumsuzluğu (ters Janis–Fadner) | [HERHAUSEN2019], [DEEPHOUSE2000], [JANIS_FADNER1965] |
| Uyarılmışlık | G8 öfke, G9 korku/kaygı, G10 iğrenme yoğunluğu | [HERHAUSEN2019], [BERGER_MILKMAN2012] |
| Yayılım | G3 etkileşim (viralite), G11 platformlar arası yayılım | [STIEGLITZ2013], [PFEFFER2014] |
| Davranış niyeti | G12 boykot / olumsuz ağızdan ağıza oranı | [COOMBS_HOLLADAY2007], [HERHAUSEN2019] |
| Sorumluluk | G13 SCCT sorumluluk yüklemesi | [COOMBS2007], [COOMBS_HOLLADAY2002] |

Duygu sayımları NRC EmoLex Türkçe dosyasıyla yapılır [MOHAMMAD_TURNEY2013; NRC_EMOLEX]. Bir içerik, olumsuz sözcük
sayısı olumlu sözcük sayısından büyükse olumsuzdur [HERHAUSEN2019]. Türkçe "değil" ve "yok" kendinden önceki sözcüğün
kutbunu çevirir [GOKSEL_KERSLAKE2005]; 5 karakterlik önek eşleşmesi Türkçe gövdeleme bulgusuna dayanır [CAN2008].

Haber tonalitesi Janis–Fadner katsayısıyla ölçülür [JANIS_FADNER1965; DEEPHOUSE2000]:

\[
JF = \begin{cases} (f^2 - fu)/N^2 & f > u \\ 0 & f = u \\ (fu - u^2)/N^2 & f < u \end{cases}
\qquad G7 = -JF
\]

Burada \(f\) olumlu, \(u\) olumsuz haber sayısı, \(N\) toplam haber sayısıdır; işaret, yüksek değer "kötü" olacak
şekilde çevrilir.

Q1 (koordineli/kopya içerik oranı) formüle girmez; yüksekse sinyalin yapay olabileceği uyarısı verilir [PACHECO2021].

## 3. Her göstergenin kendi akışında normalleştirilmesi

Her gösterge kurumun kendi geçmişine göre, TwitInfo Algoritma 1 ile normalleştirilir [MARCUS2011]. Bu adım eşiği
kuruma özgü kılan adımdır: aynı ham değer büyük bir kurum için olağan, küçük bir kurum için olağandışı olabilir.

\[
s_{i,t} = \frac{x_{i,t} - \mu_{i,t-1}}{\sqrt{\pi/2}\;\cdot\;\mathrm{OMS}_{i,t-1}}
\]

\[
\mathrm{OMS}_{i,t} = \alpha\,|\mu_{i,t-1} - x_{i,t}| + (1-\alpha)\,\mathrm{OMS}_{i,t-1},
\qquad
\mu_{i,t} = \alpha\,x_{i,t} + (1-\alpha)\,\mu_{i,t-1},
\qquad \alpha = 0{,}125
\]

- \(\alpha = 0{,}125\) TwitInfo'nun TCP tur süresi kestiriminden aldığı değerdir [MARCUS2011; RFC6298; JACOBSON1988].
- Ortalama mutlak sapmanın (OMS) standart sapmaya dönüşümü için normal dağılımda \(\sigma = \sqrt{\pi/2}\cdot\mathrm{OMS}\)
  ilişkisi kullanılır [GEARY1935].
- Başlatma: \(\mu\) ilk değer, OMS ilk \(p = 5\) değerin varyansı [MARCUS2011]; popülasyon varyansı seçimi raporun
  Tasarım kararı 4'üdür. OMS = 0 ise skor tanımsızdır ve gösterge o pencerede eksik sayılır.

## 4. Kırpma ve ağırlıklandırma

\[
\tilde s_{i,t} = \min(\max(s_{i,t}, -3), +3)
\]

±3 sınırı kontrol kartı geleneğinden [SHEWHART1931] ve bileşik gösterge el kitabının uç değer önerisinden gelir [OECD2008].

Ağırlıklar eşittir: önce altı boyuta, sonra boyut içindeki göstergelere [OECD2008]:

\[
w_i = \frac{1}{|D|}\cdot\frac{1}{|I_{d(i)}|}, \qquad \sum_i w_i = 1
\]

Bir göstergenin verisi yoksa ağırlıklar mevcut göstergeler üzerinden yeniden normalleştirilir (Tasarım kararı 5).

## 5. Kriz Risk Endeksi (KRE) ve Z

\[
\mathrm{KRE}_t = \sum_i w_i\,\tilde s_{i,t},
\qquad
Z_t = \frac{\sum_i w_i\,\tilde s_{i,t}}{\sqrt{\sum_i w_i^2}},
\qquad
\text{yüzdelik} = 100\cdot\Phi(Z_t)
\]

\(Z\), ağırlıklı Stouffer birleştirmesidir [WHITLOCK2005; COUSINS2007]. Bileşenler bağımsız standart normal olduğunda
\(Z\) de standart normaldir; bu nedenle aşağıdaki σ bölgeleri doğrudan \(Z\) üzerinde tanımlanabilir.

İsteğe bağlı Strube düzeltmesi (`ERKIS_Z_YONTEMI=strube`, Tasarım kararı 20) göstergeler arası korelasyonu hesaba katar
[STRUBE1985; CINAR_VIECHTBAUER2022]:

\[
Z_t = \frac{\sum_i w_i\,\tilde s_{i,t}}{\sqrt{\sum_i \sum_j w_i w_j \rho_{ij}}}
\]

\(\rho_{ij}\), kurumun ısınma sonrası skorlarından kestirilir.

## 6. Seviye kararı: Western Electric kuralları

\(Z\) dizisine üst taraf Western Electric kuralları uygulanır [WECO1956; NIST_WECO]. Birden fazla kural ihlal edilirse
en yüksek seviye alınır.

| Kural | Koşul | Seviye |
|---|---|---|
| 1 | Tek nokta \(Z > 3\) | KRİZ (3) |
| 2 | Son 3 noktanın 2'si \(Z > 2\) | YÜKSEK UYARI (2) |
| 3 | Son 5 noktanın 4'ü \(Z > 1\) | ERKEN UYARI (1) |
| 4 | 8 ardışık nokta \(Z > 0\) ("sessiz birikim") | ERKEN UYARI (1) |

Kural 4'ün "prodromal evre" yorumu kriz evreleri modeline dayanır [FINK1986]. İlk 28 pencere ısınma dönemidir; bu
dönemde seviye üretilmez [MARCUS2011; FISHER_P05]. Isınma sonrası nokta dizisinin nasıl kurulduğu Tasarım kararı 23'tür.

## 7. Kuruma özgü eşik istatistikleri (v5)

Bu katman seviye kararını değiştirmez (Tasarım kararı 22). Kararın kurum için ne anlama geldiğini ve kurumun kendi
geçmişine göre ne kadar olağandışı olduğunu gösterir.

### 7.1 Ham birim eşikler

Bir sonraki pencerede göstergenin \(+k\sigma\) bölgesine girmesi için gereken ham değer, Bölüm 3'teki skorun tersidir
[MARCUS2011; GEARY1935]:

\[
x^{*}_{i,k} = \mu_{i,t} + k\cdot\sqrt{\pi/2}\cdot\mathrm{OMS}_{i,t}, \qquad k \in \{1, 2, 3\}
\]

\(\mu\) ve OMS kurumun kendi akışından geldiği için eşik kuruma özgüdür. Aşırı olayları sabit mutlak eşikle değil yerel
dağılıma göre tanımlama ilkesi WMO kılavuzunda [WMO2023] ve yakın tarihli bir halk sağlığı uygulamasında [THAYER2025]
yer alır.

### 7.2 Ampirik aşım olasılığı ve dönüş süresi

\[
\hat p_t = \frac{1 + \#\{j : Z_j \ge Z_t\}}{n + 1}, \qquad \text{dönüş süresi} = \frac{\text{pencere uzunluğu}}{\hat p_t}
\]

\(Z_j\) kurumun ısınma sonrası geçmiş değerleridir (mevcut nokta hariç). \(+1\) düzeltmesi sıfır olasılık üretilmesini
önler [PHIPSON_SMYTH2010]. Dönüş süresi kavramı [WMO2023; THAYER2025] kaynaklıdır.

### 7.3 Kalibrasyon tanısı

Bağımsızlık varsayımı altında \(P(Z > k) = 1 - \Phi(k)\) [WHITLOCK2005]. Kurumun gözlenen aşım oranının %95
Clopper–Pearson aralığı [CLOPPER_PEARSON1934] bu nominal değeri içermiyorsa "şişme" (gözlenen fazla) ya da "daralma"
(gözlenen az) uyarısı verilir. Bu, raporun Bölüm 8'de belirttiği Stouffer sınırlılığının kuruma özgü ölçümüdür.

### 7.4 Kullanıcı geri bildirimiyle başarım

Kullanıcı alarm dönemlerini "gerçek kriz" ya da "yanlış alarm" olarak etiketleyebilir. Seviye bazında kesinlik
\(TP/(TP+FP)\) [FAWCETT2006] ve %95 Clopper–Pearson aralığı [CLOPPER_PEARSON1934] raporlanır. Kaçırılan krizler sistemce
bilinemediği için duyarlılık hesaplanmaz.

## 8. SCCT itibar tehdidi

İçerikler Coombs'un kriz tiplerine eşlenir ve üç kümeye ayrılır: mağdur (hafif), kaza (orta), önlenebilir (şiddetli)
[COOMBS2007]. Kriz geçmişi ya da olumsuz önceki itibar tehdidi bir kademe artırır [COOMBS2007; COOMBS_HOLLADAY2002].
Önceki itibar kullanıcı tarafından girilmezse ısınma dönemi Janis–Fadner katsayısından belirlenir (katsayı negatifse
"olumsuz") [DEEPHOUSE2000]. Türkçe tohum ifadeleri bir operasyonelleştirmedir (Tasarım kararı 1); alternatif olarak
çok dilli sıfır-atış NLI modeli kullanılabilir [LAURER2024] (Tasarım kararı 19).

## 9. v4 sürümünden kaldırılan literatür dışı parametreler

Önceki sürümdeki şu değerlerin literatürde karşılığı bulunmadığı için v5'te hiçbiri kullanılmamaktadır:

- 50 / 75 / 95 sabit risk sınırları ve bunlara bağlı ön olasılıklar,
- 25 / 40 / 55 alt sınırları (taban) ve üst sınırlar (tavan),
- \(n_0 = 100\) büzülme parametresi ve \(c_{FN} = 5\) maliyet oranı,
- \(p = 0{,}05 / 0{,}01 / 0{,}001\) basamakları,
- \(k_{on}\) / \(k_{off}\) histerezis katsayıları,
- EWMA tabanlı "+1 seviye" kuralı.

Bunların yerini Bölüm 3–7'deki kaynaklı formüller almıştır.

## 10. Sentetik demo bulguları (doğrulama değildir)

Geliştirme ortamındaki üç demo hesabı tamamen sentetik veri kullanır (Tasarım kararı 29). Aşağıdaki sonuçlar yalnız
kodun beklendiği gibi çalıştığını gösterir; gerçek krizlerdeki isabet iddiası değildir.

| Kurum (senaryo) | Stouffer: son seviye / 30 günde alarm dönemi | Strube: son seviye / 30 günde alarm dönemi |
|---|---|---|
| Anadolu Gıda A.Ş. (önlenebilir kriz) | YÜKSEK UYARI, tehdit Şiddetli / 33 | YÜKSEK UYARI / 10 |
| Örnek İlçe Belediyesi (kaza) | YÜKSEK UYARI, tehdit Orta / 35 | YÜKSEK UYARI / 15 |
| Umut Derneği (kriz yok) | NORMAL / 38 | NORMAL / 8 |

Kriz içermeyen sentetik akışta Stouffer modunda 38 alarm dönemi oluşması ve kalibrasyon tanısının üç eşikte de
"şişme" vermesi, göstergeler arası korelasyonun Z'yi büyüttüğünü gösterir. Strube modunda alarm dönemi sayısı 8'e
iner ve kalibrasyon \(k = 1\) ve \(k = 3\)'te "uyumlu", \(k = 2\)'de "şişme" olur. Korelasyon aynı 30 günlük pencereden
kestirildiği için bu sonuç iyimser olabilir; gerçek veride etiketli kriz vakalarıyla ayrıca doğrulanmalıdır.

## Bu belgede atıf yapılan kaynaklar

- **MARCUS2011** — Marcus, A., Bernstein, M. S., Badar, O., Karger, D. R., Madden, S., & Miller, R. C. (2011). TwitInfo: Aggregating and visualizing microblogs for event exploration. Proceedings of CHI 2011, 227-236. https://dspace.mit.edu/handle/1721.1/72370
- **PFEFFER2014** — Pfeffer, J., Zorbach, T., & Carley, K. M. (2014). Understanding online firestorms: Negative word-of-mouth dynamics in social media networks. Journal of Marketing Communications, 20(1-2), 117-128. https://doi.org/10.1080/13527266.2013.797778
- **CHOI_VARIAN2012** — Choi, H., & Varian, H. (2012). Predicting the present with Google Trends. Economic Record, 88(s1), 2-9. https://doi.org/10.1111/j.1475-4932.2012.00809.x
- **DEEPHOUSE2000** — Deephouse, D. L. (2000). Media reputation as a strategic resource: An integration of mass communication and resource-based theories. Journal of Management, 26(6), 1091-1112. https://doi.org/10.1177/014920630002600602
- **HERHAUSEN2019** — Herhausen, D., Ludwig, S., Grewal, D., Wulf, J., & Schoegel, M. (2019). Detecting, preventing, and mitigating online firestorms in brand communities. Journal of Marketing, 83(3), 1-21. https://doi.org/10.1177/0022242918822300
- **JANIS_FADNER1965** — Janis, I. L., & Fadner, R. H. (1965). The coefficient of imbalance. In H. D. Lasswell, N. Leites et al. (Eds.), Language of Politics: Studies in Quantitative Semantics. Cambridge, MA: MIT Press. (Deephouse, 2000 aracılığıyla uygulanmıştır.) https://study.sagepub.com/sites/default/files/3 Deephouse.pdf
- **BERGER_MILKMAN2012** — Berger, J., & Milkman, K. L. (2012). What makes online content viral? Journal of Marketing Research, 49(2), 192-205. https://doi.org/10.1509/jmr.10.0353
- **STIEGLITZ2013** — Stieglitz, S., & Dang-Xuan, L. (2013). Emotions and information diffusion in social media: Sentiment of microblogs and sharing behavior. Journal of Management Information Systems, 29(4), 217-248. https://doi.org/10.2753/MIS0742-1222290408
- **COOMBS_HOLLADAY2007** — Coombs, W. T., & Holladay, S. J. (2007). The negative communication dynamic: Exploring the impact of stakeholder affect on behavioral intentions. Journal of Communication Management, 11(4), 300-312. https://doi.org/10.1108/13632540710843913
- **COOMBS2007** — Coombs, W. T. (2007). Protecting organization reputations during a crisis: The development and application of Situational Crisis Communication Theory. Corporate Reputation Review, 10(3), 163-176. https://doi.org/10.1057/palgrave.crr.1550049
- **COOMBS_HOLLADAY2002** — Coombs, W. T., & Holladay, S. J. (2002). Helping crisis managers protect reputational assets: Initial tests of the Situational Crisis Communication Theory. Management Communication Quarterly, 16(2), 165-186. https://doi.org/10.1177/089331802237233
- **MOHAMMAD_TURNEY2013** — Mohammad, S. M., & Turney, P. D. (2013). Crowdsourcing a word-emotion association lexicon. Computational Intelligence, 29(3), 436-465. (NRC EmoLex; Türkçe çeviri dosyası dahil) https://arxiv.org/abs/1308.6297
- **NRC_EMOLEX** — National Research Council Canada. NRC Word-Emotion Association Lexicon (EmoLex) - araştırma amaçlı ücretsiz, ticari kullanım lisanslı. https://nrc.canada.ca/en/research-development/products-services/technical-advisory-services/sentiment-emotion-lexicons
- **GOKSEL_KERSLAKE2005** — Göksel, A., & Kerslake, C. (2005). Turkish: A Comprehensive Grammar. London: Routledge. ('değil' ve 'yok' olumsuzluk işaretleri) https://www.routledge.com/Turkish-A-Comprehensive-Grammar/Goksel-Kerslake/p/book/9781138350533
- **CAN2008** — Can, F., Kocberber, S., Balcik, E., Kaynak, C., Ocalan, H. C., & Vursavas, O. M. (2008). Information retrieval on Turkish texts. JASIST, 59(3), 407-421. (F5: ilk 5 karakterle kesme) https://repository.bilkent.edu.tr/server/api/core/bitstreams/d108cb89-6abe-4dd8-856e-2540b8f0717d/content
- **PACHECO2021** — Pacheco, D., Hui, P.-M., Torres-Lugo, C., Truong, B. T., Flammini, A., & Menczer, F. (2021). Uncovering coordinated networks on social media: Methods and case studies. Proceedings of ICWSM 2021. https://arxiv.org/abs/2001.05658
- **RFC6298** — Paxson, V., Allman, M., Chu, J., & Sargent, M. (2011). RFC 6298: Computing TCP's Retransmission Timer (RFC 2988'in güncel sürümü; TwitInfo RFC 2988'e atıf yapar). https://www.rfc-editor.org/rfc/rfc6298
- **JACOBSON1988** — Jacobson, V. (1988). Congestion avoidance and control. ACM SIGCOMM Computer Communication Review, 18(4), 314-329. https://doi.org/10.1145/52324.52356
- **GEARY1935** — Geary, R. C. (1935). The ratio of the mean deviation to the standard deviation as a test of normality. Biometrika, 27(3-4), 310-332. (Normal dağılımda OMS/SS = sqrt(2/pi)) https://doi.org/10.1093/biomet/27.3-4.310
- **SHEWHART1931** — Shewhart, W. A. (1931). Economic Control of Quality of Manufactured Product. New York: Van Nostrand. (3-sigma kontrol sınırları) https://www.iise.org/uploadedfiles/IIE/Education/Six_Sigma_Green_Belt_Transition/Shewhart and Variation.pdf
- **OECD2008** — OECD & European Commission JRC (2008). Handbook on Constructing Composite Indicators: Methodology and User Guide. Paris: OECD Publishing. https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf
- **WHITLOCK2005** — Whitlock, M. C. (2005). Combining probability from independent tests: The weighted Z-method is superior to Fisher's approach. Journal of Evolutionary Biology, 18(5), 1368-1373. (Ağırlıklı Stouffer Z: Mosteller & Bush genellemesi) https://doi.org/10.1111/j.1420-9101.2005.00917.x
- **COUSINS2007** — Cousins, R. D. (2007). Annotated bibliography of some papers on combining significances or p-values. arXiv:0705.2209. (Stouffer ve ağırlıklı Stouffer formülleri) https://arxiv.org/abs/0705.2209
- **STRUBE1985** — Strube, M. J. (1985). Combining and comparing significance levels from nonindependent hypothesis tests. Psychological Bulletin, 97(2), 334-341. https://doi.org/10.1037/0033-2909.97.2.334
- **CINAR_VIECHTBAUER2022** — Cinar, O., & Viechtbauer, W. (2022). The poolr package for combining independent and dependent p values. Journal of Statistical Software, 101(1), 1-42. https://doi.org/10.18637/jss.v101.i01
- **WECO1956** — Western Electric Company (1956). Statistical Quality Control Handbook. Indianapolis: Western Electric Co. https://search.worldcat.org/title/Statistical-quality-control-handbook/oclc/33858387
- **NIST_WECO** — NIST/SEMATECH e-Handbook of Statistical Methods, Bölüm 6.3.2: What are Variables Control Charts? (WECO kuralları). https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm
- **FINK1986** — Fink, S. (1986). Crisis Management: Planning for the Inevitable. New York: AMACOM. https://www.kirkusreviews.com/book-reviews/a/steven-fink/crisis-management-planning-for-the-inevitable/
- **FISHER_P05** — Fisher'ın %5 anlamlılık uzlaşımı; bkz. Amrhein, Korner-Nievergelt & Roth (2017). The earth is flat (p > 0.05). PeerJ, 5, e3544 (Fisher 1937, s.15 alıntısı). https://pmc.ncbi.nlm.nih.gov/articles/PMC5502092/
- **WMO2023** — World Meteorological Organization (2023). Guidelines on the Definition and Characterization of Extreme Weather and Climate Events (WMO-No. 1310). https://library.wmo.int/records/item/58396-guidelines-onthe-definition-and-characterization-of-extreme-weather-and-climate-events
- **THAYER2025** — Thayer, M. B., et al. (2025). Dengue alert thresholds. BMJ Open, 15, e106182. https://doi.org/10.1136/bmjopen-2025-106182
- **PHIPSON_SMYTH2010** — Phipson, B., & Smyth, G. K. (2010). Permutation p-values should never be zero: Calculating exact p-values when permutations are randomly drawn. Statistical Applications in Genetics and Molecular Biology, 9(1), Article 39. https://arxiv.org/abs/1603.05766
- **CLOPPER_PEARSON1934** — Clopper, C. J., & Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika, 26(4), 404-413. https://doi.org/10.1093/biomet/26.4.404
- **FAWCETT2006** — Fawcett, T. (2006). An introduction to ROC analysis. Pattern Recognition Letters, 27(8), 861-874. https://doi.org/10.1016/j.patrec.2005.10.010
- **LAURER2024** — Laurer, M., van Atteveldt, W., Casas, A., & Welbers, K. (2024). Less annotating, more classifying: Addressing the data scarcity issue of supervised machine learning with deep transfer learning and BERT-NLI. Political Analysis, 32, 84-100. https://doi.org/10.1017/pan.2023.20
