/** Backend yanıt tipleri (backend/app/indicators/analysis.py ile birebir). */
export type Seviye = 0 | 1 | 2 | 3;

export interface Kullanici {
  id: number;
  email: string;
  kurum: string;
  sektor: string;
  rol: string;
  izleme_terimleri: string[];
  kriz_gecmisi: string[];
  onceki_itibar: "olumlu" | "notr" | "olumsuz" | null;
  bildirim_email: boolean;
  bildirim_slack: boolean;
  bildirim_min_seviye: number;
  bildirim_ek_epostalar: string[];
  bildirim_haftalik: boolean;
  eposta_gonderimi_hazir: boolean;
  eposta_dogrulandi: boolean;
  web_sitesi: string;
  resmi_hesaplar: { platform: string; hesap: string }[];
  haric_terimler: string[];
  ek_rss: string[];
  acik_kaynak: boolean;
  aralik_turu: "7" | "30" | "90" | "180" | "ozel";
  ozel_baslangic: string | null;
  ozel_bitis: string | null;
  tekrar_plani: "periyodik" | "tek_seferlik";
  tarama_min_dk: number;
  tarama_max_dk: number;
  tarama_aralik_dk: number | null;
  sonraki_tarama: string | null;
  bildirim_bekleme_saat: number;
  rapor_gunu: number;
  rapor_saati: number;
  en_fazla_analiz_gun: number;
}

export interface KrizTipi { anahtar: string; ad: string; kume: "magdur" | "kaza" | "onlenebilir"; }
export interface Profil extends Kullanici { kriz_tipleri: KrizTipi[]; }

export type GostergeDegerleri = Record<string, number | null>;

export interface Pencere {
  bas: string;
  icerik_sayisi: number;
  sosyal_sayisi: number;
  haber_sayisi: number;
  gostergeler: GostergeDegerleri;
  skorlar: GostergeDegerleri;
  kre: number | null;
  z: number | null;
  yuzdelik: number | null;
  z_yontemi: string;
  seviye: Seviye;
  etiket: string;
  kurallar: number[];
  sessiz_birikim?: boolean;
  risk_uzman?: number | null; z_uzman?: number | null;
  risk_puani?: number | null; risk_ham?: Seviye | null; risk_seviye?: Seviye | null; risk_esik_yuksek?: number | null;
  isinmada: boolean;
  eksik?: boolean;
  baskin_kume: string | null;
  tehdit: string;
}

export interface Kalibrasyon {
  bolgeler: { k_sigma: number; gozlenen: number; n: number; gozlenen_oran: number; nominal_oran: number;
    guven_araligi_95: [number, number]; durum: "uyumlu" | "şişme" | "daralma" }[];
}

export interface RiskOzeti {
  saat: string; puan: number; z: number | null; z_tavan: number; hacim_z: number | null;
  ham_seviye: Seviye; nihai_seviye: Seviye; etiket: string; ham_etiket: string;
  esikler: { orta: number; yuksek: number; kritik: number };
  kaynak: string; yontemler: Record<string, string>; guvenilirlik_z: number; n_blok: number; olcek_s: number;
  p: number | null; donus_saat: number | null; donus_metni: string | null; korkuluk: string[];
  histerezis: { yon?: string; kod?: string; metin?: string; delta?: number; hacim_sok?: boolean };
  aciklama: string;
  gpd: { u: number; lam_u: number; sigma: number; xi: number; m: number; gecerli: boolean } | null;
  onsel: [number, number, number] | null; onsel_kaynak: string | null;
  kurum_tahmini: [number | null, number | null, number | null] | null;
  etiket_duzeltme: { c_star: number; z_e: number; m: number; onceki_yuksek: number; gercek: number; siradan: number } | null;
  esige_oran: number | null; alarm_id: number | null; gecmis: boolean;
}

export interface SonPencere extends Pencere {
  risk: RiskOzeti | null;
  weco_seviye: Seviye;
  agirliklar: Record<string, number>;
  uzman_agirliklar?: Record<string, number>;
  katkilar: Record<string, number>;
  kirpilmis: Record<string, number>;
  boyut_katkilari: Record<string, number | null>;
  ham_esikler: Record<string, Record<string, number | null>>;
  asim: { p: number; n_gecmis: number; donus_suresi_saat: number; normal_teori_p: number } | null;
  kalibrasyon: Kalibrasyon | null;
}

export interface AlarmDonemi {
  baslangic: string; bitis: string; max_seviye: Seviye; max_etiket: string; kurallar: number[]; acik: boolean;
}
export interface Bildirim { alarm: number; karar: string; neden?: string; kanallar?: string[] }

export interface AnalizSonucu {
  durum?: string;
  zaman?: string;
  kurum: string;
  baslangic: string;
  bitis: string;
  bin_saat: number;
  pencere_sayisi: number;
  isinma_pencere: number;
  isinmada: boolean;
  onceki_itibar: { deger: string | null; kaynak: string; jf: number | null; lpti?: { skor: number; ci95: [number, number]; kaynak: string } };
  kriz_gecmisi: string[];
  pencereler: Pencere[];
  son: SonPencere;
  g1_zirveleri: { bas: string; son: string }[];
  eksik_gostergeler: string[];
  uyarilar: string[];
  alarm_donemleri: AlarmDonemi[];
  yontem?: { duygu_motoru: string; scct_motoru: string; z_yontemi: string; nrc_yuklu: boolean };
  kaynak_durumlari?: { kaynak: string; durum: string; mesaj: string; adet: number }[];
  aralik: { tur: string; bas: string; bit: string; canli: boolean };
  kaynak_ozeti: KaynakOzeti[];
  kaynak_kapsami: { kaynaklar: Record<string, { kapsanan_pencere: number; oran: number; ilk: string | null; son: string | null }>;
    degisimler: { bas: string; eklenen: string[]; cikan: string[] }[] };
  beyin: BeyinKarsilastirma;
  bildirimler: Bildirim[];
  esik?: { durum: string; islenen_olcum: number };
}

export interface Alarm {
  id: number; baslangic: string; bitis: string; acik: boolean; max_seviye: Seviye; max_etiket: string;
  kurallar: number[]; baskin_kume: string | null; tehdit: string | null; max_z: number | null; max_risk: number | null;
  saat_sayisi: number; geri_bildirim: "gercek_kriz" | "yanlis_alarm" | null; not_metni: string;
  ilk_yanit_zamani: string | null; cozum_zamani: string | null; bildirim_kuyrugu: Record<string, number>;
  bildirim_durumu: "yok" | "kuyruga_alindi" | "gecmis" | "bastirildi" | "alici_yok" | "kapali" | "gonderilemedi";
  bildirim_seviye: number; bastirma_nedeni: string; benzer_alarm_id: number | null; terimler: string[]; tip: string | null;
  benzer_onemsiz_sayisi?: number;
}

export interface Icerik {
  id: number; platform: string; tur: "sosyal" | "haber"; erisim: "acik" | "bagli"; icerik_turu: string; yazar: string | null; baslik: string; metin: string;
  url: string; tarih: string; begeni: number; yorum: number; paylasim: number;
  duygu_etiketi: "olumlu" | "olumsuz" | "notr" | null;
  duygu: { olumlu?: number; olumsuz?: number; ofke?: number; korku?: number; igrenme?: number; toplam_sozcuk?: number;
    motor?: string; kanitlar?: { sozcuk: string; girdi: string; etiketler: string[]; olumsuzlandi: boolean }[] };
  niyet: string[];
  scct: { seviye?: number; baslangic_seviye?: number; tip?: string | null; tip_adi?: string | null; kume?: string | null };
}

export interface Kaynak { atif: string; url: string; }
export interface Gosterge {
  kod: string; grup: string; ad: string; boyut?: string; veri?: string; olcum?: string; gerekce: string; kaynaklar: string[];
}
export interface TasarimKarari { no: number; kaynak: string; baslik: string; aciklama: string; }

/** WECO kural katmanı (açıklayıcı sinyal). */
export const SEVIYE_ETIKETI: Record<number, string> = { 0: "NORMAL", 1: "ERKEN UYARI", 2: "YÜKSEK UYARI", 3: "KRİZ" };
/** Kuruma özgü eşik katmanı (karar): Metodoloji Bölüm 2. */
export const RISK_ETIKETI: Record<number, string> = { 0: "DÜŞÜK RİSK", 1: "ORTA RİSK", 2: "YÜKSEK RİSK", 3: "KRİTİK RİSK" };
export const RISK_EYLEMI: Record<number, string> = {
  0: "Olağan dalgalanma; işlem yok.", 1: "İzleme; panelde işaret.", 2: "Kriz kaydı açılır, bildirim gider.", 3: "Kriz kaydı + acil öncelik.",
};
export const BILDIRIM_DURUMU: Record<string, string> = {
  yok: "Beklemede", gonderildi: "E-posta gönderildi", gecmis: "Geçmiş kayıt (bildirim yok)", bastirildi: "Bastırıldı",
  smtp_yok: "E-posta ayarı yok", kapali: "Bildirim kapalı",
};
export const SEVIYE_RENK: Record<number, string> = {
  0: "bg-emerald-50 text-emerald-800 border-emerald-200",
  1: "bg-amber-50 text-amber-800 border-amber-200",
  2: "bg-orange-50 text-orange-800 border-orange-300",
  3: "bg-red-50 text-red-800 border-red-300",
};
export const BOYUT_ADI: Record<string, string> = {
  DIKKAT: "Dikkat", TONALITE: "Tonalite", UYARILMISLIK: "Uyarılmışlık", YAYILIM: "Yayılım",
  NIYET: "Davranış niyeti", SORUMLULUK: "Sorumluluk",
};
export const KUME_ADI: Record<string, string> = { magdur: "Mağdur", kaza: "Kaza", onlenebilir: "Önlenebilir" };
export const PLATFORM_ADI: Record<string, string> = {
  google_news: "Google Haber", bing_news: "Bing Haber", rss: "RSS", reddit: "Reddit", youtube: "YouTube", x: "X", instagram: "Instagram",
};

// ---- PR danışmanlığı ----------------------------------------------------------------------
export interface StratejiOgesi { kod: string; ad: string; durus: string; tanim_tr: string; tanim_en: string; benoit_karsiligi: string | null }
export interface KrizStratejisi {
  alarm_id?: number; durum: string; kume: string | null; kume_adi?: string; tehdit?: string; tip: string | null; tip_adi?: string | null;
  yogunlastirici?: boolean; durus: string; durus_kodu?: string;
  temel_yanit: { kod: string; ad: string; tanim: string; uygulama_notu: string }[];
  birincil: StratejiOgesi[]; destekleyici: StratejiOgesi[];
  kosullu: { kural: number; stratejiler: StratejiOgesi[]; kosul: string }[];
  kurallar: { no: number; metin: string }[]; kacinilacaklar?: string[]; adimlar?: string[]; iskelet?: string[];
  zamanlama?: { ad: string; tanim: string; uygulama_notu: string; kaynaklar: string[] } | null;
  kanal?: { ad: string; tanim: string; kaynaklar: string[] } | null;
  aciklama: string; kaynaklar: string[];
}
export interface Yapilacak { oncelik: number; baslik: string; gerekce: string; kaynaklar: string[] }
export interface PRBrif {
  zaman: string; kurum: string; analiz_var: boolean; mesaj?: string;
  evre: { kod: string; no: number; ad: string; tanim: string; neden: string; kaynaklar: string[]; tum_evreler: { kod: string; no: number; ad: string }[] };
  sinyal_radari?: {
    risk: { puan: number; etiket: string; esikler: { orta: number; yuksek: number; kritik: number }; esige_oran: number | null;
      donus_metni: string | null; kaynak: string; guvenilirlik_z: number; n_blok: number; son7_orta_ve_uzeri_saat: number;
      son7_yuksek_saat: number; olculen_saat_son7: number; kaynaklar: string[] } | null;
    zayif_sinyaller: { kod: string; ad: string; boyut: string; pencere_sayisi: number; son_skor: number | null; kaynaklar: string[] }[];
    weco: { kurallar: number[]; sessiz_birikim: boolean; etiket?: string; kaynaklar: string[] };
    hafta: { icerik: { bu_hafta: number; onceki_hafta: number }; olumsuzluk_G6: { bu_hafta: number | null; onceki_hafta: number | null };
      haber_olumsuzlugu_G7: { bu_hafta: number | null; onceki_hafta: number | null }; kanit: string } | null;
    sinyal_kaynak: { boyut: string; katki: number }[];
  };
  kirilganlik?: {
    yogunlastiricilar: { kriz_gecmisi: string[]; onceki_itibar: string | null; onceki_itibar_kaynak: string | null; aciklama: string };
    son30_kriz_tipleri: { tip: string; ad: string; kume: string; kume_adi: string; adet: number }[];
    kume_dagilimi: Record<string, number>; hazirlik_stratejisi: KrizStratejisi; kaynaklar: string[];
  };
  itibar?: {
    durum: "var" | "yok"; mesaj?: string; dalga?: number; dalga_adi?: string; genel_skor?: number | null;
    gruplar?: LptiGrup[]; surucular?: LptiSurucu[];
    en_zayif_surucu?: { surucu: string; ad: string; grup: string; skor: number; ci95: [number, number]; ozellikler: string; oneri: string } | null;
    kaynaklar: string[];
  };
  ogrenme?: { alarm_sayisi: number; gercek: number; onemsiz: number; etiketsiz: number; bastirilan_bildirim: number;
    esik_etiket_duzeltmesi: boolean; kesinlik: number | null; mesaj: string; kaynaklar: string[] };
  kriz_stratejisi?: KrizStratejisi | null;
  yapilacaklar: Yapilacak[];
}

// ---- L-PTİ ----------------------------------------------------------------------------------
export type LptiDurum = "ok" | "insufficient_data" | "invalid_instrument" | "invariance_not_established";
export interface LptiGrup {
  group: string; score: number | null; estimate: number | null; se: number | null; ci95: [number, number] | null;
  n: number; n_eff: number | null; deff_kish?: number | null; status: LptiDurum; reason: string | null;
  dislanan?: Record<string, number>; raking?: boolean;
}
export interface LptiSurucu {
  group: string; driver: string; driver_adi?: string; score: number | null; estimate: number | null; se: number | null;
  ci95: [number, number] | null; n: number; n_eff: number | null; status: LptiDurum;
}
export interface LptiSonuc {
  construct: string; model: string; instrument_version: string; wave_id: number; run_id: number;
  params: Record<string, unknown>; overall_score: number | null;
  overall: { score: number | null; estimate: number | null; se: number | null; ci95: [number, number] | null; reason: string | null };
  stakeholder_scores: LptiGrup[]; drivers?: LptiSurucu[];
  quality: { invariance_level: string | null; missing_rate: number | null; validation_bypassed?: boolean;
    gruplar?: { group: string; omega: number | null; estimator: string; missing_rate: number | null; invariance_level: string | null;
      dogrulama_durumu: string; dogrulama_kaynagi: string | null }[] };
  comparison: { durum: string; delta: { group: string; delta: number; se: number; ci95: [number, number]; anlamli: boolean }[]; neden?: string };
}
export interface LptiDalga { id: number; name: string; instrument_id: number; status: string;
  yanit_sayisi: number; son_kosu: number | null; overall_score: number | null }
export const LPTI_DURUM_ADI: Record<string, string> = {
  ok: "Geçerli", insufficient_data: "Yetersiz veri", invalid_instrument: "Araç doğrulanmamış",
  invariance_not_established: "Değişmezlik sağlanmadı",
};
export const GRUP_ADI: Record<string, string> = {
  customers: "Müşteriler", employees: "Çalışanlar", investors: "Yatırımcılar",
  suppliers_regulators: "Tedarikçi / düzenleyici", general_public: "Genel kamuoyu",
};
export const SURUCU_ADI: Record<string, string> = {
  products_services: "Ürün ve hizmetler", innovation: "Yenilik", workplace: "İşyeri", conduct: "Davranış / yönetişim",
  citizenship: "Vatandaşlık", leadership: "Liderlik", performance: "Performans",
};


// ---- Kaynaklar, işler, iki beyin ---------------------------------------
export type KaynakDurumKodu = "baglanti_yok" | "kapali" | "taranmadi" | "hata" | "kapsam_yok" | "icerik_yok" | "icerik_var";
export interface KaynakOzeti {
  kaynak: string; ad: string; tur: "sosyal" | "haber"; durum: KaynakDurumKodu; etkin: boolean; icerik: number;
  kapsam_orani: number; son_tarama: string | null; son_durum: string | null; mesaj: string; ulasilan_bas: string | null;
}
export interface Baglanti {
  platform: string; hesap_ref: string; durum: "dogrulanmadi" | "bagli" | "yetki_yok" | "hata"; gizli_alan: string; maske: string;
  son_test: string | null; son_basari: string | null; son_hata: string; kapsam: Record<string, unknown>;
}
export interface KaynakYaniti {
  aralik: { bas: string; bit: string; tur: string }; acik_kaynak: boolean; kaynaklar: KaynakOzeti[];
  baglantilar: Record<string, Baglanti>; platformlar: { platform: string; gizli_alan: string; hesap_alan: string }[];
}
export interface TaramaIsi {
  id: number; tur: string; durum: "bekliyor" | "calisiyor" | "tamam" | "kismi" | "hata" | "iptal"; bas: string; bit: string;
  olusturma: string; baslama: string | null; bitis: string | null; yeni_icerik: number; mesaj: string; tetikleyen: string;
  kaynaklar: { kaynak: string; durum: string; adet: number; mesaj: string }[];
}
export interface TaramaListesi {
  isler: TaramaIsi[]; plan: { tekrar_plani: string; aralik_dk: number | null; sonraki: string | null; tek_seferlik_yapildi: boolean };
}
export interface BildirimKaydi {
  id: number; tur: string; alici: string; konu: string; durum: string; deneme: number; son_hata: string; olusturma: string;
  gonderim: string | null; sonraki_deneme: string | null; alarm_id: number | null;
}
export interface BeyinGostergesi { kod: string; ad: string; boyut: string; agirlik1: number; agirlik2: number | null; uzman_puani: number | null;
  yayilim: { min: number; max: number; std: number } | null }
export interface BeyinKarsilastirma {
  etkin: boolean; neden?: string; aciklama?: string; form?: string; gerekli_uzman?: number; tam_uzman?: number;
  son?: { bas: string; r1: number | null; r2: number | null; fark: number | null; z1: number | null; z2: number | null; seviye1: number | null;
    seviye2: number | null; etiket1: string | null; etiket2: string | null; yuzdelik1: number | null; yuzdelik2: number | null };
  donem?: { n: number; korelasyon: number | null; ortalama_mutlak_fark: number | null; r1_ortalama: number | null; r2_ortalama: number | null };
  katkilar?: { kod: string; ad: string; w1: number | null; w2: number | null; skor: number | null; katki1: number | null; katki2: number | null; fark: number | null }[];
  seri?: { bas: string; r1: number; r2: number }[];
}
export interface BeyinYaniti {
  beyin1: { aciklama: string; toplam: number };
  beyin2: { etkin: boolean; neden?: string; aciklama?: string; form?: string; soru?: string; olcek?: [number, number]; birlestirme?: string;
    gerekli_uzman?: number; tam_uzman?: number; girilen_uzman?: number; uzman_sayisi?: number; kendall_w?: number | null };
  gostergeler: BeyinGostergesi[]; karsilastirma: BeyinKarsilastirma | null;
}
export interface BilgiProfili {
  aralik: { bas: string; bit: string; gun: number }; toplam: number; gunluk_ortalama: number; haftalik_ortalama: number;
  duygu: Record<string, number>; olumsuz_oran: number | null; olagan_duzey: { medyan: number; q1: number; q3: number } | null;
  hafta_ritmi: { gun: string; ortalama: number | null; gun_sayisi: number }[];
  gunluk: { tarih: string; sosyal: number; haber: number; olumsuz: number; olumlu: number; notr: number; toplam: number; etkilesim: number }[];
  haftalik: { hafta: string; toplam: number; olumsuz: number; olumsuz_oran: number | null }[];
  kaynak_dagilimi: { kaynak: string; ad: string; adet: number }[]; konular: { konu: string; adet: number }[];
  kaynak_ozeti: KaynakOzeti[]; kapsam_orani: number; sinirlama: string;
}
export interface KontrolListesi {
  kaynak: { ad: string; url: string }; evreler: { kod: string; ad: string; aciklama: string }[];
  maddeler: { kod: string; evre: string; metin: string }[]; yanit_hedefleri: { tur: string; yaklasim: string; hedef: string }[];
  olcutler: { kod: string; ad: string; tanim: string }[]; alarm_id: number; tamamlanan: string[];
}
export interface PROlcutleri {
  alarmlar: { alarm_id: number; baslangic: string; acik: boolean; max_seviye: number; ilk_yanit_dk: number | null; cozum_dk: number | null;
    sosyal_icerik: number; olumsuz_oran: number | null }[];
  ozet: { alarm_sayisi: number; ilk_yanit_medyan_dk: number | null; cozum_medyan_dk: number | null };
}
export interface UzmanForm {
  id: number; surum: string; soru: string; olcek_min: number; olcek_max: number; birlestirme: "ortalama" | "medyan"; min_uzman: number;
  aktif: boolean; uzman_sayisi: number; tam_uzman: number; olusturma: string;
}
