"""
PR danışmanlığı katalog verisi: ek kaynaklar ve literatür dışı tasarım kararları.

Strateji adları, tanımları ve seçim kuralları app/pr/katalog.py içindedir ve
Coombs (2007) "SCCT crisis response strategy guidelines" tablosuna dayanır.
Bu dosyadaki iki kaynak (DOI'leri doğrulanmıştır) SCCT yoğunlaştırıcılarının
(kriz geçmişi, önceki ilişki itibarı) dayanağıdır.
"""
from __future__ import annotations

PR_KAYNAKLARI: dict[str, dict[str, str]] = {
    "COOMBS2004": {"atif": "Coombs, W. T. (2004). Impact of past crises on current crisis communication: Insights from situational crisis communication theory. Journal of Business Communication, 41(3), 265-289.",
                   "url": "https://doi.org/10.1177/0021943604265607"},
    "COOMBS_HOLLADAY2001": {"atif": "Coombs, W. T., & Holladay, S. (2001). An extended examination of the crisis situations: A fusion of the relational management and symbolic approaches. Journal of Public Relations Research, 13(4), 321-340.",
                            "url": "https://doi.org/10.1207/S1532754XJPRR1304_03"},
}

# v5.1 PR danışmanlığı için literatür dışı kararlar (numaralar app/literatur.py'de sıraya eklenir)
PR_KARARLARI: list[dict] = [
    {"kaynak": "pr", "baslik": "PR danışmanlığının sürekli (kriz dışı) yapısı",
     "aciklama": "Danışmanlık yalnızca alarm anında değil her gün veriyle çalışır. Çerçeve Pearson & Mitroff'un (1993) beş evresidir: sinyal tespiti, yoklama/önleme, hasar sınırlama, toparlanma, öğrenme. Her evre için sistemin ürettiği içerik verinin kendisinden gelir (göstergeler, alarm geçmişi, geri bildirimler, L-PTİ). Evrelerin isimleri literatürden, evreyi veriden belirleyen kurallar (aşağıdaki karar) tasarımdır."},
    {"kaynak": "pr", "baslik": "Evre belirleme kuralı",
     "aciklama": "Açık alarm (nihai seviye ≥ Yüksek) varsa 'hasar sınırlama'; son 14 gün içinde kapanmış bir alarm varsa 'toparlanma'; geri bildirimi verilmemiş kapanmış alarm varsa 'öğrenme' öne çıkarılır; bunların hiçbiri yoksa 'sinyal tespiti / yoklama ve önleme'. 14 günlük süre kaynaksızdır."},
    {"kaynak": "pr", "baslik": "Zayıf sinyal tanımı",
     "aciklama": "Bir gösterge, son 24 pencerenin en az 3'ünde +1σ bölgesinin (WECO Bölge C sınırı) üstünde ise 'izlenecek zayıf sinyal' sayılır. +1σ sınırı Western Electric kurallarından, 3 pencere sayısı tasarımdandır. WECO Kural 3/4 tetiklenmişse (özellikle Kural 4, Fink'in prodromal evresi) sinyal 'sessiz birikim' olarak ayrıca gösterilir."},
    {"kaynak": "pr", "baslik": "Kriz eşiğine uzaklık",
     "aciklama": "Kriz olmadığı dönemlerde de sistemin çalıştığını göstermek için son risk puanı, kurumun Yüksek eşiğine oranıyla ve eşik aşılırsa aşım olasılığıyla birlikte sunulur (R/T_yüksek ve 'son 7 günde Orta seviyede geçen saat sayısı'). Oran ve saat sayımı basit betimsel istatistiklerdir; literatür yorumu içermez."},
    {"kaynak": "pr", "baslik": "Strateji metinlerinin operasyonelleştirilmesi",
     "aciklama": "Strateji ailelerinin adları, tanımları ve hangi kriz kümesi/yoğunlaştırıcı durumunda önerileceği Coombs (2007) tablosundan gelir (kural numaraları gösterilir). 'Uygulama notu' olarak verilen somut cümle iskeletleri ve sıralama önerileri ise bu tanımların pratiğe çevrilmesidir ve literatür bulgusu değildir; kurumun hukuk/iletişim ekibince onaylanmalıdır. İçerikteki olgusal iddiaların doğrulanması sistemin kapsamı dışındadır."},
    {"kaynak": "pr", "baslik": "Söylenti ve meydan okuma için inkâr seçeneği",
     "aciklama": "Coombs (2007) kural 7 inkâr duruşunu söylenti ve meydan okuma krizlerinde 'mümkünse' önerir. İddianın gerçekten asılsız olup olmadığı veriden anlaşılamaz; bu yüzden inkâr, kurumun kendi doğrulamasına bağlı koşullu seçenek olarak sunulur ve kural 8 (inkârı diğer duruşlarla karıştırmama) hatırlatılır."},
    {"kaynak": "pr", "baslik": "Haftalık PR brifi",
     "aciklama": "Kurum, kriz olmasa da yedi günde bir e-posta ile brif alır (Ayarlar'dan kapatılabilir). Brif, panelde her an görülebilen PR danışmanlık ekranıyla aynı içeriktir. Yedi günlük periyot tasarım tercihidir."},
    {"kaynak": "pr", "baslik": "İtibar sürücüsüne yönelik iletişim odağı",
     "aciklama": "L-PTİ sürücü karnesinde (L-PTİ Adım 9) en düşük skorlu sürücü, iletişim odağı olarak önerilir ve o sürücünün RepTrak özellikleri (Fombrun vd. 2015, Tablo 1) listelenir. 'En zayıf sürücüye odaklan' kuralı bir tasarım kararıdır; literatür sürücülerin önem ağırlığının paydaşa ve pazara göre değiştiğini söyler (RepTrak 2026), bu nedenle öneri sınama gerektiren bir hipotezdir. Yalnızca güven aralığı ve n_eff yeterliyse (status = ok) üretilir."},
    {"kaynak": "pr", "baslik": "Yapılandırma/veri eksikliği önerileri",
     "aciklama": "Kriz geçmişinin girilmemesi, önceki itibarın bilinmemesi, L-PTİ ölçümünün olmaması gibi eksikler 'yapılacaklar' listesinde gösterilir. Bunlar SCCT yoğunlaştırıcılarının ve G13'ün doğruluğuna etki eden veri eksikleridir; PR stratejisi değil sistem yapılandırması önerisidir."},
]
