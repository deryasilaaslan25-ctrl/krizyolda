import { api } from "./api-client";
import type { Alarm, BeyinYaniti, BildirimKaydi, BilgiProfili, KaynakYaniti, KontrolListesi, PROlcutleri, TaramaIsi, TaramaListesi, UzmanForm, AnalizSonucu, Icerik, Kullanici, KrizStratejisi, LptiDalga, LptiGrup, LptiSonuc, LptiSurucu, PRBrif, Profil, RiskOzeti } from "./domain";

type TokenYaniti = { access_token: string; kullanici: Kullanici };

export async function girisApi(email: string, sifre: string) {
  const f = new URLSearchParams({ username: email, password: sifre });
  return (await api.post<TokenYaniti>("/api/auth/giris", f)).data;
}
export async function kayitApi(email: string, sifre: string, sifre_tekrar: string, kurum: string, sektor: string,
  bildirim_ek_epostalar: string[] = []) {
  return (await api.post<TokenYaniti>("/api/auth/kayit", { email, sifre, sifre_tekrar, kurum, sektor, bildirim_ek_epostalar })).data;
}
export const dogrulamaGonderApi = async () => (await api.post("/api/auth/dogrulama-gonder")).data;
export const epostaDogrulaApi = async (token: string) => (await api.post("/api/auth/eposta-dogrula", { token })).data;
export const sifreSifirlaIsteApi = async (email: string) => (await api.post("/api/auth/sifre-sifirla-iste", { email })).data;
export const sifreSifirlaApi = async (token: string, yeni_sifre: string) => (await api.post("/api/auth/sifre-sifirla", { token, yeni_sifre })).data;
export const benApi = async () => (await api.get<Kullanici>("/api/auth/ben")).data;
export const sifreDegistirApi = async (mevcut_sifre: string, yeni_sifre: string) =>
  (await api.post("/api/auth/sifre-degistir", { mevcut_sifre, yeni_sifre })).data;
export const emailDegistirApi = async (yeni_email: string, sifre: string) =>
  (await api.post<TokenYaniti>("/api/auth/email-degistir", { yeni_email, sifre })).data;

export const profilApi = async () => (await api.get<Profil>("/api/kurum/profil")).data;
export const profilGuncelleApi = async (g: Record<string, unknown>) =>
  (await api.put<Kullanici>("/api/kurum/profil", g)).data;

export const sonAnalizApi = async () => (await api.get<AnalizSonucu>("/api/analiz/son")).data;
export const yenidenHesaplaApi = async () => (await api.post<AnalizSonucu>("/api/analiz/yeniden-hesapla")).data;

export const alarmlarApi = async () => (await api.get<Alarm[]>("/api/alarmlar")).data;
export const geriBildirimApi = async (id: number, geri_bildirim: string | null, not_metni = "") =>
  (await api.post<Alarm>(`/api/alarmlar/${id}/geri-bildirim`, { geri_bildirim, not_metni })).data;
export type Degerlendirme = { seviyeler: { min_seviye: number; etiket: string; dogru_alarm: number; yanlis_alarm: number;
  kesinlik: number | null; guven_araligi_95: [number, number] | null }[] };
export const degerlendirmeApi = async () => (await api.get<Degerlendirme>("/api/alarmlar/degerlendirme")).data;

export const iceriklerApi = async (p: Record<string, string | number | boolean>) =>
  (await api.get<{ toplam: number; ogeler: Icerik[] }>("/api/icerikler", { params: p })).data;
export async function trendsCsvApi(dosya: File, utcFarki: number) {
  const f = new FormData();
  f.append("dosya", dosya);
  f.append("utc_farki_saat", String(utcFarki));
  return (await api.post<{ aktarilan: number; ilk: string; son: string }>("/api/trends/csv", f)).data;
}

export const literaturApi = async () => (await api.get<Record<string, unknown>>("/api/literatur")).data;

// ---- E-postadan geri bildirim (oturumsuz) ----
export type EpostaAlarm = Alarm & { kurum: string };
export const epostaOnizleApi = async (token: string) => (await api.get<EpostaAlarm>("/api/geri-bildirim/onizle", { params: { token } })).data;
export const epostaGeriBildirimApi = async (token: string, karar: "gercek_kriz" | "onemsiz") =>
  (await api.post<EpostaAlarm>("/api/geri-bildirim/e-posta", { token, karar })).data;

// ---- Eşik ----
export type EsikDurumu = { son: RiskOzeti | null; p: Record<string, number>; donus_saatleri: Record<string, number>; z_tavan: number;
  seviyeler: { seviye: number; etiket: string; eylem: string }[]; etiketler: { gercek: number; onemsiz: number; duzeltme_icin_gerekli: string };
  olcum_sayisi: number };
export const esikDurumuApi = async () => (await api.get<EsikDurumu>("/api/esik/durum")).data;

// ---- PR danışmanlığı ----
export const prBrifApi = async () => (await api.get<PRBrif>("/api/pr/brif")).data;
export const prStratejiApi = async (alarm_id?: number) =>
  (await api.get<KrizStratejisi>("/api/pr/strateji", { params: alarm_id ? { alarm_id } : {} })).data;

// ---- L-PTİ ----
export const itibarDalgalariApi = async () => (await api.get<LptiDalga[]>("/api/reputation/waves")).data;
export const itibarSkorApi = async (w: number) => (await api.get<LptiSonuc>(`/api/reputation/waves/${w}/scores`)).data;
export const itibarSurucuApi = async (w: number) => (await api.get<{ drivers: LptiSurucu[] }>(`/api/reputation/waves/${w}/drivers`)).data;
export const itibarKaliteApi = async (w: number) => (await api.get<{ quality: NonNullable<LptiSonuc["quality"]> }>(`/api/reputation/waves/${w}/quality`)).data;
export const itibarPuanlaApi = async (w: number, g: { precision_target: number; pi?: Record<string, number> | null; dogrulama_zorunlu: boolean; min_items: number }) =>
  (await api.post<LptiSonuc>(`/api/reputation/waves/${w}/score-runs`, g)).data;
export type { LptiGrup };

// ---- Tarama, kaynaklar, bildirimler ----
export const taramaBaslatApi = async () => (await api.post<TaramaIsi>("/api/tarama")).data;
export const taramaListesiApi = async () => (await api.get<TaramaListesi>("/api/tarama")).data;
export const taramaIptalApi = async (id: number) => (await api.post<TaramaIsi>(`/api/tarama/${id}/iptal`)).data;
export const kaynaklarApi = async () => (await api.get<KaynakYaniti>("/api/kaynaklar")).data;
export const kaynakSaglikApi = async () => (await api.get<{ kaynak: string; zaman: string; durum: string; adet: number; mesaj: string;
  istenen_bas: string | null; ulasilan_bas: string | null }[]>("/api/kaynaklar/saglik")).data;
export const baglantiKaydetApi = async (platform: string, hesap_ref: string, gizli?: string) =>
  (await api.put<{ baglanti: unknown; test: { basarili: boolean; mesaj?: string; neden?: string; tarih_siniri?: string; veri_turleri?: string[]; kota?: string } }>(
    `/api/kaynaklar/baglanti/${platform}`, { hesap_ref, gizli: gizli || undefined })).data;
export const baglantiTestApi = async (platform: string) =>
  (await api.post<{ test: { basarili: boolean; mesaj?: string; tarih_siniri?: string; veri_turleri?: string[]; kota?: string } }>(`/api/kaynaklar/baglanti/${platform}/test`)).data;
export const baglantiSilApi = async (platform: string) => (await api.delete(`/api/kaynaklar/baglanti/${platform}`)).data;
export const testEpostaApi = async () => (await api.post<{ alicilar: string[]; gonderilen: number; tekrar: number; kalici_hata: number }>("/api/kurum/test-eposta")).data;
export const bildirimlerApi = async () => (await api.get<{ ozet: Record<string, number>; smtp_hazir: boolean; kayitlar: BildirimKaydi[] }>("/api/kurum/bildirimler")).data;
export const bilgiProfiliApi = async () => (await api.get<BilgiProfili>("/api/kurum/bilgi-profili")).data;
export const alarmYanitApi = async (id: number, g: { ilk_yanit_zamani?: string | null; cozum_zamani?: string | null }) =>
  (await api.put<Alarm>(`/api/alarmlar/${id}/yanit`, g)).data;

// ---- İki beyin ve uzman paneli ----
export const beyinApi = async () => (await api.get<BeyinYaniti>("/api/beyin")).data;
export const uzmanFormlariApi = async () => (await api.get<UzmanForm[]>("/api/uzman/formlar")).data;
export const uzmanFormOlusturApi = async (g: Omit<UzmanForm, "id" | "aktif" | "uzman_sayisi" | "tam_uzman" | "olusturma">) =>
  (await api.post<UzmanForm>("/api/uzman/formlar", g)).data;
export const uzmanFormDurumApi = async (id: number, aktif: boolean) => (await api.post(`/api/uzman/formlar/${id}/${aktif ? "aktif" : "pasif"}`)).data;
export const uzmanPuanlariApi = async (id: number) =>
  (await api.get<{ form: UzmanForm; uzmanlar: Record<string, { puanlar: Record<string, number>; gerekceler: Record<string, string> }> }>(`/api/uzman/formlar/${id}/puanlar`)).data;
export const uzmanKaydetApi = async (id: number, kod: string, puanlar: Record<string, number>, gerekceler: Record<string, string>) =>
  (await api.put(`/api/uzman/formlar/${id}/uzmanlar/${kod}`, { puanlar, gerekceler })).data;
export const uzmanSilApi = async (id: number, kod: string) => (await api.delete(`/api/uzman/formlar/${id}/uzmanlar/${kod}`)).data;
export const uzmanGostergeleriApi = async () => (await api.get<{ kod: string; ad: string; olcum: string }[]>("/api/uzman/gostergeler")).data;

// ---- PR danışmanı: süreç ----
export const prHaftalikGonderApi = async () => (await api.post<{ alicilar: string[] }>("/api/pr/haftalik-gonder")).data;
export const kontrolListesiApi = async (alarm_id = 0) => (await api.get<KontrolListesi>("/api/pr/kontrol-listesi", { params: { alarm_id } })).data;
export const kontrolIsaretleApi = async (madde: string, tamam: boolean, alarm_id = 0) =>
  (await api.put("/api/pr/kontrol-listesi", { madde, tamam, alarm_id })).data;
export const prOlcutleriApi = async () => (await api.get<PROlcutleri>("/api/pr/olcutler")).data;
