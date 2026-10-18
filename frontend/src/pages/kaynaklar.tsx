import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { baglantiKaydetApi, baglantiSilApi, baglantiTestApi, kaynakSaglikApi, kaynaklarApi, taramaListesiApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import type { Baglanti, KaynakDurumKodu } from "@/lib/domain";
import { sayi, tarihSaat, yuzde } from "@/lib/format";
import { Alan, Bos, Dugme, Kart, Rozet, Sayfa, Uyari, girdiSinifi } from "@/components/ortak";

const DURUM: Record<KaynakDurumKodu, [string, "yesil" | "mavi" | "sari" | "kirmizi" | "gri"]> = {
  icerik_var: ["İçerik var", "yesil"], icerik_yok: ["Taranmış, içerik yok", "mavi"], kapsam_yok: ["Bu aralık taranmadı", "sari"],
  taranmadi: ["Henüz taranmadı", "sari"], hata: ["Kaynak hatası", "kirmizi"], baglanti_yok: ["Bağlı değil", "gri"], kapali: ["Kapalı", "gri"],
};
const BAGLANTI_DURUMU: Record<Baglanti["durum"], [string, "yesil" | "sari" | "kirmizi"]> = {
  bagli: ["Bağlı", "yesil"], dogrulanmadi: ["Doğrulanmadı", "sari"], yetki_yok: ["Yetki hatası", "kirmizi"], hata: ["Hata", "kirmizi"],
};
const IS_DURUMU: Record<string, string> = { bekliyor: "Sırada", calisiyor: "Çalışıyor", tamam: "Tamamlandı", kismi: "Kısmen tamamlandı", hata: "Hata", iptal: "İptal" };

export default function Kaynaklar() {
  const q = useQuery({ queryKey: ["kaynaklar"], queryFn: kaynaklarApi, refetchInterval: 30_000 });
  const isler = useQuery({ queryKey: ["tarama"], queryFn: taramaListesiApi, refetchInterval: 15_000 });
  const saglik = useQuery({ queryKey: ["saglik"], queryFn: kaynakSaglikApi });
  if (q.isLoading || !q.data) return <Sayfa baslik="Kaynaklar"><Bos>Yükleniyor…</Bos></Sayfa>;
  const d = q.data;
  return (
    <Sayfa baslik="Kaynaklar"
      aciklama="Veri iki yoldan gelir: herkese açık, anahtar gerektirmeyen kaynaklar ve kurumunuzun kendi hesaplarına bağladığınız API’ler. Sistem tüm interneti taramaz; yalnızca aşağıda listelenen kaynaklardan, her birinin fiilen ulaşabildiği tarih aralığıyla çalışır.">
      <div className="space-y-4">
        <Kart baslik="Kaynak durumu" aciklama={`Analiz aralığı: ${tarihSaat(d.aralik.bas)} – ${tarihSaat(d.aralik.bit)}`}>
          <div className="overflow-x-auto">
            <table className="tablo">
              <thead><tr><th>Kaynak</th><th>Tür</th><th>Durum</th><th className="text-right">İçerik</th><th className="text-right">Kapsanan aralık</th><th>Son tarama</th><th>Not</th></tr></thead>
              <tbody>
                {d.kaynaklar.map((k) => (
                  <tr key={k.kaynak}>
                    <td className="font-medium">{k.ad}</td><td>{k.tur === "haber" ? "Haber" : "Sosyal"}</td>
                    <td><Rozet renk={DURUM[k.durum][1]}>{DURUM[k.durum][0]}</Rozet></td>
                    <td className="text-right sayi">{k.etkin ? sayi(k.icerik, 0) : "—"}</td>
                    <td className="text-right sayi">{k.etkin ? yuzde(k.kapsam_orani, 0) : "—"}</td>
                    <td>{k.son_tarama ? tarihSaat(k.son_tarama) : "—"}</td>
                    <td className="text-xs text-muted-foreground max-w-xs">{k.mesaj || (k.ulasilan_bas && k.kapsam_orani < 1 ? `Ulaşılan başlangıç: ${tarihSaat(k.ulasilan_bas)}` : "")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-3 leading-relaxed">
            “Taranmış, içerik yok” kaynağın o dönemi başarıyla okuduğunu ve içerik bulmadığını gösterir; gerçek sıfırdır. “Bu aralık taranmadı” ve “Kaynak hatası” durumlarında ilgili göstergeler sıfır değil
            “veri yok” sayılır, risk puanı bu eksikle hesaplanır.
          </p>
        </Kart>

        <Kart baslik="Kurum hesabı bağlantıları" aciklama="Kendi YouTube, X ve Instagram hesaplarınızın API bilgilerini bağlayarak hesabınıza gelen yorum ve gönderileri de analize katın.">
          <Uyari renk="mavi">
            Anahtarlar şifrelenerek saklanır, bir daha ekranda gösterilmez ve günlüklere yazılmaz. IP adresi tek başına veri erişim yetkisi sağlamaz; erişim için platformun verdiği anahtar/token ve izinler gerekir.
            Her platformun geçmiş veri sınırı ve kotası farklıdır; bağlantı testi bu bilgileri gösterir.
          </Uyari>
          <div className="grid gap-4 lg:grid-cols-3 mt-4">
            {d.platformlar.map((p) => <BaglantiKarti key={p.platform} p={p} b={d.baglantilar[p.platform]} />)}
          </div>
        </Kart>

        <div className="grid gap-4 xl:grid-cols-2">
          <Kart baslik="Tarama işleri" aciklama="İlk tarama seçilen aralığın tamamını çeker; sonraki taramalar yalnızca eksik kısmı tamamlar.">
            {!isler.data?.isler.length ? <Bos>Henüz tarama işi yok.</Bos> : (
              <table className="tablo">
                <thead><tr><th>Tür</th><th>Durum</th><th>Başlangıç</th><th className="text-right">Yeni içerik</th></tr></thead>
                <tbody>{isler.data.isler.slice(0, 12).map((j) => (
                  <tr key={j.id}><td>{j.tur === "gecmis" ? "Geçmiş" : j.tur === "elle" ? "Elle" : "Rutin"}</td>
                    <td>{IS_DURUMU[j.durum]}{j.mesaj && <div className="text-[11px] text-destructive">{j.mesaj}</div>}</td>
                    <td>{tarihSaat(j.baslama ?? j.olusturma)}</td><td className="text-right sayi">{sayi(j.yeni_icerik, 0)}</td></tr>
                ))}</tbody>
              </table>
            )}
          </Kart>
          <Kart baslik="Kaynak sağlık kayıtları" aciklama="Her taramada kaynak başına gerçek sonuç.">
            {!saglik.data?.length ? <Bos>Kayıt yok.</Bos> : (
              <div className="max-h-80 overflow-y-auto">
                <table className="tablo">
                  <thead><tr><th>Zaman</th><th>Kaynak</th><th>Sonuç</th><th className="text-right">Adet</th></tr></thead>
                  <tbody>{saglik.data.slice(0, 40).map((s, i) => (
                    <tr key={i}><td>{tarihSaat(s.zaman)}</td><td>{s.kaynak}</td>
                      <td><Rozet renk={s.durum === "tamam" ? "yesil" : s.durum === "hata" ? "kirmizi" : "sari"}>{s.durum}</Rozet>{s.mesaj && <div className="text-[11px] text-muted-foreground max-w-xs">{s.mesaj}</div>}</td>
                      <td className="text-right sayi">{s.adet}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </Kart>
        </div>
      </div>
    </Sayfa>
  );
}

function BaglantiKarti({ p, b }: { p: { platform: string; gizli_alan: string; hesap_alan: string }; b?: Baglanti }) {
  const qc = useQueryClient();
  const [hesap, setHesap] = useState(b?.hesap_ref ?? "");
  const [gizli, setGizli] = useState("");
  const [test, setTest] = useState<{ basarili: boolean; mesaj?: string; tarih_siniri?: string; veri_turleri?: string[]; kota?: string } | null>(null);
  const yenile = () => { qc.invalidateQueries({ queryKey: ["kaynaklar"] }); qc.invalidateQueries({ queryKey: ["tarama"] }); };
  const kaydet = useMutation({
    mutationFn: () => baglantiKaydetApi(p.platform, hesap, gizli),
    onSuccess: (r) => { setGizli(""); setTest(r.test); yenile(); r.test.basarili ? toast.success("Bağlantı doğrulandı; eksik aralık taranacak.") : toast.error("Bağlantı kaydedildi ama doğrulanamadı."); },
    onError: (e) => toast.error(apiHataMesaji(e)),
  });
  const dene = useMutation({ mutationFn: () => baglantiTestApi(p.platform), onSuccess: (r) => { setTest(r.test); yenile(); }, onError: (e) => toast.error(apiHataMesaji(e)) });
  const sil = useMutation({ mutationFn: () => baglantiSilApi(p.platform), onSuccess: () => { setHesap(""); setTest(null); yenile(); toast.success("Bağlantı kaldırıldı."); }, onError: (e) => toast.error(apiHataMesaji(e)) });
  const ad = { youtube: "YouTube", x: "X", instagram: "Instagram" }[p.platform] ?? p.platform;
  const bilgi = test ?? (b ? { basarili: b.durum === "bagli", mesaj: b.son_hata, ...(b.kapsam as object) } : null);

  return (
    <div className="surface-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{ad}</h3>
        {b ? <Rozet renk={BAGLANTI_DURUMU[b.durum][1]}>{BAGLANTI_DURUMU[b.durum][0]}</Rozet> : <Rozet>Bağlı değil</Rozet>}
      </div>
      <Alan etiket={p.hesap_alan}><input className={girdiSinifi} value={hesap} onChange={(e) => setHesap(e.target.value)} /></Alan>
      <Alan etiket={p.gizli_alan} yardim={b ? `Kayıtlı: ${b.maske}. Değiştirmek için yeni değer girin, boş bırakırsanız mevcut anahtar korunur.` : undefined}>
        <input type="password" autoComplete="off" className={girdiSinifi} value={gizli} onChange={(e) => setGizli(e.target.value)} />
      </Alan>
      <div className="flex gap-2 flex-wrap">
        <Dugme onClick={() => kaydet.mutate()} disabled={kaydet.isPending || !hesap || (!b && !gizli)}>{b ? "Güncelle ve test et" : "Bağla"}</Dugme>
        {b && <Dugme ikincil onClick={() => dene.mutate()} disabled={dene.isPending}>Test et</Dugme>}
        {b && <Dugme ikincil onClick={() => sil.mutate()} disabled={sil.isPending}>Kaldır</Dugme>}
      </div>
      {bilgi && (
        <div className="text-xs space-y-1 text-muted-foreground border-t border-border pt-3">
          {b?.son_test && <div>Son test: {tarihSaat(b.son_test)}</div>}
          {b?.son_basari && <div>Son başarılı erişim: {tarihSaat(b.son_basari)}</div>}
          {"mesaj" in bilgi && bilgi.mesaj && <div className="text-destructive">{String(bilgi.mesaj)}</div>}
          {"veri_turleri" in bilgi && Array.isArray(bilgi.veri_turleri) && <div>Erişilen veri: {bilgi.veri_turleri.join(", ")}</div>}
          {"tarih_siniri" in bilgi && bilgi.tarih_siniri && <div>Geçmiş sınırı: {String(bilgi.tarih_siniri)}</div>}
          {"kota" in bilgi && bilgi.kota && <div>Kota: {String(bilgi.kota)}</div>}
        </div>
      )}
    </div>
  );
}
