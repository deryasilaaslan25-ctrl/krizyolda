"""
PR danışmanlığı katalogu — kriz yanıt stratejileri ve seçim kuralları.

KAYNAK: Coombs, W. T. (2007). Protecting organization reputations during a crisis:
the development and application of Situational Crisis Communication Theory.
Corporate Reputation Review, 10(3), 163-176 [COOMBS2007].
  * Strateji aileleri ve tanımları: Coombs (2007) "crisis response strategies" tablosu
    (inkâr / azaltma / yeniden inşa birincil; destekleme ikincil).
  * Seçim kuralları: Coombs (2007) "SCCT crisis response strategy guidelines" (8 kural).
  * Yönlendirici (instructing) ve uyarlayıcı (adjusting) bilgi: temel yanıt.
Benoit (1997) karşılıkları yaklaşık çaprazlamadır [BENOIT1997]. Zamanlama: 'stealing thunder'
[ARPAN2005]. Evreler: Pearson & Mitroff (1993) [PEARSON_MITROFF1993]; Fink (1986) [FINK1986].

Buradaki 'uygulama_notu' alanları literatür bulgusu değil, operasyonelleştirmedir (Tasarım kararı 50).
"""
from __future__ import annotations

# --- Kriz evreleri (Pearson & Mitroff 1993) ---------------------------------------------
EVRELER = [
    {"kod": "sinyal_tespiti", "no": 1, "ad": "Sinyal tespiti", "tanim": "Kriz uyarı işaretlerinin tanımlanması ve önleyici önlem alınması.", "kaynaklar": ["PEARSON_MITROFF1993", "FINK1986"]},
    {"kod": "yoklama_onleme", "no": 2, "ad": "Yoklama ve önleme", "tanim": "Bilinen risk etkenlerinin aktif olarak aranması ve zarar potansiyelinin azaltılması.", "kaynaklar": ["PEARSON_MITROFF1993"]},
    {"kod": "hasar_sinirlama", "no": 3, "ad": "Hasar sınırlama", "tanim": "Kriz gerçekleştiğinde yayılmasını sınırlayacak eylemler.", "kaynaklar": ["PEARSON_MITROFF1993", "COOMBS2007"]},
    {"kod": "toparlanma", "no": 4, "ad": "Toparlanma", "tanim": "Normal işleyişe olabildiğince çabuk dönüş çabası.", "kaynaklar": ["PEARSON_MITROFF1993"]},
    {"kod": "ogrenme", "no": 5, "ad": "Öğrenme", "tanim": "Kriz yönetimi çabasının gözden geçirilmesi ve ondan ders çıkarılması.", "kaynaklar": ["PEARSON_MITROFF1993"]},
]

# --- Temel yanıt (Coombs 2007) -----------------------------------------------------------
TEMEL_YANIT = [
    {"kod": "yonlendirici_bilgi", "ad": "Yönlendirici bilgi (instructing information)",
     "tanim": "Krizin ne olduğu, paydaşları nasıl etkileyebileceği ve kendilerini korumak için ne yapmaları gerektiği.",
     "uygulama_notu": "İlk açıklamada olgu, etkilenen kişiler ve alınacak önlem net ve tarihli yazılır."},
    {"kod": "uyarlayici_bilgi", "ad": "Uyarlayıcı bilgi (adjusting information)",
     "tanim": "Paydaşların krizle psikolojik olarak başa çıkmasına yardım: endişe/ilgi ifadesi ve kurumun tekrarını önlemek için yaptıkları (düzeltici eylem).",
     "uygulama_notu": "Endişe ifadesi ile düzeltici eylem aynı metinde, sorumluluk üstlenme düzeyini aşmayacak biçimde verilir."},
]

# --- Stratejiler (Coombs 2007 tablosu) ---------------------------------------------------
STRATEJILER = {
    "suclayana_karsi_cikma": {"durus": "inkar", "ad": "Suçlayana karşı çıkma (attack the accuser)",
        "tanim_en": "Crisis manager confronts the person or group claiming something is wrong with the organization.",
        "tanim_tr": "İletişim yöneticisi, kurumda bir sorun olduğunu iddia eden kişi/grupla yüzleşir.",
        "benoit": "attack accuser"},
    "inkar": {"durus": "inkar", "ad": "İnkâr (denial)",
        "tanim_en": "Crisis manager asserts that there is no crisis.",
        "tanim_tr": "Kriz olmadığı ileri sürülür.", "benoit": "simple denial"},
    "sucu_baskasina_atma": {"durus": "inkar", "ad": "Suçu başkasına yükleme (scapegoat)",
        "tanim_en": "Crisis manager blames some person or group outside of the organization for the crisis.",
        "tanim_tr": "Krizin sorumlusu kurum dışındaki bir kişi/grup olarak gösterilir.", "benoit": "shift the blame"},
    "mazeret": {"durus": "azaltma", "ad": "Mazeret (excuse)",
        "tanim_en": "Crisis manager minimizes organizational responsibility by denying intent to do harm and/or claiming inability to control the events that triggered the crisis.",
        "tanim_tr": "Zarar verme niyeti olmadığı ve/veya krizi tetikleyen olaylar üzerinde kontrol bulunmadığı belirtilerek kurumsal sorumluluk küçültülür.",
        "benoit": "evading responsibility (provocation, defeasibility, accident, good intentions)"},
    "haklilastirma": {"durus": "azaltma", "ad": "Haklılaştırma (justification)",
        "tanim_en": "Crisis manager minimizes the perceived damage caused by the crisis.",
        "tanim_tr": "Krizin yol açtığı algılanan zarar küçültülür.", "benoit": "minimization"},
    "tazminat": {"durus": "yeniden_insa", "ad": "Tazminat (compensation)",
        "tanim_en": "Crisis manager offers money or other gifts to victims.",
        "tanim_tr": "Mağdurlara para ya da başka bir karşılık sunulur.", "benoit": "compensation"},
    "ozur": {"durus": "yeniden_insa", "ad": "Özür (apology)",
        "tanim_en": "Crisis manager indicates the organization takes full responsibility for the crisis and asks stakeholders for forgiveness.",
        "tanim_tr": "Kurum krizin tam sorumluluğunu üstlendiğini belirtir ve paydaşlardan af diler.", "benoit": "mortification"},
    "hatirlatma": {"durus": "destekleme", "ad": "Hatırlatma (reminder)",
        "tanim_en": "Tell stakeholders about the past good works of the organization.",
        "tanim_tr": "Paydaşlara kurumun geçmişteki iyi işleri hatırlatılır.", "benoit": "bolstering"},
    "pohpohlama": {"durus": "destekleme", "ad": "Paydaşı över/iltifat (ingratiation)",
        "tanim_en": "Crisis manager praises stakeholders and/or reminds them of past good works by the organization.",
        "tanim_tr": "Paydaşlar övülür ve/veya kurumun geçmişteki iyi işleri hatırlatılır.", "benoit": "bolstering"},
    "magduriyet": {"durus": "destekleme", "ad": "Mağduriyet (victimage)",
        "tanim_en": "Crisis managers remind stakeholders that the organization is a victim of the crisis too.",
        "tanim_tr": "Kurumun da krizin mağduru olduğu hatırlatılır.", "benoit": None},
}

DURUSLAR = {
    "temel": {"ad": "Temel yanıt (yönlendirici + uyarlayıcı bilgi)", "sira": 0},
    "inkar": {"ad": "İnkâr duruşu", "sira": 1},
    "azaltma": {"ad": "Azaltma duruşu", "sira": 2},
    "yeniden_insa": {"ad": "Yeniden inşa duruşu", "sira": 3},
    "destekleme": {"ad": "Destekleme (yalnızca tamamlayıcı)", "sira": 4},
}

# --- Coombs (2007) SCCT strateji kılavuzu — 8 kural (Türkçe özet) -------------------------
KURALLAR = [
    {"no": 1, "metin": "Sorumluluk atfı asgari olan (mağdur kümesi) krizde, benzer kriz geçmişi yoksa ve önceki ilişki itibarı nötr/olumluysa yalnızca yönlendirici ve uyarlayıcı bilgi yeterli olabilir."},
    {"no": 2, "metin": "İş yeri şiddeti, ürün kurcalama, doğal afet ve söylenti krizlerinde mağduriyet (victimage) yanıtın bir parçası olabilir."},
    {"no": 3, "metin": "Mağdur kümesi krizinde benzer kriz geçmişi ve/veya olumsuz önceki itibar varsa azaltma stratejileri kullanılmalıdır."},
    {"no": 4, "metin": "Düşük sorumluluk atfı olan (kaza kümesi) krizde, kriz geçmişi yoksa ve önceki itibar nötr/olumluysa azaltma stratejileri kullanılmalıdır."},
    {"no": 5, "metin": "Kaza kümesi krizinde kriz geçmişi ve/veya olumsuz önceki itibar varsa yeniden inşa stratejileri kullanılmalıdır."},
    {"no": 6, "metin": "Güçlü sorumluluk atfı olan (önlenebilir küme) krizde, kriz geçmişi ve önceki itibardan bağımsız olarak yeniden inşa stratejileri kullanılmalıdır."},
    {"no": 7, "metin": "Söylenti ve meydan okuma krizlerinde, mümkün olduğunda inkâr duruşu kullanılmalıdır."},
    {"no": 8, "metin": "Yanıt stratejilerinde tutarlılık korunmalıdır; inkârı azaltma ya da yeniden inşa ile karıştırmak yanıtın etkisini aşındırır."},
]

# Zamanlama ve kanal (ek kaynaklar)
ZAMANLAMA = {
    "ad": "Kriz bilgisini kurumun ilk açıklaması (stealing thunder)",
    "tanim": "Kriz bilgisinin kurum tarafından, üçüncü taraflar ortaya çıkarmadan önce proaktif olarak açıklanması.",
    "kaynaklar": ["ARPAN2005"],
    "uygulama_notu": "Kriz kaydı açıldığında ilk kurumsal açıklama, haber akışı yükselmeden (G5/G11) yayımlanacak biçimde hazırlanır.",
}
KANAL = {
    "ad": "Kanal ve yankı odası",
    "tanim": "Risk sinyalleri medya ve kişilerarası ağlar gibi 'yükseltme istasyonlarında' işlenir; haber ve sosyal medya birlikte yükseliyorsa (G11 yüksek) tek bir tutarlı açıklama iki mecrada eşzamanlı yayımlanmalıdır. Mecra seçiminin krize verilen tepkiyi etkilediği gösterilmiştir.",
    "kaynaklar": ["KASPERSON1988", "SCHULTZ2011"],
}

# Baskın küme + yoğunlaştırıcı → duruş (kural numaralarıyla)
KUME_DURUS = {"magdur": "temel", "kaza": "azaltma", "onlenebilir": "yeniden_insa"}
VICTIMAGE_TIPLERI = ("dogal_afet", "soylenti", "isyeri_siddeti", "kurcalama")
INKAR_TIPLERI = ("soylenti", "meydan_okuma")

# Kümeye özgü hazır yanıt iskeleti (operasyonelleştirme — literatür bulgusu değildir)
ISKELET = {
    "temel": ["Olgu ve etkilenenler (yönlendirici bilgi)", "Endişe ifadesi", "Kurumun aldığı/alacağı düzeltici eylem (uyarlayıcı bilgi)"],
    "azaltma": ["Temel yanıt", "Niyet/kontrol dışı etken (mazeret) ya da zararın boyutu (haklılaştırma) — yalnız doğrulanmış olgularla"],
    "yeniden_insa": ["Temel yanıt", "Sorumluluğun üstlenilmesi ve özür", "Tazminat/telafi imkânı", "Tekrarlanmaması için somut düzeltici eylem"],
}
