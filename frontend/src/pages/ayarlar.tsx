import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useApp } from "@/lib/app-context";
import { bildirimlerApi, profilApi, profilGuncelleApi, sifreDegistirApi, testEpostaApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { KUME_ADI, type Profil } from "@/lib/domain";
import { tarihSaat } from "@/lib/format";
import { Alan, Bos, Dugme, Kart, Rozet, Sayfa, Sekmeler, Uyari, girdiSinifi } from "@/components/ortak";

type Sekme = "marka" | "tarama" | "bildirim" | "hesap";
const satirlar = (m: string) => m.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);
const GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
const HESAP_PLATFORMLARI = ["x", "instagram", "youtube", "tiktok", "linkedin", "facebook", "web"];
const KUYRUK_ADI: Record<string, [string, "yesil" | "sari" | "kirmizi" | "gri"]> = {
  smtp_kabul: ["SMTP kabul etti", "yesil"], kuyrukta: ["Kuyrukta", "gri"], gonderiliyor: ["Gönderiliyor", "gri"],
  tekrar_bekliyor: ["Yeniden denenecek", "sari"], kalici_hata: ["Gönderilemedi", "kirmizi"], bastirildi: ["Bastırıldı", "gri"],
};

export default function Ayarlar() {
  const [sekme, setSekme] = useState<Sekme>("marka");
  const q = useQuery({ queryKey: ["profil"], queryFn: profilApi });
  return (
    <Sayfa baslik="Ayarlar">
      <Sekmeler deger={sekme} degistir={setSekme} secenekler={[
        { kod: "marka", ad: "Marka profili" }, { kod: "tarama", ad: "Veri kapsamı ve tarama" }, { kod: "bildirim", ad: "Bildirimler" }, { kod: "hesap", ad: "Hesap" }]} />
      {q.isLoading || !q.data ? <Bos>Yükleniyor…</Bos> : sekme === "marka" ? <Marka p={q.data} /> : sekme === "tarama" ? <Tarama p={q.data} /> : sekme === "bildirim" ? <Bildirim p={q.data} /> : <Hesap p={q.data} />}
    </Sayfa>
  );
}

function useKaydet() {
  const qc = useQueryClient();
  const { yenile } = useApp();
  return useMutation({
    mutationFn: (g: Record<string, unknown>) => profilGuncelleApi(g),
    onSuccess: async () => {
      await yenile();
      qc.invalidateQueries();
      toast.success("Kaydedildi.");
    },
    onError: (e) => toast.error(apiHataMesaji(e)),
  });
}

function Marka({ p }: { p: Profil }) {
  const kaydet = useKaydet();
  const [f, setF] = useState({ kurum: p.kurum, sektor: p.sektor, web: p.web_sitesi, terimler: p.izleme_terimleri.join("\n"), haric: p.haric_terimler.join("\n"),
    rss: p.ek_rss.join("\n"), krizler: p.kriz_gecmisi, itibar: p.onceki_itibar ?? "otomatik" });
  const [hesaplar, setHesaplar] = useState(p.resmi_hesaplar);
  const ac = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  return (
    <div className="space-y-4">
      <Kart baslik="Marka tanımı" aciklama="Tarama bu terimlerle yapılır. Aynı isimli işletme ve ürünlerle karışmayı azaltmak için alternatif yazımları ve hariç tutulacak terimleri girin.">
        <div className="grid gap-4 md:grid-cols-2">
          <Alan etiket="Kurum / marka adı"><input className={girdiSinifi} value={f.kurum} onChange={ac("kurum")} /></Alan>
          <Alan etiket="Sektör"><input className={girdiSinifi} value={f.sektor} onChange={ac("sektor")} /></Alan>
          <Alan etiket="Resmî web sitesi"><input className={girdiSinifi} value={f.web} onChange={ac("web")} placeholder="https://" /></Alan>
          <div />
          <Alan etiket="Arama terimleri" yardim="Her satıra bir terim: marka adı, alternatif yazımlar, ürün adları. Boşsa kurum adı kullanılır.">
            <textarea rows={5} className={girdiSinifi} value={f.terimler} onChange={ac("terimler")} />
          </Alan>
          <Alan etiket="Hariç tutulacak terimler" yardim="Bu sözcükleri içeren içerikler analize alınmaz (aynı isimli başka işletmeler için).">
            <textarea rows={5} className={girdiSinifi} value={f.haric} onChange={ac("haric")} />
          </Alan>
          <Alan etiket="Ek RSS adresleri" yardim="Her satıra bir adres (en fazla 10). Başlık ya da açıklamasında terimleriniz geçen öğeler alınır.">
            <textarea rows={3} className={girdiSinifi} value={f.rss} onChange={ac("rss")} placeholder="https://…/rss" />
          </Alan>
        </div>
      </Kart>
      <Kart baslik="Resmî hesaplar" aciklama="Marka doğrulaması ve raporlar için. API bağlantısı için Kaynaklar sayfasını kullanın.">
        <div className="space-y-2">
          {hesaplar.map((h, i) => (
            <div key={i} className="flex gap-2">
              <select className={`${girdiSinifi} max-w-36`} value={h.platform} onChange={(e) => setHesaplar(hesaplar.map((x, j) => (j === i ? { ...x, platform: e.target.value } : x)))}>
                {HESAP_PLATFORMLARI.map((x) => <option key={x}>{x}</option>)}
              </select>
              <input className={girdiSinifi} value={h.hesap} onChange={(e) => setHesaplar(hesaplar.map((x, j) => (j === i ? { ...x, hesap: e.target.value } : x)))} placeholder="@kullanici ya da adres" />
              <Dugme ikincil onClick={() => setHesaplar(hesaplar.filter((_, j) => j !== i))}>Sil</Dugme>
            </div>
          ))}
          <Dugme ikincil onClick={() => setHesaplar([...hesaplar, { platform: "x", hesap: "" }])}>Hesap ekle</Dugme>
        </div>
      </Kart>
      <Kart baslik="Kriz geçmişi ve itibar" aciklama="Daha önce yaşadığınız kriz türleri, olası bir krizde sorumluluk yüklemesinin şiddetini etkiler (SCCT; Coombs 2007).">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 mb-4">
          {p.kriz_tipleri.map((t) => (
            <label key={t.anahtar} className="flex gap-2 items-start text-sm">
              <input type="checkbox" className="mt-1" checked={f.krizler.includes(t.anahtar)}
                onChange={(e) => setF((x) => ({ ...x, krizler: e.target.checked ? [...x.krizler, t.anahtar] : x.krizler.filter((k) => k !== t.anahtar) }))} />
              <span>{t.ad} <span className="text-muted-foreground text-xs">({KUME_ADI[t.kume]})</span></span>
            </label>
          ))}
        </div>
        <Alan etiket="Önceki itibar" yardim="Otomatik: itibar ölçümü varsa o, yoksa dönem içi haber tonu kullanılır.">
          <select className={`${girdiSinifi} max-w-xs`} value={f.itibar} onChange={ac("itibar")}>
            <option value="otomatik">Otomatik</option><option value="olumlu">Olumlu</option><option value="notr">Nötr</option><option value="olumsuz">Olumsuz</option>
          </select>
        </Alan>
      </Kart>
      <Dugme disabled={kaydet.isPending} onClick={() => kaydet.mutate({ kurum: f.kurum, sektor: f.sektor, web_sitesi: f.web, izleme_terimleri: satirlar(f.terimler),
        haric_terimler: satirlar(f.haric), ek_rss: satirlar(f.rss), resmi_hesaplar: hesaplar.filter((h) => h.hesap.trim()), kriz_gecmisi: f.krizler, onceki_itibar: f.itibar })}>
        Marka profilini kaydet
      </Dugme>
    </div>
  );
}

function Tarama({ p }: { p: Profil }) {
  const kaydet = useKaydet();
  const [f, setF] = useState({ acik: p.acik_kaynak, aralik: p.aralik_turu, bas: p.ozel_baslangic ?? "", bit: p.ozel_bitis ?? "", plan: p.tekrar_plani, min: p.tarama_min_dk, max: p.tarama_max_dk });
  const bugun = new Date().toISOString().slice(0, 10);
  const en_erken = new Date(Date.now() - p.en_fazla_analiz_gun * 86400000).toISOString().slice(0, 10);
  return (
    <div className="space-y-4">
      <Kart baslik="Veri kaynakları">
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" className="mt-1" checked={f.acik} onChange={(e) => setF({ ...f, acik: e.target.checked })} />
          <span><b>Açık kaynaklar</b> (anahtar gerektirmez): Google Haber, Bing Haber, Reddit genel arama, Google Trends ve ek RSS adresleri.
            <span className="block text-muted-foreground text-xs mt-1">Kapatırsanız yalnızca Kaynaklar sayfasında bağladığınız kurum hesapları (YouTube, X, Instagram) kullanılır.</span></span>
        </label>
      </Kart>
      <Kart baslik="Analiz aralığı" aciklama={`Veri toplama ve analiz bu aralığı kapsar. En fazla ${p.en_fazla_analiz_gun} gün (6 ay). Aralığı genişlettiğinizde eksik geçmiş otomatik taranır.`}>
        <div className="flex flex-wrap gap-2 mb-4">
          {(["7", "30", "90", "180", "ozel"] as const).map((a) => (
            <button key={a} type="button" onClick={() => setF({ ...f, aralik: a })}
              className={`px-4 py-2 rounded-lg border text-sm ${f.aralik === a ? "bg-primary text-primary-foreground border-primary" : "bg-card hover:bg-muted"}`}>
              {a === "ozel" ? "Özel aralık" : a === "7" ? "Son 7 gün" : a === "30" ? "Son 30 gün" : a === "90" ? "Son 3 ay" : "Son 6 ay"}
            </button>
          ))}
        </div>
        {f.aralik === "ozel" && (
          <div className="grid gap-4 sm:grid-cols-2 max-w-lg">
            <Alan etiket="Başlangıç"><input type="date" className={girdiSinifi} min={en_erken} max={bugun} value={f.bas} onChange={(e) => setF({ ...f, bas: e.target.value })} /></Alan>
            <Alan etiket="Bitiş" yardim="Bugünden önce biterse geriye dönük inceleme yapılır: alarm ve e-posta üretilmez.">
              <input type="date" className={girdiSinifi} min={f.bas || en_erken} max={bugun} value={f.bit} onChange={(e) => setF({ ...f, bit: e.target.value })} />
            </Alan>
          </div>
        )}
        <p className="text-xs text-muted-foreground mt-4 leading-relaxed">
          Her kaynak yalnızca erişebildiği kadar geriye gider (örneğin Bing Haber yalnız güncel öğeleri, X yetkiye göre son 7 günü ya da arşivi, Google Trends saatlik veriyi yalnız son 7 gün için verir).
          Ulaşılan aralık Kaynaklar sayfasında gösterilir; eksik dönemler doldurulmaz.
        </p>
      </Kart>
      <Kart baslik="Tekrarlama planı" aciklama="Sistem veriyi sürekli toplar; ancak her artışta e-posta göndermez. Tarama sıklığını risk düzeyine göre kendisi seçer.">
        <div className="grid gap-3 sm:grid-cols-2 mb-4">
          {([["periyodik", "Periyodik tarama", "Sistem aralığı risk düzeyine göre seçer: düşük riskte uzun, yüksek riskte kısa aralık. Kriz tespit edilince sıklık artar, geçince azalır."],
            ["tek_seferlik", "Tek seferlik", "Seçilen aralık bir kez taranır ve analiz edilir. Sonrasında otomatik tarama yapılmaz."]] as const).map(([k, ad, a]) => (
            <label key={k} className={`rounded-lg border p-4 cursor-pointer text-sm ${f.plan === k ? "border-signal bg-accent/50" : "bg-card"}`}>
              <input type="radio" className="mr-2" checked={f.plan === k} onChange={() => setF({ ...f, plan: k })} /><b>{ad}</b>
              <span className="block text-xs text-muted-foreground mt-1 ml-5">{a}</span>
            </label>
          ))}
        </div>
        {f.plan === "periyodik" && (
          <div className="grid gap-4 sm:grid-cols-2 max-w-lg">
            <Alan etiket="En sık tarama (dakika)" yardim="Kriz sırasında sistemin inebileceği en kısa aralık (en az 15)."><input type="number" min={15} max={360} className={girdiSinifi} value={f.min} onChange={(e) => setF({ ...f, min: +e.target.value })} /></Alan>
            <Alan etiket="En seyrek tarama (dakika)" yardim="Risk düşükken kullanılabilecek en uzun aralık (en fazla 360)."><input type="number" min={15} max={360} className={girdiSinifi} value={f.max} onChange={(e) => setF({ ...f, max: +e.target.value })} /></Alan>
          </div>
        )}
        {p.tarama_aralik_dk && f.plan === "periyodik" && <p className="text-xs text-muted-foreground mt-3">Sistemin şu an seçtiği aralık: {p.tarama_aralik_dk} dakika{p.sonraki_tarama ? ` · sonraki tarama ${tarihSaat(p.sonraki_tarama)}` : ""}.</p>}
      </Kart>
      <Dugme disabled={kaydet.isPending || (f.aralik === "ozel" && (!f.bas || !f.bit))} onClick={() => kaydet.mutate({
        acik_kaynak: f.acik, aralik_turu: f.aralik, tekrar_plani: f.plan, tarama_min_dk: f.min, tarama_max_dk: f.max,
        ...(f.aralik === "ozel" ? { ozel_baslangic: f.bas, ozel_bitis: f.bit } : {}) })}>
        Kaydet
      </Dugme>
    </div>
  );
}

function Bildirim({ p }: { p: Profil }) {
  const kaydet = useKaydet();
  const qc = useQueryClient();
  const k = useQuery({ queryKey: ["bildirimler"], queryFn: bildirimlerApi, refetchInterval: 30_000 });
  const [f, setF] = useState({ email: p.bildirim_email, slack: p.bildirim_slack, ek: p.bildirim_ek_epostalar.join("\n"), min: p.bildirim_min_seviye,
    bekleme: p.bildirim_bekleme_saat, haftalik: p.bildirim_haftalik, gun: p.rapor_gunu, saat: p.rapor_saati });
  const test = useMutation({
    mutationFn: testEpostaApi,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["bildirimler"] }); r.gonderilen ? toast.success(`SMTP ${r.gonderilen} e-postayı kabul etti.`) : toast.error("E-posta gönderilemedi; kuyruk kaydındaki hataya bakın."); },
    onError: (e) => toast.error(apiHataMesaji(e)),
  });
  return (
    <div className="space-y-4">
      <Kart baslik="Kriz uyarıları" aciklama="Eşik aşıldığında kurumunuzun kayıtlı adreslerine ‘KRİZ UYARISI’ e-postası gider. Her adrese ayrı e-posta gönderilir; adresler birbirine görünmez.">
        <div className="space-y-4 max-w-xl">
          <label className="flex gap-2 text-sm"><input type="checkbox" checked={f.email} onChange={(e) => setF({ ...f, email: e.target.checked })} />Kriz uyarılarını e-postayla gönder</label>
          <Alan etiket={`Kayıtlı adres: ${p.email}`} yardim="Ek alıcılar (her satıra bir adres, en fazla 5)."><textarea rows={3} className={girdiSinifi} value={f.ek} onChange={(e) => setF({ ...f, ek: e.target.value })} /></Alan>
          <Alan etiket="En düşük bildirim seviyesi">
            <select className={girdiSinifi} value={f.min} onChange={(e) => setF({ ...f, min: +e.target.value })}>
              <option value={1}>Orta risk ve üzeri</option><option value={2}>Yüksek risk ve üzeri</option><option value={3}>Yalnız kritik risk</option>
            </select>
          </Alan>
          <Alan etiket="Bekleme süresi (saat)" yardim="Aynı alarm için seviye yükselme e-postaları arasındaki en kısa süre. Kritik seviyeye çıkış bu süreyi beklemez. Tarama sıklığı bundan bağımsızdır.">
            <input type="number" min={0} max={72} className={girdiSinifi} value={f.bekleme} onChange={(e) => setF({ ...f, bekleme: +e.target.value })} />
          </Alan>
        </div>
      </Kart>
      <Kart baslik="Haftalık PR raporu">
        <div className="grid gap-4 sm:grid-cols-3 max-w-xl">
          <label className="flex gap-2 text-sm sm:col-span-3"><input type="checkbox" checked={f.haftalik} onChange={(e) => setF({ ...f, haftalik: e.target.checked })} />Haftalık raporu e-postayla gönder</label>
          <Alan etiket="Gün"><select className={girdiSinifi} value={f.gun} onChange={(e) => setF({ ...f, gun: +e.target.value })}>{GUNLER.map((g, i) => <option key={g} value={i}>{g}</option>)}</select></Alan>
          <Alan etiket="Saat (Türkiye)"><select className={girdiSinifi} value={f.saat} onChange={(e) => setF({ ...f, saat: +e.target.value })}>{Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{String(i).padStart(2, "0")}:00</option>)}</select></Alan>
        </div>
      </Kart>
      <div className="flex gap-2 flex-wrap">
        <Dugme disabled={kaydet.isPending} onClick={() => kaydet.mutate({ bildirim_email: f.email, bildirim_ek_epostalar: satirlar(f.ek), bildirim_min_seviye: f.min,
          bildirim_bekleme_saat: f.bekleme, bildirim_haftalik: f.haftalik, rapor_gunu: f.gun, rapor_saati: f.saat })}>Kaydet</Dugme>
        <Dugme ikincil disabled={test.isPending || !k.data?.smtp_hazir} onClick={() => test.mutate()}>Deneme e-postası gönder</Dugme>
      </div>
      {!k.data?.smtp_hazir && <Uyari renk="kirmizi">Sunucuda SMTP yapılandırılmamış; e-postalar kuyrukta bekler.</Uyari>}
      <Kart baslik="Gönderim durumu" aciklama="“SMTP kabul etti”, sunucunun mesajı kabul ettiği anlamına gelir; gelen kutusuna kesin teslim edildiğini göstermez.">
        {!k.data?.kayitlar.length ? <Bos>Henüz bildirim yok.</Bos> : (
          <div className="overflow-x-auto"><table className="tablo">
            <thead><tr><th>Zaman</th><th>Tür</th><th>Alıcı</th><th>Konu</th><th>Durum</th></tr></thead>
            <tbody>{k.data.kayitlar.slice(0, 15).map((b) => (
              <tr key={b.id}><td>{tarihSaat(b.olusturma)}</td><td>{b.tur}</td><td>{b.alici}</td><td className="max-w-xs truncate">{b.konu}</td>
                <td><Rozet renk={KUYRUK_ADI[b.durum]?.[1] ?? "gri"}>{KUYRUK_ADI[b.durum]?.[0] ?? b.durum}</Rozet>
                  {b.deneme > 0 && b.durum !== "smtp_kabul" && <span className="text-[11px] text-muted-foreground ml-1">{b.deneme}. deneme</span>}
                  {b.sonraki_deneme && <div className="text-[11px] text-muted-foreground">Sonraki: {tarihSaat(b.sonraki_deneme)}</div>}
                  {b.son_hata && b.durum !== "smtp_kabul" && <div className="text-[11px] text-destructive max-w-xs">{b.son_hata}</div>}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </Kart>
    </div>
  );
}

function Hesap({ p }: { p: Profil }) {
  const { emailDegistir } = useApp();
  const [s, setS] = useState({ mevcut: "", yeni: "", email: "", sifre: "" });
  const sif = useMutation({ mutationFn: () => sifreDegistirApi(s.mevcut, s.yeni), onSuccess: () => { toast.success("Şifre güncellendi."); setS({ ...s, mevcut: "", yeni: "" }); }, onError: (e) => toast.error(apiHataMesaji(e)) });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Kart baslik="Şifre değiştir">
        <div className="space-y-3 max-w-sm">
          <Alan etiket="Mevcut şifre"><input type="password" className={girdiSinifi} value={s.mevcut} onChange={(e) => setS({ ...s, mevcut: e.target.value })} /></Alan>
          <Alan etiket="Yeni şifre" yardim="En az 8 karakter."><input type="password" className={girdiSinifi} value={s.yeni} onChange={(e) => setS({ ...s, yeni: e.target.value })} /></Alan>
          <Dugme disabled={sif.isPending || !s.mevcut || s.yeni.length < 8} onClick={() => sif.mutate()}>Şifreyi güncelle</Dugme>
        </div>
      </Kart>
      <Kart baslik="E-posta adresi" aciklama={`Mevcut: ${p.email} (${p.eposta_dogrulandi ? "doğrulandı" : "doğrulanmadı"}). Değişince yeni adrese doğrulama e-postası gider.`}>
        <div className="space-y-3 max-w-sm">
          <Alan etiket="Yeni e-posta"><input type="email" className={girdiSinifi} value={s.email} onChange={(e) => setS({ ...s, email: e.target.value })} /></Alan>
          <Alan etiket="Şifre"><input type="password" className={girdiSinifi} value={s.sifre} onChange={(e) => setS({ ...s, sifre: e.target.value })} /></Alan>
          <Dugme disabled={!s.email || !s.sifre} onClick={async () => { const r = await emailDegistir(s.email, s.sifre); r.basarili ? toast.success("E-posta güncellendi.") : toast.error(r.hata); }}>Adresi değiştir</Dugme>
        </div>
      </Kart>
    </div>
  );
}
