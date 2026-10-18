"""
"L-PTİ İtibar Skoru Hesaplama Raporu" (Literatür-Temelli Paydaş İtibar Endeksi) kataloğu.

Kaynak kimlikleri raporun numaralı kaynakçasına eşlenir (yorumda [n]). Raporun 1. ve 35.
kaynakları (FOMBRUN2000, COOMBS2007) ERKİS v4 kaynakçasında zaten vardır; burada tekrar tanımlanmaz.
URL'ler raporun kaynakçasından alınmıştır (PDF satır sonlarında bölünmüş bağlantılar birleştirilmiştir).
"""
from __future__ import annotations

LPTI_KAYNAKLARI: dict[str, dict[str, str]] = {
    "PONZI2011": {"atif": "[2] Ponzi, L. J., Fombrun, C. J., & Gardberg, N. A. (2011). RepTrak Pulse: Conceptualizing and validating a short-form measure of corporate reputation. Corporate Reputation Review, 14(1), 15-35.", "url": "https://doi.org/10.1057/crr.2011.5"},
    "FOMBRUN2015": {"atif": "[3] Fombrun, C. J., Ponzi, L. J., & Newburry, W. (2015). Stakeholder tracking and analysis: The RepTrak System for measuring corporate reputation. Corporate Reputation Review, 18(1), 3-24.", "url": "https://cdn2.hubspot.net/hubfs/2963875/Reputation_Institute_Jun2017/pdf/stakeholdertrackingandanalysis_crr_issue_18-1.pdf"},
    "WALKER2010": {"atif": "[4] Walker, K. (2010). A systematic review of the corporate reputation literature: Definition, measurement, and theory. Corporate Reputation Review, 12(4), 357-387.", "url": "https://doi.org/10.1057/crr.2009.26"},
    "BIGUS2024": {"atif": "[5] Bigus, J. vd. (2024). Definitions and measures of corporate reputation in accounting and management: Commonalities, differences, and future research. Accounting and Business Research, 54(3), 304-336.", "url": "https://www.tandfonline.com/doi/full/10.1080/00014788.2022.2149458"},
    "MOLAVI_ZHANG2025": {"atif": "[6] Molavi & Zhang (2025). AI-driven corporate reputation measurement in digital ecosystems: A systematic literature review. Acta Psychologica, 261, 105846. (Yazar adları erişilen sayfada tam verilmediğinden kısaltılmıştır.)", "url": "https://research.manchester.ac.uk/en/publications/ai-driven-corporate-reputation-measurement-in-digital-ecosystems-/"},
    "ALLOZA2021": {"atif": "[7] Alloza-Losana, Á., & Carreras-Romero, E. (2021). Invariance of the Reputation Emotional Index RepTrak Pulse: A study validation on generational change. Corporate Reputation Review, 24(3), 143-157.", "url": "https://ideas.repec.org/a/pal/crepre/v24y2021i3d10.1057_s41299-020-00099-w.html"},
    "REPTRAK2026": {"atif": "[8] RepTrak (2026). Measuring what happens between coverage and commerce (yöntem açıklaması, kurumsal blog; hakemli değildir).", "url": "https://www.reptrak.com/blog/measuring-what-happens-between-coverage-and-commerce/"},
    "SCHWAIGER2004": {"atif": "[9] Schwaiger, M. (2004). Components and parameters of corporate reputation — An empirical study. Schmalenbach Business Review, 56, 46-71.", "url": "https://doi.org/10.1007/BF03396685"},
    "HITZ2025": {"atif": "[10] Hitz, N., Schwaiger, M., & Gabel, J. (2025). How to measure and manage country reputation. International Journal of Advertising, 44(6), 1066-1096.", "url": "https://www.tandfonline.com/doi/full/10.1080/02650487.2024.2411670"},
    "WALSH_BEATTY2007": {"atif": "[11] Walsh, G., & Beatty, S. E. (2007). Customer-based corporate reputation of a service firm: Scale development and validation. Journal of the Academy of Marketing Science, 35(1), 127-143.", "url": "https://strathprints.strath.ac.uk/9215/"},
    "WALSH2009": {"atif": "[12] Walsh, G., Beatty, S. E., & Shiu, E. M. K. (2009). The customer-based corporate reputation scale: Replication and short form. Journal of Business Research, 62(10), 924-930.", "url": "https://www.sciencedirect.com/science/article/abs/pii/S0148296308002385"},
    "ERGUN2021": {"atif": "[13] Ergun, M. (2021). Adaptation of Reputation Tracker Corporate Reputation Measurement Tool (RepTrak) to Turkish: Validity and reliability study. International Online Journal of Educational Sciences, 13(1), 33-52.", "url": "https://toad.halileksi.net/wp-content/uploads/2022/07/reputation-tracker-corporate-reputation-measurement-tool-toad.pdf"},
    "KOC_CIMEN2025": {"atif": "[14] Koç, A. F., & Çimen, Z. (2025). The Turkish adaptation of the customer-based corporate reputation scale: A study on validity and reliability in the case of fitness centers. Journal of ROL Sport Sciences, 6(4), 846-864.", "url": "https://rrpubs.com/index.php/rol/article/view/2115"},
    "YILMAZ2025": {"atif": "[15] Yılmaz, F. (2025). İç paydaşlarda kurumsal itibar algısının ölçümünde RepTrak yöntemi ve Reputation Quotient (RQ) yöntemi karşılaştırması (Yüksek lisans tezi, Zonguldak Bülent Ecevit Üniversitesi, Tez No. 925445).", "url": "https://tezara.org/theses/925445"},
    "ITC2018": {"atif": "[16] International Test Commission (2018). ITC guidelines for translating and adapting tests (2nd ed.). International Journal of Testing, 18(2), 101-134.", "url": "https://eric.ed.gov/?id=EJ1175982"},
    "CHURCHILL1979": {"atif": "[17] Churchill, G. A. (1979). A paradigm for developing better measures of marketing constructs. Journal of Marketing Research, 16(1), 64-73.", "url": "https://journals.sagepub.com/doi/10.1177/002224377901600110"},
    "BOATENG2018": {"atif": "[18] Boateng, G. O., Neilands, T. B., Frongillo, E. A., Melgar-Quiñonez, H. R., & Young, S. L. (2018). Best practices for developing and validating scales for health, social, and behavioral research: A primer. Frontiers in Public Health, 6, 149.", "url": "https://doi.org/10.3389/fpubh.2018.00149"},
    "ANDERSON_GERBING1988": {"atif": "[19] Anderson, J. C., & Gerbing, D. W. (1988). Structural equation modeling in practice: A review and recommended two-step approach. Psychological Bulletin, 103(3), 411-423.", "url": "https://aboomsma.webhosting.rug.nl/csadata/anderson_gerbing_1988.pdf"},
    "COHEN1999": {"atif": "[20] Cohen, P., Cohen, J., Aiken, L. S., & West, S. G. (1999). The problem of units and the circumstance for POMP. Multivariate Behavioral Research, 34(3), 315-346.", "url": "https://eric.ed.gov/?id=EJ602641"},
    "MOELLER2015": {"atif": "[21] Moeller, J. (2015). A word on standardization in longitudinal studies: Don't. Frontiers in Psychology, 6, 1389.", "url": "https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.01389/full"},
    "WETZELHUTTER2020": {"atif": "[22] Wetzelhütter, D. (2020). Scale-sensitive response behavior!? Consequences of offering versus omitting a “don't know” option and/or a middle category. Survey Practice, 13(1).", "url": "https://www.surveypractice.org/article/14484-scale-sensitive-response-behavior-consequences-of-offering-versus-omitting-a-don-t-know-option-and-or-a-middle-category"},
    "MAZZA2015": {"atif": "[23] Mazza, G. L., Enders, C. K., & Ruehlman, L. S. (2015). Addressing item-level missing data: A comparison of proration and full information maximum likelihood estimation. Multivariate Behavioral Research, 50, 504-519.", "url": "https://asu.elsevierpure.com/en/publications/addressing-item-level-missing-data-a-comparison-of-proration-and-/"},
    "VALLIANT2018": {"atif": "[24] Valliant, R., Dever, J. A., & Kreuter, F. (2018). Practical tools for designing and weighting survey samples (2nd ed.). Springer. (Kish tasarım etkisi ve etkin örneklem için PracTools vinyeti.)", "url": "https://stat.ethz.ch/CRAN/web/packages/PracTools/vignettes/Design-effects.html"},
    "LUMLEY2004": {"atif": "[25] Lumley, T. (2004). Analysis of complex survey samples. Journal of Statistical Software, 9(8).", "url": "https://www.jstatsoft.org/article/view/v009i08"},
    "MERCER2018": {"atif": "[26] Mercer, A., Lau, A., & Kennedy, C. (2018). For weighting online opt-in samples, what matters most? Pew Research Center.", "url": "https://www.pewresearch.org/methods/2018/01/26/for-weighting-online-opt-in-samples-what-matters-most/"},
    "BRAUER2023": {"atif": "[27] Brauer, K., Ranger, J., & Ziegler, M. (2023). Confirmatory factor analyses in psychological test adaptation and development: A nontechnical discussion of the WLSMV estimator. Psychological Test Adaptation and Development, 4(1).", "url": "https://econtent.hogrefe.com/doi/10.1027/2698-1866/a000034"},
    "MCNEISH_WOLF2023": {"atif": "[28] McNeish, D., & Wolf, M. G. (2023). Dynamic fit index cutoffs for confirmatory factor analysis models. Psychological Methods, 28(1), 61-88.", "url": "https://pubmed.ncbi.nlm.nih.gov/34694832/"},
    "MCNEISH2024": {"atif": "[29] McNeish, D. (2024). Dynamic fit index cutoffs for factor analysis with Likert-type, ordinal, or binary responses. American Psychologist, 79(9), 1061-1075.", "url": "https://files.eric.ed.gov/fulltext/ED640042.pdf"},
    "FLORA2020": {"atif": "[30] Flora, D. B. (2020). Your coefficient alpha is probably wrong, but which coefficient omega is right? A tutorial on using R to obtain better reliability estimates. Advances in Methods and Practices in Psychological Science, 3(4).", "url": "https://journals.sagepub.com/doi/10.1177/2515245920951747"},
    "MCNEISH2018": {"atif": "[31] McNeish, D. (2018). Thanks coefficient alpha, we'll take it from here. Psychological Methods, 23(3), 412-433.", "url": "https://doi.org/10.1037/met0000144"},
    "PUTNICK2016": {"atif": "[32] Putnick, D. L., & Bornstein, M. H. (2016). Measurement invariance conventions and reporting: The state of the art and future directions for psychological research. Developmental Review, 41, 71-90.", "url": "https://www.sciencedirect.com/science/article/abs/pii/S0273229716300351"},
    "LEITGOB2023": {"atif": "[33] Leitgöb, H., Seddig, D., Asparouhov, T., Behr, D., Davidov, E., De Roover, K., Jak, S., Meitinger, K., Menold, N., Muthén, B., Rudnev, M., Schmidt, P., & van de Schoot, R. (2023). Measurement invariance in the social sciences: Historical development, methodological challenges, state of the art, and future perspectives. Social Science Research, 110, 102805.", "url": "https://ppw.kuleuven.be/okp/_pdf/Leitgoeb2023MIITS.pdf"},
    "MOSHAGEN_BADER2024": {"atif": "[34] Moshagen, M., & Bader, M. (2024). semPower: General power analysis for structural equation models. Behavior Research Methods, 56(4), 2901-2922.", "url": "https://pubmed.ncbi.nlm.nih.gov/37950114/"},
    "MA_ZHAN2016": {"atif": "[36] Ma, L., & Zhan, M. (2016). Effects of attributed responsibility and response strategies on organizational reputation: A meta-analysis of situational crisis communication theory research. Journal of Public Relations Research, 28(2), 102-119.", "url": "https://www.tandfonline.com/doi/full/10.1080/1062726X.2016.1166367"},
}

# Raporun Bölüm 12 tablosu (K1–K7) + uygulamada eklenen kararlar (K8–K12)
LPTI_KARARLARI: list[dict] = [
    {"kod": "K1", "kaynak": "rapor", "baslik": "Aşinalık eşiği", "varsayilan": "Ön kayıtta tanımlanır",
     "aciklama": "Hangi aşinalık düzeyinin yeterli sayılacağı için literatürde evrensel bir sayı yoktur. Eşik ön kayıtta tanımlanır; dışlanan katılımcı sayısı ve oranı her dalgada raporlanır. Uygulama: dalga başına 'aşinalık eşiği' saklanır ve katılımcı verisindeki familiarity_eligible bayrağı bu eşikten türetilir.", "kaynaklar": ["REPTRAK2026", "WETZELHUTTER2020"]},
    {"kod": "K2", "kaynak": "rapor", "baslik": "Asgari geçerli madde sayısı m", "varsayilan": "3 (Pulse için)",
     "aciklama": "Dört maddeli Pulse için varsayılan m = 3 (en fazla bir eksik madde). Literatürden gelmez; ön kayıtta sabitlenir ve m = 4 (liste bazında silme) ile duyarlılık analizi yapılır; doğrulama aşamasında FIML önerilir.", "kaynaklar": ["MAZZA2015"]},
    {"kod": "K3", "kaynak": "rapor", "baslik": "Asgari hassasiyet (hedef GA yarı genişliği E)", "varsayilan": "±5 puan",
     "aciklama": "n_eff ≥ (1,96·σ/E)²; gereken ham örneklem n ≈ n_eff · deff_Kish. E bir tasarım kararıdır ve ön kayıtta sabitlenir.", "kaynaklar": ["VALLIANT2018"]},
    {"kod": "K4", "kaynak": "rapor", "baslik": "Paydaş payları π_g", "varsayilan": "Tanımsız → overall_score = null",
     "aciklama": "Literatür paydaş gruplarının itibara katkısı için evrensel pay vermez. π_g yönetişim kararıdır, ön kayda alınır ve farklı π senaryolarıyla duyarlılık analizi raporlanır.", "kaynaklar": ["REPTRAK2026"]},
    {"kod": "K5", "kaynak": "rapor", "baslik": "L-PTİ → onceki_itibar eşlemesi", "varsayilan": "GA'nın 50'ye göre konumu",
     "aciklama": "%95 GA tamamen 50'nin üstündeyse olumlu; tamamen altındaysa olumsuz; 50'yi kapsıyorsa nötr. status ≠ ok ise ısınma dönemi (Janis–Fadner) yoluna dönülür. Alternatif referans noktalarıyla duyarlılık analizi yapılmalıdır.", "kaynaklar": ["COOMBS2007", "MA_ZHAN2016"]},
    {"kod": "K6", "kaynak": "rapor", "baslik": "Ağırlık değişkenleri ve kırpma (trimming)", "varsayilan": "Grup başına ön kayıt",
     "aciklama": "Ağırlık değişkenleri (yaş, cinsiyet, bölge, müşteri segmenti) her paydaş grubu için ön kayıtta tanımlanır. Değişken seçimi yöntem karmaşıklığından daha önemlidir (raking karmaşık yöntemlere çok yakın sonuç verir).", "kaynaklar": ["MERCER2018"]},
    {"kod": "K7", "kaynak": "rapor", "baslik": "Paydaş grubu listesi", "varsayilan": "5 varsayılan grup",
     "aciklama": "customers, employees, investors, suppliers_regulators, general_public; kurum türüne göre proje başında tanımlanır.", "kaynaklar": ["FOMBRUN2015"]},
    {"kod": "K8", "kaynak": "uygulama", "baslik": "Ölçek maddelerinin metni", "varsayilan": "Boş taslak",
     "aciklama": "RepTrak maddeleri ticari bir yönteme aittir (Rapor Bölüm 4.3). Sistem lisanslı madde metnini paketle dağıtmaz; kurum, lisans/uyarlama yolunu (A: Ergun 2021, B: Koç & Çimen 2025, C: yeni madde havuzu) izleyerek madde metnini kendisi girer. Demo aracı lisanslı değildir ve yalnızca sistemi göstermek içindir.", "kaynaklar": ["ERGUN2021", "KOC_CIMEN2025", "ITC2018"]},
    {"kod": "K9", "kaynak": "uygulama", "baslik": "Doğrulama kapısı", "varsayilan": "Zorunlu",
     "aciklama": "Rapor 'Formül ancak ölçüm aracı doğrulandıktan sonra status=ok üretir' der. Uygulama: araç sürümü için tek faktör CFA desteği kaydı (ve aynı puanlama özeti) yoksa ya da madde uçları/yönü değişmişse status = invalid_instrument, score = null. Pilot için doğrulama kapısı 'dogrulama_zorunlu=false' ile kapatılabilir; bu durum çalıştırma kaydında ve çıktıda 'validation_bypassed' olarak açıkça işaretlenir.", "kaynaklar": ["BRAUER2023", "MCNEISH_WOLF2023", "MCNEISH2024"]},
    {"kod": "K10", "kaynak": "uygulama", "baslik": "CFA, ω ve değişmezlik hesabının yeri", "varsayilan": "Harici (R/lavaan/Mplus) + uygulama içi yaklaşık ω",
     "aciklama": "WLSMV CFA, dinamik uyum kesimleri, kategorik ω (ω_u-cat, ω_ho) ve ölçüm değişmezliği uygulama içinde hesaplanmaz; harici analizle üretilip API ile kayda girilir. Uygulama içinde yalnızca eksik yanıt oranı ve Pearson korelasyonuna dayalı tek faktörlü yaklaşık ω hesaplanır (estimator='pearson_paf'); bu değer sıralı maddeler için kategorik ω'nun yerine geçmez.", "kaynaklar": ["FLORA2020", "MCNEISH2018", "PUTNICK2016", "LEITGOB2023"]},
    {"kod": "K11", "kaynak": "uygulama", "baslik": "Değişmezlik ve karşılaştırma", "varsayilan": "≥ skaler veya kısmi skaler",
     "aciklama": "Grup/dil/dalga karşılaştırması (Δ) yalnızca doğrulama kaydında invariance_level 'scalar', 'partial_scalar' ya da 'strict' ise üretilir; aksi halde karşılaştırma durumu 'invariance_not_established' olur ve grup içi skorlar yine verilir.", "kaynaklar": ["PUTNICK2016", "LEITGOB2023"]},
    {"kod": "K12", "kaynak": "uygulama", "baslik": "K5 etiketinde kaynak grup", "varsayilan": "Kurum geneli skor; yoksa en büyük n_eff'li ok grup",
     "aciklama": "K5 tek bir skor/GA ister. π_g tanımlı ve overall_score varsa kurum geneli skor ve GA'sı (V = Σπ_g²V_g) kullanılır; yoksa status='ok' olan gruplar arasında n_eff'i en büyük olan seçilir. Rapor bu seçimi belirtmez.", "kaynaklar": []},
    {"kod": "K13", "kaynak": "uygulama", "baslik": "Önceki itibar kaynak sıralaması", "varsayilan": "Kullanıcı > L-PTİ > ısınma Janis–Fadner",
     "aciklama": "Kurum profilinde açıkça 'olumlu/nötr/olumsuz' seçildiyse o kullanılır. 'Otomatik' ise en son geçerli (status=ok) L-PTİ skorundan K5 kuralıyla etiket üretilir; yoksa v4 raporundaki ısınma dönemi haber Janis–Fadner yoluna dönülür.", "kaynaklar": ["COOMBS2007", "DEEPHOUSE2000"]},
    {"kod": "K14", "kaynak": "uygulama", "baslik": "Ağırlık kırpma ve ham ağırlık", "varsayilan": "Kırpma yok",
     "aciklama": "final_weight boşsa tasarım × yanıtsızlık ağırlığı × (varsa) raking çarpanı olarak üretilir. Kırpma sınırları K6'ya göre grup başına parametredir; varsayılan kırpma yoktur.", "kaynaklar": ["MERCER2018"]},
]

LPTI_SINIRLILIKLARI: list[str] = [
    "L-PTİ anket verisi gerektirir; dalgalar arası sürede itibar değişimi gözlenemez. Bu boşluk ERKİS'in dijital söylem ve kriz katmanlarıyla izlenir, fakat bu katmanlar itibar skoru yerine geçmez.",
    "RepTrak madde metinleri lisanslı olabilir; ticari kullanımdan önce kullanım izni doğrulanmalıdır.",
    "Türkçe uyarlamalarda özgün boyut yapısı korunamamıştır (RepTrak 7 → 5, CBR 5 → 3); kurumun kendi sektöründe yeniden doğrulama gerekir.",
    "Denklem (6), tek aşamalı iadeli örnekleme yaklaşımıdır; karmaşık (tabakalı/kümeli) tasarımlarda tasarıma uygun varyans yordamı kullanılmalıdır.",
    "RepTrak 2026 metni hakemli değil, kurumsal yöntem açıklamasıdır; yalnızca güncel uygulamayı belgelemek için kullanılmıştır.",
    "Bölüm 6 ve 10.3'teki sayılar uydurma örnek veridir; sonuç değeri olarak kullanılamaz.",
    "WLSMV CFA, dinamik uyum kesimleri, kategorik ω ve ölçüm değişmezliği uygulama dışında hesaplanır (K10).",
]
