"""
ERKİS literatür kataloğu — sistemin TEK doğruluk kaynağı.

Bu dosya "ERKİS v4 — Literatüre Dayalı Kriz Göstergeleri ve Kriz Risk Endeksi
(KRE) Raporu" ile birebir eşleşir:
  * KAYNAKLAR: Rapor Bölüm 10 kaynakçası (kimlik, tam atıf, URL). Kod içindeki
    her yorumda geçen [KIMLIK] bu sözlükte tanımlıdır.
  * GOSTERGELER: Rapor Bölüm 2 (SEÇİLDİ G1–G13, KALİTE Q1, ÇERÇEVE C1–C4,
    ELENDİ E1–E18) — ölçüm, gerekçe ve kaynaklarıyla.
  * BOYUTLAR: Rapor Bölüm 2.1 sonu.
  * SABITLER: Rapor Bölüm 4.
  * TASARIM_KARARLARI: Rapor Bölüm 7 (literatürden gelmeyen kararlar, açık liste)
    ve v5'te eklenen kuruma özgü eşik katmanının kararları.
  * SINIRLILIKLAR: Rapor Bölüm 8.

v5 eki: "EK_KAYNAKLAR" bölümündeki kimlikler rapordan değil, kuruma özgü
eşik/değerlendirme katmanından gelir (app/detection/kurum_esik.py). Bunlar
raporun formülünü DEĞİŞTİRMEZ; KRE ve WECO kararının yanında raporlanan
ek istatistiklerin kaynaklarıdır.

dogrula_katalog() katalog tutarlılığını denetler (tests/test_literatur.py).
"""
from __future__ import annotations

import math

from app.katalog.esik import (ESIK_KARARLARI, ESIK_KAYNAKLARI, ESIK_PARAMETRELERI, ESIK_SINIRLILIKLARI)
from app.katalog.lpti import LPTI_KARARLARI, LPTI_KAYNAKLARI, LPTI_SINIRLILIKLARI
from app.katalog.pr import PR_KARARLARI, PR_KAYNAKLARI

# ---------------------------------------------------------------------------
# 1) KAYNAKLAR — Rapor Bölüm 10 (birebir)
# ---------------------------------------------------------------------------
KAYNAKLAR: dict[str, dict[str, str]] = {
    "ARPAN2005": {"atif": "Arpan, L. M., & Roskos-Ewoldsen, D. R. (2005). Stealing thunder: Analysis of the effects of proactive disclosure of crisis information. Public Relations Review, 31(3), 425-433.", "url": "https://www.sciencedirect.com/science/article/pii/S0363811105000809"},
    "BENOIT1997": {"atif": "Benoit, W. L. (1997). Image repair discourse and crisis communication. Public Relations Review, 23(2), 177-186.", "url": "https://eric.ed.gov/?id=EJ547153"},
    "BERGER_MILKMAN2012": {"atif": "Berger, J., & Milkman, K. L. (2012). What makes online content viral? Journal of Marketing Research, 49(2), 192-205.", "url": "https://doi.org/10.1509/jmr.10.0353"},
    "BLEI2003": {"atif": "Blei, D. M., Ng, A. Y., & Jordan, M. I. (2003). Latent Dirichlet allocation. Journal of Machine Learning Research, 3, 993-1022.", "url": "https://www.jmlr.org/papers/v3/blei03a.html"},
    "CAN2008": {"atif": "Can, F., Kocberber, S., Balcik, E., Kaynak, C., Ocalan, H. C., & Vursavas, O. M. (2008). Information retrieval on Turkish texts. JASIST, 59(3), 407-421. (F5: ilk 5 karakterle kesme)", "url": "https://repository.bilkent.edu.tr/server/api/core/bitstreams/d108cb89-6abe-4dd8-856e-2540b8f0717d/content"},
    "CARROLL_MCCOMBS2003": {"atif": "Carroll, C. E., & McCombs, M. (2003). Agenda-setting effects of business news on the public's images and opinions about major corporations. Corporate Reputation Review, 6(1), 36-46.", "url": "https://www.semanticscholar.org/paper/Agenda-setting-Effects-of-Business-News-on-the-and-Carroll-McCombs/7ebd7af884b1035c6eba568450a2043ed874289a"},
    "CASTILLO2011": {"atif": "Castillo, C., Mendoza, M., & Poblete, B. (2011). Information credibility on Twitter. Proceedings of WWW 2011, 675-684.", "url": "https://chato.cl/papers/castillo_mendoza_poblete_2010_twitter_credibility.pdf"},
    "CATALDI2010": {"atif": "Cataldi, M., Di Caro, L., & Schifanella, C. (2010). Emerging topic detection on Twitter based on temporal and social terms evaluation. Proceedings of MDMKDD '10, Article 4.", "url": "https://dl.acm.org/doi/10.1145/1814245.1814249"},
    "CHA2010": {"atif": "Cha, M., Haddadi, H., Benevenuto, F., & Gummadi, K. P. (2010). Measuring user influence in Twitter: The million follower fallacy. Proceedings of ICWSM 2010.", "url": "https://aaai.org/papers/00010-14033-measuring-user-influence-in-twitter-the-million-follower-fallacy/"},
    "CHOI_VARIAN2012": {"atif": "Choi, H., & Varian, H. (2012). Predicting the present with Google Trends. Economic Record, 88(s1), 2-9.", "url": "https://doi.org/10.1111/j.1475-4932.2012.00809.x"},
    "CJR2023": {"atif": "Columbia Journalism Review, Tow Center (2023). Q&A: What happened to academic research on Twitter? (Botometer'in X API kapanmasıyla işlevsiz kaldığı).", "url": "https://www.cjr.org/tow_center/qa-what-happened-to-academic-research-on-twitter.php"},
    "COOMBS2007": {"atif": "Coombs, W. T. (2007). Protecting organization reputations during a crisis: The development and application of Situational Crisis Communication Theory. Corporate Reputation Review, 10(3), 163-176.", "url": "https://doi.org/10.1057/palgrave.crr.1550049"},
    "COOMBS_HOLLADAY2002": {"atif": "Coombs, W. T., & Holladay, S. J. (2002). Helping crisis managers protect reputational assets: Initial tests of the Situational Crisis Communication Theory. Management Communication Quarterly, 16(2), 165-186.", "url": "https://doi.org/10.1177/089331802237233"},
    "COOMBS_HOLLADAY2007": {"atif": "Coombs, W. T., & Holladay, S. J. (2007). The negative communication dynamic: Exploring the impact of stakeholder affect on behavioral intentions. Journal of Communication Management, 11(4), 300-312.", "url": "https://doi.org/10.1108/13632540710843913"},
    "COOMBS_HOLLADAY2012": {"atif": "Coombs, W. T., & Holladay, S. J. (2012). The paracrisis: The challenges created by publicly managing crisis prevention. Public Relations Review, 38(3), 408-415.", "url": "https://www.sciencedirect.com/science/article/abs/pii/S0363811112000689"},
    "COUSINS2007": {"atif": "Cousins, R. D. (2007). Annotated bibliography of some papers on combining significances or p-values. arXiv:0705.2209. (Stouffer ve ağırlıklı Stouffer formülleri)", "url": "https://arxiv.org/abs/0705.2209"},
    "CROCKETT2017": {"atif": "Crockett, M. J. (2017). Moral outrage in the digital age. Nature Human Behaviour, 1, 769-771.", "url": "https://doi.org/10.1038/s41562-017-0213-3"},
    "DEEPHOUSE2000": {"atif": "Deephouse, D. L. (2000). Media reputation as a strategic resource: An integration of mass communication and resource-based theories. Journal of Management, 26(6), 1091-1112.", "url": "https://doi.org/10.1177/014920630002600602"},
    "DOWNS1972": {"atif": "Downs, A. (1972). Up and down with ecology: The 'issue-attention cycle'. The Public Interest, 28, 38-50.", "url": "https://fbaum.unc.edu/teaching/articles/Downs_Public_Interest_1972.pdf"},
    "FINK1986": {"atif": "Fink, S. (1986). Crisis Management: Planning for the Inevitable. New York: AMACOM.", "url": "https://www.kirkusreviews.com/book-reviews/a/steven-fink/crisis-management-planning-for-the-inevitable/"},
    "FISHER_P05": {"atif": "Fisher'ın %5 anlamlılık uzlaşımı; bkz. Amrhein, Korner-Nievergelt & Roth (2017). The earth is flat (p > 0.05). PeerJ, 5, e3544 (Fisher 1937, s.15 alıntısı).", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5502092/"},
    "FOMBRUN2000": {"atif": "Fombrun, C. J., Gardberg, N. A., & Sever, J. M. (2000). The Reputation Quotient: A multi-stakeholder measure of corporate reputation. Journal of Brand Management, 7(4), 241-255.", "url": "https://doi.org/10.1057/bm.2000.10"},
    "GEARY1935": {"atif": "Geary, R. C. (1935). The ratio of the mean deviation to the standard deviation as a test of normality. Biometrika, 27(3-4), 310-332. (Normal dağılımda OMS/SS = sqrt(2/pi))", "url": "https://doi.org/10.1093/biomet/27.3-4.310"},
    "GINSBERG2009": {"atif": "Ginsberg, J., Mohebbi, M. H., Patel, R. S., et al. (2009). Detecting influenza epidemics using search engine query data. Nature, 457, 1012-1014.", "url": "https://doi.org/10.1038/nature07634"},
    "GOEL2016": {"atif": "Goel, S., Anderson, A., Hofman, J., & Watts, D. J. (2016). The structural virality of online diffusion. Management Science, 62(1), 180-196.", "url": "https://ideas.repec.org/a/inm/ormnsc/v62y2016i1p180-196.html"},
    "GOKSEL_KERSLAKE2005": {"atif": "Göksel, A., & Kerslake, C. (2005). Turkish: A Comprehensive Grammar. London: Routledge. ('değil' ve 'yok' olumsuzluk işaretleri)", "url": "https://www.routledge.com/Turkish-A-Comprehensive-Grammar/Goksel-Kerslake/p/book/9781138350533"},
    "GTRENDS_API_DOC": {"atif": "Google Search Central Blog (24 Temmuz 2025). Introducing the Google Trends API (alpha).", "url": "https://developers.google.com/search/blog/2025/07/trends-api"},
    "HANSEN2011": {"atif": "Hansen, L. K., Arvidsson, A., Nielsen, F. Å., Colleoni, E., & Etter, M. (2011). Good friends, bad news: Affect and virality in Twitter. In Future Information Technology (CCIS 185, pp. 34-43). Springer.", "url": "https://arxiv.org/abs/1101.0510"},
    "HARDER2017": {"atif": "Harder, R. A., Sevenans, J., & Van Aelst, P. (2017). Intermedia agenda setting in the social media age: How traditional players dominate the news agenda in election times. The International Journal of Press/Politics, 22(3), 275-293.", "url": "https://doi.org/10.1177/1940161217704969"},
    "HERHAUSEN2019": {"atif": "Herhausen, D., Ludwig, S., Grewal, D., Wulf, J., & Schoegel, M. (2019). Detecting, preventing, and mitigating online firestorms in brand communities. Journal of Marketing, 83(3), 1-21.", "url": "https://doi.org/10.1177/0022242918822300"},
    "JACOBSON1988": {"atif": "Jacobson, V. (1988). Congestion avoidance and control. ACM SIGCOMM Computer Communication Review, 18(4), 314-329.", "url": "https://doi.org/10.1145/52324.52356"},
    "JANIS_FADNER1965": {"atif": "Janis, I. L., & Fadner, R. H. (1965). The coefficient of imbalance. In H. D. Lasswell, N. Leites et al. (Eds.), Language of Politics: Studies in Quantitative Semantics. Cambridge, MA: MIT Press. (Deephouse, 2000 aracılığıyla uygulanmıştır.)", "url": "https://study.sagepub.com/sites/default/files/3 Deephouse.pdf"},
    "JIN2012": {"atif": "Jin, Y., Pang, A., & Cameron, G. T. (2012). Toward a publics-driven, emotion-based conceptualization in crisis communication: Unearthing dominant emotions in multi-staged testing of the Integrated Crisis Mapping (ICM) model. Journal of Public Relations Research, 24(3), 266-298.", "url": "https://doi.org/10.1080/1062726X.2012.676747"},
    "JOHNEN2018": {"atif": "Johnen, M., Jungblut, M., & Ziegele, M. (2018). The digital outcry: What incites participation behavior in an online firestorm? New Media & Society, 20(9), 3140-3160.", "url": "https://doi.org/10.1177/1461444817741883"},
    "KASPERSON1988": {"atif": "Kasperson, R. E., Renn, O., Slovic, P., et al. (1988). The social amplification of risk: A conceptual framework. Risk Analysis, 8(2), 177-187.", "url": "https://doi.org/10.1111/j.1539-6924.1988.tb01168.x"},
    "KLEIN2004": {"atif": "Klein, J. G., Smith, N. C., & John, A. (2004). Why we boycott: Consumer motivations for boycott participation. Journal of Marketing, 68(3), 92-109.", "url": "https://doi.org/10.1509/jmkg.68.3.92.34770"},
    "KLEINBERG2003": {"atif": "Kleinberg, J. (2003). Bursty and hierarchical structure in streams. Data Mining and Knowledge Discovery, 7(4), 373-397 (KDD 2002 bildirisi).", "url": "https://www.cs.cornell.edu/home/kleinber/bhs.pdf"},
    "LAURER2024": {"atif": "Laurer, M., van Atteveldt, W., Casas, A., & Welbers, K. (2024). Less annotating, more classifying: Addressing the data scarcity issue of supervised machine learning with deep transfer learning and BERT-NLI. Political Analysis, 32, 84-100.", "url": "https://doi.org/10.1017/pan.2023.20"},
    "LAZER2014": {"atif": "Lazer, D., Kennedy, R., King, G., & Vespignani, A. (2014). The parable of Google Flu: Traps in big data analysis. Science, 343(6176), 1203-1205.", "url": "https://doi.org/10.1126/science.1248506"},
    "MACKINLAY1997": {"atif": "MacKinlay, A. C. (1997). Event studies in economics and finance. Journal of Economic Literature, 35(1), 13-39.", "url": "https://econpapers.repec.org/article/aeajeclit/v_3a35_3ay_3a1997_3ai_3a1_3ap_3a13-39.htm"},
    "MARCUS2011": {"atif": "Marcus, A., Bernstein, M. S., Badar, O., Karger, D. R., Madden, S., & Miller, R. C. (2011). TwitInfo: Aggregating and visualizing microblogs for event exploration. Proceedings of CHI 2011, 227-236.", "url": "https://dspace.mit.edu/handle/1721.1/72370"},
    "MAYNARD2014": {"atif": "Maynard, D., & Greenwood, M. A. (2014). Who cares about sarcastic tweets? Investigating the impact of sarcasm on sentiment analysis. Proceedings of LREC 2014.", "url": "https://aclanthology.org/L14-1527/"},
    "MCCOMBS_SHAW1972": {"atif": "McCombs, M. E., & Shaw, D. L. (1972). The agenda-setting function of mass media. Public Opinion Quarterly, 36(2), 176-187.", "url": "https://doi.org/10.1086/267990"},
    "MITCHELL1997": {"atif": "Mitchell, R. K., Agle, B. R., & Wood, D. J. (1997). Toward a theory of stakeholder identification and salience. Academy of Management Review, 22(4), 853-886.", "url": "https://journals.aom.org/doi/10.5465/amr.1997.9711022105"},
    "MOHAMMAD_TURNEY2013": {"atif": "Mohammad, S. M., & Turney, P. D. (2013). Crowdsourcing a word-emotion association lexicon. Computational Intelligence, 29(3), 436-465. (NRC EmoLex; Türkçe çeviri dosyası dahil)", "url": "https://arxiv.org/abs/1308.6297"},
    "NAJAFI_VAROL2024": {"atif": "Najafi, A., & Varol, O. (2024). TurkishBERTweet: Fast and reliable large language model for social media analysis. Expert Systems with Applications, 255, 124737.", "url": "https://huggingface.co/VRLLab/TurkishBERTweet"},
    "NIST_WECO": {"atif": "NIST/SEMATECH e-Handbook of Statistical Methods, Bölüm 6.3.2: What are Variables Control Charts? (WECO kuralları).", "url": "https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm"},
    "NRC_EMOLEX": {"atif": "National Research Council Canada. NRC Word-Emotion Association Lexicon (EmoLex) - araştırma amaçlı ücretsiz, ticari kullanım lisanslı.", "url": "https://nrc.canada.ca/en/research-development/products-services/technical-advisory-services/sentiment-emotion-lexicons"},
    "OECD2008": {"atif": "OECD & European Commission JRC (2008). Handbook on Constructing Composite Indicators: Methodology and User Guide. Paris: OECD Publishing.", "url": "https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf"},
    "OLTEANU2014": {"atif": "Olteanu, A., Castillo, C., Diaz, F., & Vieweg, S. (2014). CrisisLex: A lexicon for collecting and filtering microblogged communications in crises. Proceedings of ICWSM 2014.", "url": "https://chato.cl/papers/olteanu_castillo_diaz_vieweg_2014_crisis_lexicon_disasters_twitter.pdf"},
    "PACHECO2021": {"atif": "Pacheco, D., Hui, P.-M., Torres-Lugo, C., Truong, B. T., Flammini, A., & Menczer, F. (2021). Uncovering coordinated networks on social media: Methods and case studies. Proceedings of ICWSM 2021.", "url": "https://arxiv.org/abs/2001.05658"},
    "PANG_LEE2008": {"atif": "Pang, B., & Lee, L. (2008). Opinion mining and sentiment analysis. Foundations and Trends in Information Retrieval, 2(1-2), 1-135.", "url": "https://www.cs.cornell.edu/home/llee/opinion-mining-sentiment-analysis-survey.html"},
    "PEARSON_MITROFF1993": {"atif": "Pearson, C. M., & Mitroff, I. I. (1993). From crisis prone to crisis prepared: A framework for crisis management. Academy of Management Executive, 7(1), 48-59.", "url": "https://journals.aom.org/doi/10.5465/ame.1993.9409142058"},
    "PFEFFER2014": {"atif": "Pfeffer, J., Zorbach, T., & Carley, K. M. (2014). Understanding online firestorms: Negative word-of-mouth dynamics in social media networks. Journal of Marketing Communications, 20(1-2), 117-128.", "url": "https://doi.org/10.1080/13527266.2013.797778"},
    "PONTIKI2014": {"atif": "Pontiki, M., et al. (2014). SemEval-2014 Task 4: Aspect based sentiment analysis. Proceedings of SemEval 2014.", "url": "https://aclanthology.org/S14-2004/"},
    "PYTRENDS_DOC": {"atif": "GeneralMills/pytrends - Pseudo API for Google Trends (17 Nisan 2025'te arşivlendi).", "url": "https://github.com/GeneralMills/pytrends"},
    "REDDIT_API_DOC": {"atif": "Reddit Help. Reddit Data API Wiki (OAuth zorunlu; 100 QPM; User-Agent biçimi).", "url": "https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki"},
    "RFC6298": {"atif": "Paxson, V., Allman, M., Chu, J., & Sargent, M. (2011). RFC 6298: Computing TCP's Retransmission Timer (RFC 2988'in güncel sürümü; TwitInfo RFC 2988'e atıf yapar).", "url": "https://www.rfc-editor.org/rfc/rfc6298"},
    "ROBERTS1959": {"atif": "Roberts, S. W. (1959). Control chart tests based on geometric moving averages. Technometrics, 1(3), 239-250.", "url": "https://doi.org/10.1080/00401706.1959.10489860"},
    "ROST2016": {"atif": "Rost, K., Stahel, L., & Frey, B. S. (2016). Digital social norm enforcement: Online firestorms in social media. PLoS ONE, 11(6), e0155923.", "url": "https://doi.org/10.1371/journal.pone.0155923"},
    "SAKAKI2010": {"atif": "Sakaki, T., Okazaki, M., & Matsuo, Y. (2010). Earthquake shakes Twitter users: Real-time event detection by social sensors. Proceedings of WWW 2010, 851-860.", "url": "https://dl.acm.org/doi/10.1145/1772690.1772777"},
    "SCHULTZ2011": {"atif": "Schultz, F., Utz, S., & Göritz, A. (2011). Is the medium the message? Perceptions of and reactions to crisis communication via Twitter, blogs and traditional media. Public Relations Review, 37(1), 20-27.", "url": "https://opus.bibliothek.uni-augsburg.de/opus4/frontdoor/index/index/docId/97403"},
    "SCHWETER2020": {"atif": "Schweter, S. (2020). BERTurk - BERT models for Turkish (v1.0.0). Zenodo.", "url": "https://zenodo.org/records/3770924"},
    "SHEWHART1931": {"atif": "Shewhart, W. A. (1931). Economic Control of Quality of Manufactured Product. New York: Van Nostrand. (3-sigma kontrol sınırları)", "url": "https://www.iise.org/uploadedfiles/IIE/Education/Six_Sigma_Green_Belt_Transition/Shewhart and Variation.pdf"},
    "SHUYO2010": {"atif": "Shuyo, N. (2010). Language Detection Library for Java; Python portu: langdetect.", "url": "https://pypi.org/project/langdetect/"},
    "SLOAN_MORGAN2015": {"atif": "Sloan, L., & Morgan, J. (2015). Who tweets with their location? Understanding the relationship between demographic characteristics and the use of geoservices and geotagging on Twitter. PLoS ONE, 10(11), e0142209.", "url": "https://doi.org/10.1371/journal.pone.0142209"},
    "STIEGLITZ2013": {"atif": "Stieglitz, S., & Dang-Xuan, L. (2013). Emotions and information diffusion in social media: Sentiment of microblogs and sharing behavior. Journal of Management Information Systems, 29(4), 217-248.", "url": "https://doi.org/10.2753/MIS0742-1222290408"},
    "THELWALL2011": {"atif": "Thelwall, M., Buckley, K., & Paltoglou, G. (2011). Sentiment in Twitter events. Journal of the American Society for Information Science and Technology, 62(2), 406-418.", "url": "https://doi.org/10.1002/asi.21462"},
    "TOCOGLU2019": {"atif": "Toçoğlu, M. A., & Alpkoçak, A. (2019). Lexicon-based emotion analysis in Turkish. Turkish Journal of Electrical Engineering and Computer Sciences, 27(2), Article 40.", "url": "https://journals.tubitak.gov.tr/cgi/viewcontent.cgi?article=1717&context=elektrik"},
    "TREMO2018": {"atif": "Toçoğlu, M. A., & Alpkoçak, A. (2018). TREMO: A dataset for emotion analysis in Turkish. Journal of Information Science, 44(6).", "url": "https://doi.org/10.1177/0165551518761014"},
    "VAROL2017": {"atif": "Varol, O., Ferrara, E., Davis, C. A., Menczer, F., & Flammini, A. (2017). Online human-bot interactions: Detection, estimation, and characterization. Proceedings of ICWSM 2017.", "url": "https://aaai.org/papers/00280-14871-online-human-bot-interactions-detection-estimation-and-characterization/"},
    "VOSOUGHI2018": {"atif": "Vosoughi, S., Roy, D., & Aral, S. (2018). The spread of true and false news online. Science, 359(6380), 1146-1151.", "url": "https://doi.org/10.1126/science.aap9559"},
    "WECO1956": {"atif": "Western Electric Company (1956). Statistical Quality Control Handbook. Indianapolis: Western Electric Co.", "url": "https://search.worldcat.org/title/Statistical-quality-control-handbook/oclc/33858387"},
    "WHITLOCK2005": {"atif": "Whitlock, M. C. (2005). Combining probability from independent tests: The weighted Z-method is superior to Fisher's approach. Journal of Evolutionary Biology, 18(5), 1368-1373. (Ağırlıklı Stouffer Z: Mosteller & Bush genellemesi)", "url": "https://doi.org/10.1111/j.1420-9101.2005.00917.x"},
    "X_PRICING_DOC": {"atif": "X Developer Platform. X API pay-per-usage pricing.", "url": "https://docs.x.com/x-api/getting-started/pricing"},
    "X_SEARCH_DOC": {"atif": "X Developer Platform. Search Posts Recent (GET /2/tweets/search/recent) - son 7 gün.", "url": "https://docs.x.com/x-api/posts/search-recent-posts"},
    "YAN2013": {"atif": "Yan, X., Guo, J., Lan, Y., & Cheng, X. (2013). A biterm topic model for short texts. Proceedings of WWW 2013.", "url": "https://jiafengguo.github.io/2013/2013-A Biterm Topic Model for Short Texts.pdf"},
    "YILDIRIM2020": {"atif": "Yildirim, S. (2020). Comparing deep neural networks to traditional models for sentiment analysis in Turkish language. In Deep Learning-Based Approaches for Sentiment Analysis. Springer.", "url": "https://doi.org/10.1007/978-981-15-1216-2_12"},
    "YOUTUBE_QUOTA_DOC": {"atif": "Google for Developers. YouTube Data API - Quota Calculator.", "url": "https://developers.google.com/youtube/v3/determine_quota_cost"},
}

# ---------------------------------------------------------------------------
# 1b) EK_KAYNAKLAR — v5 kuruma özgü eşik katmanı (rapor dışı, formülü değiştirmez)
# ---------------------------------------------------------------------------
EK_KAYNAKLAR: dict[str, dict[str, str]] = {
    "STRUBE1985": {"atif": "Strube, M. J. (1985). Combining and comparing significance levels from nonindependent hypothesis tests. Psychological Bulletin, 97(2), 334-341.", "url": "https://doi.org/10.1037/0033-2909.97.2.334"},
    "CINAR_VIECHTBAUER2022": {"atif": "Cinar, O., & Viechtbauer, W. (2022). The poolr package for combining independent and dependent p values. Journal of Statistical Software, 101(1), 1-42.", "url": "https://doi.org/10.18637/jss.v101.i01"},
    "PHIPSON_SMYTH2010": {"atif": "Phipson, B., & Smyth, G. K. (2010). Permutation p-values should never be zero: Calculating exact p-values when permutations are randomly drawn. Statistical Applications in Genetics and Molecular Biology, 9(1), Article 39.", "url": "https://arxiv.org/abs/1603.05766"},
    "CLOPPER_PEARSON1934": {"atif": "Clopper, C. J., & Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika, 26(4), 404-413.", "url": "https://doi.org/10.1093/biomet/26.4.404"},
    "WMO2023": {"atif": "World Meteorological Organization (2023). Guidelines on the Definition and Characterization of Extreme Weather and Climate Events (WMO-No. 1310).", "url": "https://library.wmo.int/records/item/58396-guidelines-onthe-definition-and-characterization-of-extreme-weather-and-climate-events"},
    "THAYER2025": {"atif": "Thayer, M. B., et al. (2025). Dengue alert thresholds. BMJ Open, 15, e106182.", "url": "https://doi.org/10.1136/bmjopen-2025-106182"},
    "FAWCETT2006": {"atif": "Fawcett, T. (2006). An introduction to ROC analysis. Pattern Recognition Letters, 27(8), 861-874.", "url": "https://doi.org/10.1016/j.patrec.2005.10.010"},
}


def tum_kaynaklar() -> dict[str, dict[str, str]]:
    return {**KAYNAKLAR, **EK_KAYNAKLAR, **ESIK_KAYNAKLARI, **LPTI_KAYNAKLARI, **PR_KAYNAKLARI}


def kaynak_grubu(kimlik: str) -> str:
    """Kaynağın hangi rapora/katmana ait olduğu: v4 | v5 | esik | lpti | pr."""
    for ad, sozluk in (("v4", KAYNAKLAR), ("v5", EK_KAYNAKLAR), ("esik", ESIK_KAYNAKLARI),
                       ("lpti", LPTI_KAYNAKLARI), ("pr", PR_KAYNAKLARI)):
        if kimlik in sozluk:
            return ad
    raise KeyError(kimlik)


# ---------------------------------------------------------------------------
# 2) GÖSTERGE KATALOĞU — Rapor Bölüm 2
# ---------------------------------------------------------------------------
# veri: "sosyal" | "haber" | "her_ikisi" | "trends"  (Rapor Bölüm 7, karar 11)
GOSTERGELER: list[dict] = [
    # ---- 2.1 SEÇİLDİ -------------------------------------------------------
    {"kod": "G1", "grup": "SECILDI", "ad": "Sosyal medya bahsetme hacmi anomalisi", "boyut": "DIKKAT", "veri": "sosyal",
     "olcum": "x = pencere içindeki sosyal medya içerik sayısı (Reddit gönderi/yorum, YouTube video/yorum, X gönderisi).",
     "gerekce": "Pfeffer vd. (2014) ateş fırtınasını 'kısa sürede büyük miktarda olumsuz mesajın ani boşalması' olarak tanımlar; hacim ve hız birinci faktördür. TwitInfo (Marcus vd., 2011) zirveleri doğrudan bin sayımları üzerinden tespit eder.",
     "kaynaklar": ["PFEFFER2014", "MARCUS2011", "HERHAUSEN2019"]},
    {"kod": "G2", "grup": "SECILDI", "ad": "Tekil yazar (katılımcı) sayısı anomalisi", "boyut": "DIKKAT", "veri": "sosyal",
     "olcum": "x = pencere içindeki farklı yazar sayısı.",
     "gerekce": "Ateş fırtınası az sayıda hesabın çok yazması değil, çok sayıda kullanıcının katılımıdır (Pfeffer vd. 2014 'sınırsız bilgi akışı'; Johnen vd. 2018 ve Rost vd. 2016 katılım davranışı).",
     "kaynaklar": ["PFEFFER2014", "JOHNEN2018", "ROST2016"]},
    {"kod": "G4", "grup": "SECILDI", "ad": "Arama ilgisi (Google Trends) anomalisi", "boyut": "DIKKAT", "veri": "trends",
     "olcum": "x = Google Trends göreli ilgi değeri (0-100), TR, saatlik.",
     "gerekce": "Arama verisi kamu ilgisinin eşzamanlı göstergesidir (Choi & Varian 2012; Ginsberg vd. 2009). Lazer vd. (2014) tek başına tahminci olarak kullanımının hatalı olduğunu gösterdiği için yalnızca bileşik endeksin bir alt göstergesi olarak kullanılır.",
     "kaynaklar": ["CHOI_VARIAN2012", "GINSBERG2009", "LAZER2014"]},
    {"kod": "G5", "grup": "SECILDI", "ad": "Haber hacmi anomalisi", "boyut": "DIKKAT", "veri": "haber",
     "olcum": "x = pencere içindeki kurumla ilgili haber sayısı (Google News RSS + tanımlı RSS).",
     "gerekce": "Gündem belirleme kuramı medyadaki görünürlüğün kamu önceliğine aktarıldığını gösterir (McCombs & Shaw 1972); iş haberlerinde kurum imajına etkisi Carroll & McCombs (2003) ile, medya itibarının kaynak niteliği Deephouse (2000) ile desteklenir.",
     "kaynaklar": ["DEEPHOUSE2000", "MCCOMBS_SHAW1972", "CARROLL_MCCOMBS2003"]},
    {"kod": "G6", "grup": "SECILDI", "ad": "Sosyal medya olumsuzluk oranı", "boyut": "TONALITE", "veri": "sosyal",
     "olcum": "x = olumsuz etiketli sosyal içerik / toplam sosyal içerik. Olumsuz: olumsuz sözcük sayısı > olumlu sözcük sayısı (Herhausen vd. 2019 kuralı) ya da TurkishBERTweet 'negative'.",
     "gerekce": "Popüler olaylar olumsuz duygu gücündeki artışla ilişkilidir (Thelwall vd. 2011); haber bağlamında olumsuz içerik daha çok yayılır (Hansen vd. 2011).",
     "kaynaklar": ["THELWALL2011", "HANSEN2011", "HERHAUSEN2019"]},
    {"kod": "G7", "grup": "SECILDI", "ad": "Haber olumsuzluğu (ters Janis-Fadner katsayısı)", "boyut": "TONALITE", "veri": "haber",
     "olcum": "JF = (f²-fu)/total² (f>u); 0 (f=u); (fu-u²)/total² (u>f). x = -JF (yüksek = kötü).",
     "gerekce": "Deephouse (2000) medya itibarını tam olarak bu katsayı ile ölçer; aralık (-1,1).",
     "kaynaklar": ["DEEPHOUSE2000", "JANIS_FADNER1965"]},
    {"kod": "G8", "grup": "SECILDI", "ad": "Öfke yoğunluğu", "boyut": "UYARILMISLIK", "veri": "sosyal",
     "olcum": "x = öfke sözcükleri / toplam sözcük (NRC EmoLex Türkçe 'anger').",
     "gerekce": "Herhausen vd. (2019) yüksek uyarılmışlık (öfke, korku/kaygı, iğrenme) yoğunluğunu 'eşleşen sözcük / toplam sözcük' olarak ölçer ve ateş fırtınası viralitesini daha güçlü öngördüğünü bulur. Berger & Milkman (2012): öfke viraliteyi artırır. Coombs (2007): sorumluluk arttıkça öfke artar ve olumsuz davranışı tetikler.",
     "kaynaklar": ["HERHAUSEN2019", "BERGER_MILKMAN2012", "COOMBS2007", "COOMBS_HOLLADAY2007"]},
    {"kod": "G9", "grup": "SECILDI", "ad": "Korku/kaygı yoğunluğu", "boyut": "UYARILMISLIK", "veri": "sosyal",
     "olcum": "x = korku sözcükleri / toplam sözcük (NRC EmoLex Türkçe 'fear').",
     "gerekce": "Jin vd. (2012) ICM modelinde kaygı krizlerde 'varsayılan' duygudur; Berger & Milkman (2012) kaygının viraliteyi artırdığını gösterir; Herhausen vd. (2019) korku/kaygıyı yüksek uyarılmışlık kategorisinde ölçer.",
     "kaynaklar": ["HERHAUSEN2019", "BERGER_MILKMAN2012", "JIN2012"]},
    {"kod": "G10", "grup": "SECILDI", "ad": "İğrenme yoğunluğu", "boyut": "UYARILMISLIK", "veri": "sosyal",
     "olcum": "x = iğrenme sözcükleri / toplam sözcük (NRC EmoLex Türkçe 'disgust').",
     "gerekce": "Herhausen vd. (2019) iğrenmeyi yüksek uyarılmışlık kategorisine dahil eder; Crockett (2017) çevrimiçi ahlaki öfkeyi (öfke+iğrenme) dijital yayılımın itici gücü olarak tartışır.",
     "kaynaklar": ["HERHAUSEN2019", "CROCKETT2017"]},
    {"kod": "G3", "grup": "SECILDI", "ad": "Etkileşim (viralite) anomalisi", "boyut": "YAYILIM", "veri": "sosyal",
     "olcum": "x = pencere içindeki sosyal içeriklerin beğeni + yorum (+ paylaşım/retweet) toplamı.",
     "gerekce": "Herhausen vd. (2019) viraliteyi 'beğeni + yorum' toplamı olarak ölçer; Stieglitz & Dang-Xuan (2013) paylaşım davranışını ölçer; Cha vd. (2010) takipçi sayısının değil retweet/bahsetmenin etkiyi yansıttığını gösterir.",
     "kaynaklar": ["HERHAUSEN2019", "STIEGLITZ2013", "CHA2010"]},
    {"kod": "G11", "grup": "SECILDI", "ad": "Platformlar arası (çapraz medya) yayılım", "boyut": "YAYILIM", "veri": "her_ikisi",
     "olcum": "x = pencerede en az bir olumsuz içerik görülen platform sayısı / aktif platform sayısı.",
     "gerekce": "Pfeffer vd. (2014) 'çapraz medya dinamiği'ni (sosyal medya-geleneksel medya yankı odası) ateş fırtınasının altıncı faktörü sayar; Kasperson vd. (1988) medyayı risk 'yükseltme istasyonu' olarak tanımlar; Harder vd. (2017) medya arası gündem aktarımını gösterir.",
     "kaynaklar": ["PFEFFER2014", "HARDER2017", "KASPERSON1988"]},
    {"kod": "G12", "grup": "SECILDI", "ad": "Olumsuz davranış niyeti (boykot / olumsuz ağızdan ağıza) oranı", "boyut": "NIYET", "veri": "sosyal",
     "olcum": "x = boykot / satın almama / başkalarını uyarma ifadesi içeren sosyal içerik oranı.",
     "gerekce": "Coombs & Holladay (2007) paydaş duygusunun olumsuz ağızdan ağıza iletişim ve satın alma niyeti üzerindeki etkisini (olumsuz iletişim dinamiği) inceler; Klein vd. (2004) boykot katılım motivasyonlarını açıklar.",
     "kaynaklar": ["COOMBS_HOLLADAY2007", "COOMBS2007", "KLEIN2004"]},
    {"kod": "G13", "grup": "SECILDI", "ad": "SCCT kriz sorumluluğu yüklemesi (yoğunlaştırıcılarla)", "boyut": "SORUMLULUK", "veri": "her_ikisi",
     "olcum": "Her içerik için seviye: 0 kriz dışı, 1 mağdur, 2 kaza, 3 önlenebilir; kriz geçmişi veya olumsuz önceki itibar varsa mağdur->kaza, kaza->önlenebilir. x = pencere ortalaması.",
     "gerekce": "SCCT'nin iki adımlı tehdit değerlendirmesi: (1) kriz tipi -> başlangıç sorumluluğu, (2) yoğunlaştırıcılar (Coombs 2007).",
     "kaynaklar": ["COOMBS2007", "COOMBS_HOLLADAY2002"]},
    # ---- 2.2 KALİTE ----------------------------------------------------------
    {"kod": "Q1", "grup": "KALITE", "ad": "Koordineli / kopya içerik oranı", "boyut": "KALITE", "veri": "sosyal",
     "olcum": "x = normalleştirilmiş metni en az iki farklı yazar tarafından paylaşılan içerik oranı.",
     "gerekce": "Pacheco vd. (2021) koordinasyonu hesaplar arasında paylaşılan davranış izleri (içerik, n-gram, hashtag) ile tespit eder. Doğal öfke de kısa tekrarlar üretebildiği için KRE'ye girmez; yalnızca 'manipülasyon şüphesi' uyarısıdır.",
     "kaynaklar": ["PACHECO2021"]},
    # ---- 2.3 ÇERÇEVE ---------------------------------------------------------
    {"kod": "C1", "grup": "CERCEVE", "ad": "Kriz yaşam döngüsü - prodromal (öncül) evre", "boyut": "CERCEVE", "veri": None,
     "olcum": "Ölçülmez; sistemin hedef evresidir. Western Electric Kural 4 (8 ardışık pozitif sapma) 'sessiz birikim' olarak raporlanır.",
     "gerekce": "Fink (1986) krizin akut evreden önceki uyarı evresini (prodromal) tanımlar; Pearson & Mitroff (1993) kriz yönetiminin ilk evresini sinyal tespiti olarak koyar.",
     "kaynaklar": ["FINK1986", "PEARSON_MITROFF1993"]},
    {"kod": "C2", "grup": "CERCEVE", "ad": "Parakriz (sosyal medyada görünür kriz riski)", "boyut": "CERCEVE", "veri": None,
     "olcum": "Ölçülmez; ERKEN UYARI seviyesinin kuramsal karşılığıdır.",
     "gerekce": "Coombs & Holladay (2012) sosyal medyanın kriz riskleri için kritik tarama alanı olduğunu ve çevrimiçi risklerin 'parakriz' olarak ele alınması gerektiğini belirtir.",
     "kaynaklar": ["COOMBS_HOLLADAY2012"]},
    {"kod": "C3", "grup": "CERCEVE", "ad": "Riskin sosyal yükseltilmesi", "boyut": "CERCEVE", "veri": None,
     "olcum": "G11 ile operasyonelleştirilir.",
     "gerekce": "Risk sinyalleri medya ve kişilerarası ağlar gibi 'yükseltme istasyonlarında' işlenir.",
     "kaynaklar": ["KASPERSON1988"]},
    {"kod": "C4", "grup": "CERCEVE", "ad": "Konu-ilgi döngüsü", "boyut": "CERCEVE", "veri": None,
     "olcum": "Ölçülmez; ilginin yükselip sönmesi EWMA ile uyarlanır.",
     "gerekce": "Kamu ilgisinin bir konuda kısa süre yoğunlaşıp sönmesi; EWMA'nın eski değerleri 'unutması' bu dinamiğe uygundur.",
     "kaynaklar": ["DOWNS1972"]},
    # ---- 2.4 ELENDİ ----------------------------------------------------------
    {"kod": "E1", "grup": "ELENDI", "ad": "Kleinberg patlama otomatı", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Kleinberg (2003) iki (ya da çok) durumlu otomat ile patlamaları akışın bütünü üzerinden çözer; ölçek (s) ve geçiş maliyeti (gamma) parametreleri gerektirir. TwitInfo, sosyal medya akışı için geliştirilmiş, geçmiş değerleri tutmayan ve sabitleri (alfa=0,125, tau=2, p=5) yayımlanmış akış algoritmasıdır; gerçek zamanlı erken uyarı için o seçildi.",
     "kaynaklar": ["KLEINBERG2003", "MARCUS2011"]},
    {"kod": "E2", "grup": "ELENDI", "ad": "Coğrafi yayılım (konum etiketli sosyal sensör)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Sakaki vd. (2010) deprem gibi konuma bağlı olaylar için konum kullanır; kurumsal itibar krizleri konuma bağlı değildir ve tweet'lerin yalnızca ~%0,85'i konum etiketlidir (Sloan & Morgan 2015).",
     "kaynaklar": ["SAKAKI2010", "SLOAN_MORGAN2015"]},
    {"kod": "E3", "grup": "ELENDI", "ad": "Hisse senedi anormal getirisi (olay çalışması)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Olay çalışması etkiyi olay açıklandıktan SONRA ölçer (gecikmeli) ve yalnızca borsada işlem gören kurumlar için geçerlidir; erken uyarı amacına aykırıdır.",
     "kaynaklar": ["MACKINLAY1997"]},
    {"kod": "E4", "grup": "ELENDI", "ad": "Anket tabanlı itibar endeksleri (Reputation Quotient vb.)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Paydaş anketiyle dönemsel olarak ölçülür; saatlik/günlük erken uyarı için veri üretmez. Medya itibarı Deephouse (2000) katsayısıyla (G7) otomatik ölçülür.",
     "kaynaklar": ["FOMBRUN2000"]},
    {"kod": "E5", "grup": "ELENDI", "ad": "Yayılım ağacı yapısı / yapısal viralite", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Tam retweet/paylaşım kaskadının (derinlik, genişlik, yapısal viralite) elde edilmesini gerektirir; X API ücretli/kullandıkça öde modeline geçti, Reddit/YouTube bu ağacı sağlamaz. Yerine platform-arası yayılım (G11) ve etkileşim (G3) kullanılır.",
     "kaynaklar": ["GOEL2016", "VOSOUGHI2018", "CJR2023", "X_PRICING_DOC"]},
    {"kod": "E6", "grup": "ELENDI", "ad": "Takipçi sayısı ile kullanıcı etkisi", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Cha vd. (2010): yüksek takipçili kullanıcılar retweet/bahsetme üretmek bakımından zorunlu olarak etkili değildir; takipçi sayısı tek başına etkiyi pek az açıklar. Etki, etkileşim (G3) ile ölçülür.",
     "kaynaklar": ["CHA2010"]},
    {"kod": "E7", "grup": "ELENDI", "ad": "Bilgi güvenilirliği / söylenti sınıflandırıcısı", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Castillo vd. (2011) kitle kaynaklı etiketli veri ve kullanıcı/yayılım ağacı özellikleri gerektirir; Türkçe etiketli veri ve X ağacı mevcut değildir. Söylenti, SCCT 'mağdur' kümesindeki 'söylenti' tipi olarak G13'te karşılanır.",
     "kaynaklar": ["CASTILLO2011", "VOSOUGHI2018"]},
    {"kod": "E8", "grup": "ELENDI", "ad": "Hesap tabanlı bot tespiti (Botometer)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Botometer X hesap metaverisine dayanır ve X API kapanmasıyla fiilen işlevsiz kalmıştır (CJR 2023). Yerine içerik izi temelli koordinasyon (Q1, Pacheco vd. 2021) kullanılır.",
     "kaynaklar": ["VAROL2017", "CJR2023"]},
    {"kod": "E9", "grup": "ELENDI", "ad": "Üzüntü yoğunluğu", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Üzüntü düşük uyarılmışlık duygusudur; Berger & Milkman (2012) viraliteyi AZALTTIĞINI, Herhausen vd. (2019) yüksek uyarılmışlığın viraliteyle ilişkisinin düşük uyarılmışlıktan anlamlı ölçüde güçlü olduğunu bulmuştur.",
     "kaynaklar": ["BERGER_MILKMAN2012", "HERHAUSEN2019"]},
    {"kod": "E10", "grup": "ELENDI", "ad": "Öznellik (subjectivity) oranı", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Öznellik, duygu kutbu analizinin ön adımıdır (Pang & Lee 2008); G6 ile büyük ölçüde örtüşür. OECD (2008) aynı olguyu iki kez ölçen göstergelerin çift sayıma yol açtığı konusunda uyarır.",
     "kaynaklar": ["PANG_LEE2008", "OECD2008"]},
    {"kod": "E11", "grup": "ELENDI", "ad": "İroni / alay tespiti", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Alay duygu kutbunu tersine çevirebilir (Maynard & Greenwood 2014), fakat Türkçe için doğrulanmış açık bir alay tespit kaynağı bulunamamıştır; ayrı bir gösterge olarak güvenilir ölçülemez.",
     "kaynaklar": ["MAYNARD2014"]},
    {"kod": "E12", "grup": "ELENDI", "ad": "Paydaş belirginliği (güç-meşruiyet-aciliyet)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Paydaşın güç, meşruiyet ve aciliyet niteliklerinin nitel değerlendirmesini gerektirir; açık metin verisinden otomatik ve geçerli biçimde çıkarılamaz.",
     "kaynaklar": ["MITCHELL1997"]},
    {"kod": "E13", "grup": "ELENDI", "ad": "Kriz yanıt stratejileri / imaj onarımı / sessizlik", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Bunlar krizin TESPİTİ değil, kriz sonrası YANITI ile ilgilidir (Benoit 1997; 'stealing thunder' Arpan & Roskos-Ewoldsen 2005). SCCT'de yanıt stratejisi, tehdit değerlendirmesinden sonra seçilir.",
     "kaynaklar": ["BENOIT1997", "ARPAN2005", "COOMBS2007"]},
    {"kod": "E14", "grup": "ELENDI", "ad": "Hazır kriz sözlüğü (CrisisLex)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "CrisisLex İngilizce ve doğal/insan kaynaklı afetler (kasırga, sel, bombalama) üzerine kurulmuştur; kurumsal itibar krizleri ve Türkçe için uygun değildir. Kriz tipleri SCCT tanımlarından türetilmiştir.",
     "kaynaklar": ["OLTEANU2014"]},
    {"kod": "E15", "grup": "ELENDI", "ad": "Yükselen terim tespiti (enerji/besin modeli)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Cataldi vd. (2010) kullanıcı otoritesini takipçi grafı üzerinde PageRank ile hesaplar; bu graf Reddit/YouTube/Google News'ten elde edilemez. Yöntem eksik parçayla uygulanırsa literatüre sadık kalmaz.",
     "kaynaklar": ["CATALDI2010"]},
    {"kod": "E16", "grup": "ELENDI", "ad": "Konu modelleme (LDA/BTM)", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Keşifsel bir yöntemdir, sayısal bir risk göstergesi üretmez; kısa metinlerde LDA'nın zayıf çalıştığı gösterilmiştir (Yan vd. 2013).",
     "kaynaklar": ["BLEI2003", "YAN2013"]},
    {"kod": "E17", "grup": "ELENDI", "ad": "Özellik (aspect) tabanlı duygu analizi", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Özellik etiketli eğitim verisi gerektirir (SemEval 2014); kurum-krizi için Türkçe özellik etiketli veri yoktur. Kriz içeriğinin sınıflandırılması SCCT tipleriyle (G13) yapılır.",
     "kaynaklar": ["PONTIKI2014"]},
    {"kod": "E18", "grup": "ELENDI", "ad": "Arama verisinin tek başına tahminci olarak kullanımı", "boyut": "-", "veri": None, "olcum": "-",
     "gerekce": "Google Flu Trends'in yüksek tahmin hataları (Lazer vd. 2014) nedeniyle arama verisi yalnızca bileşik endeksin bir alt göstergesidir (G4).",
     "kaynaklar": ["LAZER2014"]},
]

# ---------------------------------------------------------------------------
# 3) BOYUTLAR — Rapor Bölüm 2.1
# ---------------------------------------------------------------------------
BOYUTLAR: dict[str, list[str]] = {
    "DIKKAT": ["G1", "G2", "G4", "G5"],
    "TONALITE": ["G6", "G7"],
    "UYARILMISLIK": ["G8", "G9", "G10"],
    "YAYILIM": ["G3", "G11"],
    "NIYET": ["G12"],
    "SORUMLULUK": ["G13"],
}
BOYUT_ADLARI = {
    "DIKKAT": "Dikkat", "TONALITE": "Tonalite", "UYARILMISLIK": "Uyarılmışlık",
    "YAYILIM": "Yayılım", "NIYET": "Niyet", "SORUMLULUK": "Sorumluluk",
}

# Rapor Bölüm 7, karar 11 — sosyal / haber ayrımı
SOSYAL_GOSTERGELER = ("G1", "G2", "G3", "G6", "G8", "G9", "G10", "G12")
HABER_GOSTERGELER = ("G5", "G7")
HER_IKISI_GOSTERGELER = ("G11", "G13")

# ---------------------------------------------------------------------------
# 4) SABİTLER — Rapor Bölüm 4
# ---------------------------------------------------------------------------
ALFA = 0.125                     # [MARCUS2011; RFC6298; JACOBSON1988]
TAU = 2.0                        # [MARCUS2011] TwitInfo zirve eşiği
P_BASLATMA = 5                   # [MARCUS2011] Algoritma 1 başlatma
OMS_SIGMA_CARPANI = math.sqrt(math.pi / 2.0)   # [GEARY1935] σ = OMS·√(π/2)
KIRPMA_SINIRI = 3.0              # [SHEWHART1931; OECD2008 s.28]
FISHER_ANLAMLILIK = 0.05         # [FISHER_P05]
ISINMA_PENCERE = P_BASLATMA + math.ceil(math.log(FISHER_ANLAMLILIK) / math.log(1.0 - ALFA))  # = 28
ONEK_UZUNLUGU = 5                # [CAN2008] F5
OLUMSUZLAYICILAR = ("değil", "yok")   # [GOKSEL_KERSLAKE2005] sözcükten sonra gelir
BIN_SAAT = 1                     # [MARCUS2011] bin boyutu ayarlanabilir; varsayılan 1 saat
ANALIZ_GUN = 30                  # varsayılan analiz aralığı; kurum 7–180 gün arasında seçer
EN_FAZLA_ANALIZ_GUN = 180        # 6 ay

# ---------------------------------------------------------------------------
# 4b) KURUMA ÖZGÜ EŞİK SABİTLERİ — "Kuruma Özgü Kriz Eşiği Metodolojisi" Bölüm 13
#     Türü "Politika" olanlar veriden türetilemez (raporun "Dürüst not"u); değerler
#     gerekçeli başlangıç değerleridir ve Delphi paneli/etiketli veriyle belirlenmelidir.
# ---------------------------------------------------------------------------
RISK_Z_TAVAN = 6.0                              # Tasarım kararı 30: R = 100·min(max(Z,0),6)/6 (16,7 puan/σ)
ESIK_P = {"orta": 0.05, "yuksek": 0.01, "kritik": 0.001}   # Politika; dönüş süreleri 20/100/1000 saat [IEC62682_2022]
ESIK_PENCERE_GUN = 90                           # İstatistik/politika; kayan pencere [THAYER2025]
ESIK_MIN_ASIM = 5                               # İstatistik: Binom(n,p) beklenen aşım ≥ 5
ESIK_GPD_U_YUZDELIK = 0.90                      # İstatistik: GPD eşiği u = P90 [SIFFER2017]
ESIK_GPD_MIN_N = 200                            # Rapor Bölüm 4 tablosu: n ≥ 200
ESIK_GPD_MIN_ASIM = 20                          # Tasarım kararı 34: uyum için en az 20 aşım
ESIK_SAGLAM_MIN_N = 10                          # Rapor Bölüm 4.3: n ≥ 10
MAD_OLCEK = 1.4826                              # s = 1,4826·MAD = 1/Φ⁻¹(0,75)
ESIK_GUVENILIRLIK_N0 = 100                      # İstatistik: Z = n/(n+n0) [BUHLMANN1967]
ESIK_HAVUZ_MIN_KURUM = 2                        # Tasarım: sektör/platform havuzu en az 2 kurum
ESIK_HAVUZ_MIN_BLOK = 200                       # Tasarım: en az 200 blok
ESIK_UZMAN_ONSEL = (50.0, 75.0, 95.0)           # Politika: veri yokken başlangıç
ESIK_TABAN = (25.0, 40.0, 55.0)                 # Politika: mutlak korkuluk tabanı [WMO2023]
ESIK_TAVAN = (70.0, 85.0, 95.0)                 # Politika: mutlak korkuluk tavanı [WMO2023]
ESIK_MIN_ARALIK = 2.0                           # T_yüksek ≥ T_orta + 2, T_kritik ≥ T_yüksek + 2
ESIK_C_FN = 5.0                                 # Politika: kaçırma maliyeti [YOUDEN1950]
ESIK_C_FP = 1.0                                 # Politika: yanlış alarm maliyeti
ESIK_MIN_ETIKET = 20                            # İstatistik: toplam en az 20 etiket
ESIK_MIN_ETIKET_SINIF = 5                       # İstatistik: her sınıftan en az 5
ESIK_ETIKET_N0 = 30                             # İstatistik: Z_e = m/(m+30)
HACIM_SOK_Z = 3.0                               # İstatistik: 3-sigma [ROBERTS1959]
HACIM_PENCERE_SAAT = 24                         # Rapor Bölüm 8: son 24 saatin saatlik EWMA'sı
HISTEREZIS_K_ON = 2                             # Tasarım: on-delay (ISA-18.2, IEC 62682)
HISTEREZIS_K_OFF = 3                            # Tasarım: off-delay
HISTEREZIS_DELTA_MIN = 2.0                      # Tasarım: δ = max(2, 0,5·s)
HISTEREZIS_DELTA_KATSAYI = 0.5
ESIK_KARANTINA_GUN = 14                         # Tasarım kararı 45: etiketsiz alarm ölçümlerinin dışlanma süresi
ALARM_MIN_SEVIYE = 2                            # Rapor Bölüm 2 tablosu: Yüksek → kriz kaydı açılır
ALARM_BIRLESTIRME_SAAT = 6                      # Tasarım kararı 37
TARAMA_ARALIGI_DAKIKA = {0: 60, 1: 30, 2: 15, 3: 15}   # Tasarım kararı 42 (rapor: 5–60 dakika)

# Aynı krizin tanınması (geri bildirimle öğrenme) — Tasarım kararı 39–40
PARMAK_IZI_TERIM_SAYISI = 8
PARMAK_IZI_BENZERLIK = 0.5                      # tip belirsizken Jaccard eşiği
PARMAK_IZI_BENZERLIK_AYNI_TIP = 0.2             # aynı SCCT tipinde Jaccard eşiği

# Ölçek ve geri bildirim değerleri
GERI_BILDIRIM_DEGERLERI = ("gercek_kriz", "yanlis_alarm")

# WECO kuralları (yalnız üst taraf) — [WECO1956; NIST_WECO]
WECO_KURALLARI = [
    {"kural": 1, "kosul": "Tek nokta > +3σ", "n": 1, "m": 1, "sinir": 3.0, "seviye": 3, "etiket": "KRİZ"},
    {"kural": 2, "kosul": "Son 3 noktanın 2'si > +2σ", "n": 3, "m": 2, "sinir": 2.0, "seviye": 2, "etiket": "YÜKSEK UYARI"},
    {"kural": 3, "kosul": "Son 5 noktanın 4'ü > +1σ", "n": 5, "m": 4, "sinir": 1.0, "seviye": 1, "etiket": "ERKEN UYARI"},
    {"kural": 4, "kosul": "8 ardışık nokta > 0", "n": 8, "m": 8, "sinir": 0.0, "seviye": 1, "etiket": "ERKEN UYARI (sessiz birikim)"},
]
SEVIYE_ETIKETLERI = {0: "NORMAL", 1: "ERKEN UYARI", 2: "YÜKSEK UYARI", 3: "KRİZ"}   # WECO kural katmanı (Rapor Bölüm 3.7)
WECO_SEVIYE_ETIKETLERI = SEVIYE_ETIKETLERI
# Kuruma özgü eşik katmanı (Kuruma Özgü Kriz Eşiği Metodolojisi, Bölüm 2): karar katmanı
RISK_SEVIYE_ETIKETLERI = {0: "DÜŞÜK RİSK", 1: "ORTA RİSK", 2: "YÜKSEK RİSK", 3: "KRİTİK RİSK"}
RISK_SEVIYE_KISA = {0: "Düşük", 1: "Orta", 2: "Yüksek", 3: "Kritik"}
RISK_SEVIYE_EYLEMI = {
    0: "Olağan dalgalanma; işlem yok.",
    1: "İzleme; panelde işaret.",
    2: "Kriz kaydı açılır, bildirim gider.",
    3: "Kriz kaydı + acil öncelik.",
}

SABITLER: list[dict] = [
    {"ad": "α", "deger": "0,125", "kaynaklar": ["MARCUS2011", "RFC6298"]},
    {"ad": "τ (TwitInfo zirve eşiği)", "deger": "2", "kaynaklar": ["MARCUS2011"]},
    {"ad": "p (başlatma)", "deger": "5", "kaynaklar": ["MARCUS2011"]},
    {"ad": "OMS → σ çarpanı", "deger": "√(π/2) ≈ 1,2533", "kaynaklar": ["GEARY1935"]},
    {"ad": "Kırpma sınırı", "deger": "±3", "kaynaklar": ["SHEWHART1931", "OECD2008"]},
    {"ad": "Ağırlıklar", "deger": "eşit (boyut, sonra gösterge)", "kaynaklar": ["OECD2008"]},
    {"ad": "Birleştirme", "deger": "ağırlıklı Stouffer Z", "kaynaklar": ["WHITLOCK2005", "COUSINS2007"]},
    {"ad": "Uyarı eşikleri", "deger": "3σ; 2/3 > 2σ; 4/5 > 1σ; 8 > 0", "kaynaklar": ["WECO1956", "NIST_WECO"]},
    {"ad": "Isınma", "deger": "28 pencere", "kaynaklar": ["MARCUS2011", "FISHER_P05"]},
    {"ad": "Janis-Fadner", "deger": "(f²−fu)/N², 0, (fu−u²)/N²", "kaynaklar": ["DEEPHOUSE2000", "JANIS_FADNER1965"]},
    {"ad": "Nötr tanımı", "deger": "olumlu = olumsuz", "kaynaklar": ["DEEPHOUSE2000"]},
    {"ad": "Olumsuz içerik kuralı", "deger": "olumsuz sözcük > olumlu sözcük; olumsuzlama tersine çevirir", "kaynaklar": ["HERHAUSEN2019"]},
    {"ad": "Yüksek uyarılmışlık", "deger": "öfke, korku/kaygı, iğrenme sözcükleri / toplam sözcük", "kaynaklar": ["HERHAUSEN2019"]},
    {"ad": "Viralite", "deger": "beğeni + yorum (+ paylaşım)", "kaynaklar": ["HERHAUSEN2019", "STIEGLITZ2013"]},
    {"ad": "Türkçe önek uzunluğu", "deger": "5 karakter", "kaynaklar": ["CAN2008"]},
    {"ad": "Türkçe olumsuzlayıcılar", "deger": "\"değil\", \"yok\" (sözcükten sonra gelir)", "kaynaklar": ["GOKSEL_KERSLAKE2005"]},
]

# ---------------------------------------------------------------------------
# 5) TASARIM KARARLARI — Rapor Bölüm 7 (1–11) + v5 ekleri (12+)
#    Hiçbirine uydurma kaynak atfedilmemiştir.
# ---------------------------------------------------------------------------
TASARIM_KARARLARI: list[dict] = [
    {"no": 1, "kaynak": "rapor", "baslik": "SCCT tohum ifadeleri (nlp/scct.py)", "aciklama": "Her kriz tipinin Türkçe anahtar gövdeleri, Coombs (2007) tanımlarından türetilmiş operasyonelleştirmedir; literatürde yayımlanmış bir Türkçe SCCT sözlüğü değildir. Daha literatüre sadık seçenek ERKIS_SCCT_MOTORU=sifir_atis'tir (tanımların kendisi hipotez olarak kullanılır)."},
    {"no": 2, "kaynak": "rapor", "baslik": "Davranış niyeti ifadeleri (nlp/behavioral.py)", "aciklama": "Boykot / satın almama / başkalarını uyarma ifadeleri, Coombs & Holladay (2007) ve Klein vd. (2004) kavramlarının Türkçe operasyonelleştirmesidir."},
    {"no": 3, "kaynak": "rapor", "baslik": "Çoklu kriz tipi eşleşmesi", "aciklama": "Birden çok kriz tipi eşleşirse en yüksek sorumluluk seçilir (ihtiyatlı varsayım). Pencere düzeyinde baskın küme en sık görülen kümedir; eşitlikte yüksek sorumluluk seçilir."},
    {"no": 4, "kaynak": "rapor", "baslik": "Başlangıç varyansı", "aciklama": "Başlangıç 'variance' popülasyon varyansı olarak hesaplanır (TwitInfo makalesi örneklem/popülasyon ayrımı belirtmez)."},
    {"no": 5, "kaynak": "rapor", "baslik": "Eksik veride ağırlıklar", "aciklama": "Bir pencerede ölçülemeyen göstergeler dışarıda bırakılır ve kalan göstergelerin ağırlıkları toplam 1 olacak biçimde yeniden normalleştirilir (her iki beyinde de). Her skorla birlikte ölçülebilen gösterge listesi saklanır; farklı kapsamla hesaplanmış iki dönem doğrudan karşılaştırılırken bu bilinmelidir."},
    {"no": 6, "kaynak": "rapor", "baslik": "NRC çoklu çeviri birleştirme", "aciklama": "Aynı Türkçe sözcüğe eşlenen İngilizce satırlarda bir etiket satırların yarısından fazlasında işaretliyse atanır (makine çevirisi gürültüsünü azaltmak için)."},
    {"no": 7, "kaynak": "rapor", "baslik": "Önek eşleşmesi kuralı", "aciklama": "Sözlük girdisi en az 5 karakterse metindeki sözcüğün öneki olarak eşleşir (Can vd. 2008'in F5 bulgusundan uyarlanmış); daha kısa girdiler yalnızca birebir eşleşir. Sözlük tarafı kesilmez; böylece 'kalite' (etiketsiz) ile 'kalitesiz' (olumsuz) karışmaz. Uygulama ayrıntısı: birden çok girdi eşleşirse en uzun girdi (etiketsiz olsa bile) seçilir; çok sözcüklü girdilerde kural her sözcüğe ayrı uygulanır."},
    {"no": 8, "kaynak": "rapor", "baslik": "Kurum adının duygu hesabından çıkarılması", "aciklama": "Kurum adındaki sözcükler (ör. 'Gıda' sözcüğünün NRC'de 'joy' etiketli olması) görüş ifadesi sayılmaz."},
    {"no": 9, "kaynak": "rapor", "baslik": "Analiz penceresi", "aciklama": "Analiz penceresi varsayılan 30 gün (Google News aylarca eski haber döndürebildiği için)."},
    {"no": 10, "kaynak": "rapor", "baslik": "Etkileşim anlık görüntüsü", "aciklama": "Etkileşim sayıları toplama anındaki değerlerdir; aynı içerik yeniden toplandığında güncellenir."},
    {"no": 11, "kaynak": "rapor", "baslik": "Sosyal / haber ayrımı", "aciklama": "G1–G3, G6, G8–G10, G12 yalnız sosyal içerikten; G5, G7 yalnız haberden; G11 ve G13 her ikisinden hesaplanır."},
    # ---- v5 ekleri: uygulamanın çalışması için alınan, raporda açıkça yazılmamış kararlar
    {"no": 12, "kaynak": "v5", "baslik": "Olumsuzlayıcının kapsamı", "aciklama": "'değil'/'yok' yalnızca hemen önündeki duygu sözcüğünün olumlu/olumsuz kutbunu tersine çevirir. Olumsuzlayıcı da 7. karardaki önek kuralına tabidir: 'değil' (5 karakter) 'değilim', 'değildir' biçimlerini kapsar; 'yok' (3 karakter) yalnızca birebir eşleşir. Olumsuzlama duygu kategorilerini (öfke/korku/iğrenme) değiştirmez; rapor yalnız kutup kuralında tersine çevirmeyi tanımlar."},
    {"no": 13, "kaynak": "v5", "baslik": "Eksik ve sıfır ayrımı", "aciklama": "Sıfır, ancak ilgili kaynak o pencereyi kapsayan bir taramada başarıyla okunmuşsa geçerli bir gözlemdir. Kaynak o pencere için taranmamış, yapılandırılmamış ya da hata vermişse gösterge eksiktir (kaynak_kapsami tablosu). Oran göstergelerinde payda sıfırsa gösterge eksiktir. Eksik pencerede TwitInfo durumu güncellenmez."},
    {"no": 14, "kaynak": "v5", "baslik": "Akış başlatması", "aciklama": "Algoritma 1'deki başlatma (μ = C1, OMS = variance(C1..Cp)) gözlenen ilk p = 5 değer biriktiğinde yapılır; C2..Cp güncelleme olarak uygulanır (Algoritma 1'deki döngü i = 2'den başlar). Bu ilk p pencerede skor tanımsızdır; ısınma kuralı zaten ilk 28 pencerede alarmı kapatır."},
    {"no": 15, "kaynak": "v5", "baslik": "Aktif platform tanımı (G11)", "aciklama": "G11 paydası, o pencereyi kapsayan başarılı taramaya sahip kaynakların (haber ve sosyal) sayısıdır; pencerede içerik gelmiş olması koşul değildir. Kaynak kapsamı olmayan pencerede G11 eksiktir. Böylece tek platformdan içerik gelmesi yayılımı olduğundan yüksek göstermez."},
    {"no": 16, "kaynak": "v5", "baslik": "Pencere düzeyi toplama (G8–G10)", "aciklama": "Pencere değeri, penceredeki tüm sosyal içeriklerdeki eşleşen sözcük toplamının toplam sözcük sayısına oranıdır (havuzlanmış oran)."},
    {"no": 17, "kaynak": "v5", "baslik": "Q1 kapsamı", "aciklama": "Kopya içerik eşleşmesi aynı pencere içinde aranır. Normalleştirme: küçük harf, URL ve @kullanıcı adlarının silinmesi, noktalama kaldırma, boşluk sadeleştirme."},
    {"no": 18, "kaynak": "v5", "baslik": "Alarm dönemi", "aciklama": "v5.1'de değişti (bkz. karar 37): alarm dönemi, kuruma özgü eşik katmanında nihai seviyesi ≥ Yüksek olan ardışık pencerelerdir. Kullanıcı geri bildirimi (gerçek kriz / önemsiz) bu kayda bağlanır. WECO düzeyi ≥ 1 pencereler artık kayıt açmaz; panelde kural sinyali olarak görünür."},
    {"no": 19, "kaynak": "v5", "baslik": "Sıfır-atış SCCT kabul sınırı", "aciklama": "ERKIS_SCCT_MOTORU=sifir_atis seçildiğinde bir kriz tipi, çok etiketli NLI modunda gerekçe (entailment) olasılığı 0,5'ten büyükse kabul edilir (ikili NLI kararında 'çelişkiden daha olası' sınırı)."},
    {"no": 20, "kaynak": "v5", "baslik": "Korelasyon düzeltmeli Z (isteğe bağlı)", "aciklama": "ERKIS_Z_YONTEMI=strube seçildiğinde korelasyonlar kurumun analiz dönemindeki ısınma sonrası skorlarından, çift bazında eksiksiz gözlemlerle Pearson korelasyonu olarak kestirilir; bir çift için en az 28 (ısınma uzunluğu) ortak pencere yoksa o çiftin korelasyonu 0 alınır; payda pozitif değilse bağımsız Stouffer'a dönülür. Varsayılan rapordaki bağımsız Stouffer Z'dir."},
    {"no": 21, "kaynak": "v5", "baslik": "Bildirim sınırı", "aciklama": "v5.1'de değişti (bkz. karar 38): bildirimler varsayılan olarak kuruma özgü eşik katmanında YÜKSEK RİSK (seviye 2) ve üstünde gönderilir; kullanıcı en düşük seviyeyi değiştirebilir. Bu bir tespit kuralı değil, iletim tercihidir."},
    {"no": 22, "kaynak": "v5", "baslik": "Kurum eşiği panelinde gösterim", "aciklama": "v5.1'de değişti (bkz. karar 43): ham birim eşikleri ve Stouffer kalibrasyon tanısı yalnız raporlanır; seviye kararı kuruma özgü eşik metodolojisiyle verilir, WECO kuralları açıklayıcı sinyaldir."},
    {"no": 23, "kaynak": "v5", "baslik": "WECO nokta dizisi", "aciklama": "WECO kuralları ısınma sonrasındaki ve Z değeri tanımlı olan pencerelerin oluşturduğu nokta dizisine uygulanır; Z'si eksik (hiç gösterge yok) pencere bir nokta sayılmaz ve atlanır. Isınma içindeki noktalar kural pencerelerine girmez."},
    {"no": 24, "kaynak": "v5", "baslik": "Kesme işaretinden sonraki ek", "aciklama": "Türkçe yazımda özel ada gelen ek kesme işaretiyle ayrıldığı için ('Gıda'nın') kesme işaretinden sonraki ek sözcüklere ayırmada atılır; böylece ek ayrı bir sözcük sayılmaz."},
    {"no": 25, "kaynak": "v5", "baslik": "Dil filtresi belirsizliği", "aciklama": "ERKIS_DIL_FILTRESI=1 iken langdetect dili belirleyemezse (çok kısa metin vb.) içerik dışlanmaz."},
    {"no": 26, "kaynak": "v5", "baslik": "Tamamlanmış pencere", "aciklama": "Yalnız süresi dolmuş pencereler analiz edilir; içinde bulunulan saat, veri toplanması sürdüğü için bir sonraki çalıştırmaya bırakılır."},
    {"no": 27, "kaynak": "v5", "baslik": "Yazarı bilinmeyen içerik (G2, Q1)", "aciklama": "Kaynak yazar bilgisi döndürmezse içerik ayrı (tekil) bir yazar sayılır; böylece Q1 kopya oranı yapay olarak şişirilmez."},
    {"no": 28, "kaynak": "v5", "baslik": "Google Trends CSV okuma", "aciklama": "Google Trends dışa aktarımındaki '<1' değeri 0 okunur. CSV saatleri kullanıcının yerel saatidir; kullanıcının belirttiği UTC farkıyla (varsayılan +3, Türkiye) UTC'ye çevrilir. Saatlik olmayan (günlük/haftalık) satırlar pencere uzunluğuyla uyuşmadığı için okunmaz."},
    {"no": 29, "kaynak": "v5", "baslik": "Gerçek veri ilkesi", "aciklama": "Sistem sentetik ya da örnek içerik üretmez. Veri yoksa panel nedenini (kaynak bağlı değil, tarama yapılmadı, kapsamda içerik yok, kaynak hatası) ayrı ayrı gösterir."},
]

# v5.1 ekleri: kuruma özgü eşik (30–44) ve PR danışmanlığı (45+) — numaralar otomatik sıralanır
for _k in [*ESIK_KARARLARI, *PR_KARARLARI]:
    TASARIM_KARARLARI.append({"no": len(TASARIM_KARARLARI) + 1, **_k})

KRIZYOLDA_KARARLARI: list[dict] = [
    {"kaynak": "krizyolda", "baslik": "1. beyin: eşit gösterge ağırlığı",
     "aciklama": "13 göstergenin tümü ölçülebildiğinde her gösterge KRE'ye 1/13 (= 7,6923 puan; toplam 100) ile girer. Tam sayı ağırlıkla toplamı 100 yapmak 13'e bölünemediği için mümkün değildir; ağırlıklar ondalıklı tutulur, toplam 1'e normalleştirilir. Boyutlara önce eşit pay verilmez; boyutlar yalnız gösterim amaçlıdır. Eşit ağırlık bir başlangıç varsayımıdır, bilimsel olarak en iyi ağırlık olduğu iddia edilmez; 2. beyinle karşılaştırılarak değerlendirilir."},
    {"kaynak": "krizyolda", "baslik": "2. beyin: uzman ağırlıklı değerlendirme",
     "aciklama": "Her uzman 13 göstergeyi form sürümünde tanımlı ölçekte puanlar. Göstergenin uzmanlar arası puanı (ortalama ya da medyan; form sürümünde seçilir) toplamı 1 olacak biçimde normalleştirilerek ağırlık yapılır. Uzmanlar arası uyum Kendall W ile raporlanır. Form sürümündeki soru, ölçek ve birleştirme yöntemi araştırmacı kararıdır. Form etkinleştirilip en az min_uzman uzmanın 13 puanı girilmedikçe 2. beyin hesaplanmaz; eksik puan sıfır sayılmaz."},
    {"kaynak": "krizyolda", "baslik": "İki beynin karşılaştırılması",
     "aciklama": "Her iki beyin aynı TwitInfo z-skorlarını kullanır; yalnız ağırlıklar farklıdır. Karar (alarm, e-posta) 1. beyinle verilir. 2. beyin paralel raporlanır: risk puanı farkı, Z farkı, ayrışan gösterge katkıları ve her beynin kendi geçmişine göre aşım yüzdeliği. Birleştirme ancak bilimsel yöntem ve veriyle doğrulandıktan sonra eklenebilir."},
    {"kaynak": "krizyolda", "baslik": "Başlangıç ölçeği (OMS) ve sabit seri",
     "aciklama": "OMS başlangıçta ilk p değerin popülasyon varyansıdır (TwitInfo Algoritma 1'in sözde kodu). Varyansın birimi ölçülen değişkenin karesidir; ortalama mutlak sapmayla birim uyuşmazlığı vardır. Bu davranış orijinal yayımla birebir uyumlu tutulmuştur; birincil kaynakla yeniden doğrulanana kadar açık karar olarak işaretlidir. İlk p değer sabitse OMS = 0 olur ve sonraki ilk sıçrama bir pencere için skor üretmez."},
    {"kaynak": "krizyolda", "baslik": "Analiz aralığı: 7 gün – 6 ay ve özel aralık",
     "aciklama": "Aralık 7, 30, 90, 180 gün ya da kurumun belirlediği özel tarih aralığıdır; en fazla 180 gündür. İlk taramada seçilen aralığın tamamı geçmiş tarama işi olarak çekilir; sonraki rutin taramalar yalnız son kapsanan andan itibarenki farkı çeker. Her kaynak yalnız erişebildiği kadar geriye gider (Google News haftalık dilimlerle, X yalnız yetkili erişim düzeyine göre, Google Trends saatlik yalnız son 7 gün); ulaşılan aralık kaynak sağlığı tablosunda gösterilir ve eksik dönemler uydurulmaz."},
    {"kaynak": "krizyolda", "baslik": "Uyarlamalı tarama sıklığı ve bildirim ayrımı",
     "aciklama": "Sistem veriyi sürekli toplar; tarama aralığı kuruma özgü risk seviyesine göre kurumun izin verdiği alt-üst sınır içinde sistemce seçilir (düşük risk: uzun aralık, yüksek/kritik: kısa). Bildirim taramadan bağımsızdır: bir alarm için ilk bildirim bir kez gönderilir, sonraki e-postalar yalnız seviye yükselirse ve kurumun belirlediği bekleme süresi dolduysa (Kritik'e çıkış bekleme süresine tabi değildir) gönderilir. Alarm kapanıp aynı kriz sürerse yeniden bildirim yapılmaz (alarm birleştirme)."},
    {"kaynak": "krizyolda", "baslik": "Açık kaynak ve kurum API bağlantısı",
     "aciklama": "Açık kaynak modu anahtarsız kaynakları kullanır: Google Haber RSS, Bing Haber RSS, kurumun tanımladığı RSS adresleri, Reddit genel arama ve Google Trends. Bu kaynakların hiçbiri tüm interneti kapsamaz ve biçimleri değişebilir. Kurum kendi YouTube, X ve Instagram hesabı için kimlik bilgisi yüklerse yorum ve gönderiler ek kaynak olur; kimlik bilgisi şifreli saklanır, arayüzde bir daha gösterilmez, bağlantı testi yetki ve erişilebilen veri türünü ayrı raporlar."},
    {"kaynak": "krizyolda", "baslik": "Bildirim güvenilirliği",
     "aciklama": "E-postalar önce kalıcı kuyruğa yazılır; her alıcıya ayrı mesaj gider (adresler birbirine görünmez). Geçici hatada artan bekleme süresiyle en fazla BILDIRIM_EN_FAZLA_DENEME kez denenir, sonra kalıcı hata olur ve yöneticiye görünür. SMTP kabulü 'smtp_kabul' olarak adlandırılır; gelen kutusuna teslim edildiği anlamına gelmez. Aynı olay için tekilleştirme anahtarı ikinci gönderimi engeller."},
]
for _k in KRIZYOLDA_KARARLARI:
    TASARIM_KARARLARI.append({"no": len(TASARIM_KARARLARI) + 1, **_k})

# ---------------------------------------------------------------------------
# 6) SINIRLILIKLAR — Rapor Bölüm 8
# ---------------------------------------------------------------------------
SINIRLILIKLAR: list[str] = [
    "NRC EmoLex Türkçe dosyası İngilizce sözlüğün makine çevirisidir; bağlama duyarsızdır ve çeviri hataları içerir. Türkçe için el ile oluşturulmuş alternatifler (ör. Toçoğlu & Alpkoçak 2019, Türkçe sözlük tabanlı duygu analizi ve TREMO veri kümesi) lisans ve kapsam uygunluğu doğrulandıktan sonra aynı arayüze bağlanabilir. [TOCOGLU2019, TREMO2018]",
    "Önek eşleşmesi fiil ekiyle yapılan olumsuzluğu (-mA-) yakalayamaz; yalnızca 'değil' ve 'yok' ele alınır.",
    "Sözlük tabanlı duygu analizi alay/ironiyi yakalayamaz (E11).",
    "Stouffer Z bileşenlerin bağımsızlığını varsayar; göstergeler arasında korelasyon olduğunda Z büyüyebilir. Bu nedenle kırpma (±3) ve göstergelere eşit ağırlık uygulanır ve seviye kararları (v5.1) kuruma özgü ampirik eşiklerle verilir; bu eşikler Z'nin şişmesini kurumun kendi dağılımıyla dengeler. Kurum eşiği panelindeki kalibrasyon tanısı şişmeyi ayrıca ölçer; isteğe bağlı Strube (1985) düzeltmesi sunulur.",
    "Q1 (koordinasyon) KRE'ye girmez; yüksek Q1, sinyalin yapay olabileceğine dair bir uyarıdır.",
    "Sistemin gerçek krizlerdeki isabeti kanıtlanmış değildir. Gerçek performans, etiketli geçmiş kriz vakalarıyla ayrıca doğrulanmalıdır.",
]


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def secilen_gostergeler() -> list[dict]:
    return [g for g in GOSTERGELER if g["grup"] == "SECILDI"]


def gosterge(kod: str) -> dict:
    for g in GOSTERGELER:
        if g["kod"] == kod:
            return g
    raise KeyError(kod)


def tam_veri_agirliklari() -> dict[str, float]:
    """1. beyin: 13 göstergenin tamamı ölçülebildiğinde her gösterge 1/13 (= 100/13 puan) ağırlık alır."""
    return {kod: 1.0 / 13 for v in BOYUTLAR.values() for kod in v}


def dogrula_katalog() -> list[str]:
    """Katalog tutarlılık denetimi; hata listesi döndürür (boş = geçerli)."""
    hatalar: list[str] = []
    tum = tum_kaynaklar()
    kodlar = [g["kod"] for g in GOSTERGELER]
    if len(kodlar) != len(set(kodlar)):
        hatalar.append("Yinelenen gösterge kodu var.")
    for g in GOSTERGELER:
        if not g["kaynaklar"]:
            hatalar.append(f"{g['kod']} için kaynak yok.")
        for k in g["kaynaklar"]:
            if k not in KAYNAKLAR:
                hatalar.append(f"{g['kod']}: tanımsız kaynak {k}")
    for s in SABITLER:
        for k in s["kaynaklar"]:
            if k not in KAYNAKLAR:
                hatalar.append(f"Sabit {s['ad']}: tanımsız kaynak {k}")
    secilen = {g["kod"] for g in secilen_gostergeler()}
    boyuttaki = [k for v in BOYUTLAR.values() for k in v]
    if set(boyuttaki) != secilen or len(boyuttaki) != len(set(boyuttaki)):
        hatalar.append("BOYUTLAR ile SEÇİLDİ göstergeleri birebir uyuşmuyor.")
    for g in secilen_gostergeler():
        if g["kod"] not in BOYUTLAR.get(g["boyut"], []):
            hatalar.append(f"{g['kod']} boyutu ({g['boyut']}) BOYUTLAR ile uyuşmuyor.")
    ayrim = set(SOSYAL_GOSTERGELER) | set(HABER_GOSTERGELER) | set(HER_IKISI_GOSTERGELER) | {"G4"}
    if ayrim != secilen:
        hatalar.append("Sosyal/haber ayrımı SEÇİLDİ kümesini tam kapsamıyor.")
    if abs(sum(tam_veri_agirliklari().values()) - 1.0) > 1e-12:
        hatalar.append("Tam veri ağırlıkları 1'e toplanmıyor.")
    if ISINMA_PENCERE != 28:
        hatalar.append(f"Isınma {ISINMA_PENCERE}, raporda 28.")
    for k, v in tum.items():
        if not v.get("url", "").startswith("http") and not v.get("url_notu"):
            hatalar.append(f"{k} için URL yok ve url_notu verilmemiş.")
    for k in {*ESIK_KAYNAKLARI, *LPTI_KAYNAKLARI, *PR_KAYNAKLARI}:
        if k in KAYNAKLAR or k in EK_KAYNAKLAR:
            hatalar.append(f"{k} birden çok katalogda tanımlı.")
    nolar = [d["no"] for d in TASARIM_KARARLARI]
    if nolar != list(range(1, len(nolar) + 1)):
        hatalar.append("Tasarım kararı numaraları sıralı değil.")
    for d in [*TASARIM_KARARLARI, *LPTI_KARARLARI]:
        for ref in d.get("kaynaklar", []):
            if ref not in tum:
                hatalar.append(f"Karar {d.get('no', d.get('kod'))}: tanımsız kaynak {ref}")
    for p_ in ESIK_PARAMETRELERI:
        for ref in p_["kaynaklar"]:
            if ref not in tum:
                hatalar.append(f"Eşik parametresi {p_['ad']}: tanımsız kaynak {ref}")
    return hatalar


def katalog_json() -> dict:
    """/api/literatur yanıtı."""
    from app.pr import katalog as prk
    tum = tum_kaynaklar()
    return {
        "kaynaklar": [{"kimlik": k, **v, "ek": kaynak_grubu(k) != "v4", "grup": kaynak_grubu(k)}
                      for k, v in sorted(tum.items())],
        "gostergeler": GOSTERGELER,
        "boyutlar": BOYUTLAR,
        "boyut_adlari": BOYUT_ADLARI,
        "agirliklar": tam_veri_agirliklari(),
        "sabitler": SABITLER,
        "weco_kurallari": WECO_KURALLARI,
        "isinma_pencere": ISINMA_PENCERE,
        "tasarim_kararlari": TASARIM_KARARLARI,
        "sinirliliklar": SINIRLILIKLAR,
        "esik_parametreleri": ESIK_PARAMETRELERI,
        "esik_sinirliliklari": ESIK_SINIRLILIKLARI,
        "risk_seviyeleri": [{"seviye": k, "etiket": RISK_SEVIYE_ETIKETLERI[k], "eylem": RISK_SEVIYE_EYLEMI[k]}
                            for k in RISK_SEVIYE_ETIKETLERI],
        "lpti_kararlari": LPTI_KARARLARI,
        "lpti_sinirliliklari": LPTI_SINIRLILIKLARI,
        "pr": {"evreler": prk.EVRELER, "temel_yanit": prk.TEMEL_YANIT, "stratejiler": prk.STRATEJILER,
               "kurallar": prk.KURALLAR, "zamanlama": prk.ZAMANLAMA, "kanal": prk.KANAL},
        "dogrulama_hatalari": dogrula_katalog(),
    }
