import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "wouter";
import { bilgiProfiliApi } from "@/lib/api";
import { sayi, yuzde } from "@/lib/format";
import { Bos, Gosterge, Kart, Rozet, Sayfa, Uyari } from "@/components/ortak";

const gun = (d: string) => new Date(d).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
const DURUM: Record<string, [string, "yesil" | "mavi" | "sari" | "kirmizi" | "gri"]> = {
  icerik_var: ["İçerik var", "yesil"], icerik_yok: ["Taranmış, içerik yok", "mavi"], kapsam_yok: ["Bu aralık taranmadı", "sari"],
  taranmadi: ["Henüz taranmadı", "sari"], hata: ["Kaynak hatası", "kirmizi"], baglanti_yok: ["Bağlı değil", "gri"], kapali: ["Kapalı", "gri"],
};

export default function Profil() {
  const q = useQuery({ queryKey: ["bilgi-profili"], queryFn: bilgiProfiliApi });
  if (q.isLoading || !q.data) return <Sayfa baslik="Kurum Profili"><Bos>Yükleniyor…</Bos></Sayfa>;
  const p = q.data;
  const d = p.duygu;
  return (
    <Sayfa baslik="Kurum Profili"
      aciklama={`Seçili aralıkta (${gun(p.aralik.bas)} – ${gun(p.aralik.bit)}, ${p.aralik.gun} gün) erişilebilen kaynaklardan toplanan içeriklerin özeti. Aralığı Ayarlar sayfasından 6 aya kadar genişletebilirsiniz.`}>
      {p.toplam === 0 ? (
        <Uyari renk="mavi">Bu aralıkta kayıtlı içerik yok. Tarama tamamlanmamış, kaynak bağlı değil ya da kapsamda içerik bulunmuyor olabilir; <Link href="/kaynaklar" className="underline">kaynak durumunu</Link> kontrol edin.</Uyari>
      ) : (
        <div className="space-y-4">
          <Kart>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
              <Gosterge etiket="Toplam içerik" deger={sayi(p.toplam, 0)} />
              <Gosterge etiket="Günlük ortalama" deger={sayi(p.gunluk_ortalama, 1)} alt={p.olagan_duzey ? `medyan ${sayi(p.olagan_duzey.medyan, 0)} (${sayi(p.olagan_duzey.q1, 0)}–${sayi(p.olagan_duzey.q3, 0)})` : "medyan için yetersiz gün"} />
              <Gosterge etiket="Haftalık ortalama" deger={sayi(p.haftalik_ortalama, 0)} />
              <Gosterge etiket="Olumsuzluk oranı" deger={yuzde(p.olumsuz_oran)} alt={`${sayi(d.olumsuz, 0)} olumsuz · ${sayi(d.olumlu, 0)} olumlu · ${sayi(d.notr, 0)} nötr`} />
              <Gosterge etiket="Ortalama kaynak kapsamı" deger={yuzde(p.kapsam_orani, 0)} alt="etkin kaynaklar" />
            </div>
          </Kart>
          <Kart baslik="Günlük hacim ve olumsuz içerik">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={p.gunluk.map((g) => ({ ...g, x: gun(g.tarih) }))} margin={{ left: -15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 24% 89%)" vertical={false} />
                  <XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={30} /><YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 12 }} /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="toplam" name="Toplam" fill="hsl(189 94% 36% / .55)" />
                  <Line dataKey="olumsuz" name="Olumsuz" stroke="hsl(0 72% 50%)" dot={false} strokeWidth={1.5} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Kart>
          <div className="grid gap-4 lg:grid-cols-2">
            <Kart baslik="Haftanın günlerine göre ritim" aciklama="Her gün için aralıktaki günlük ortalama içerik sayısı.">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={p.hafta_ritmi.map((h) => ({ gun: h.gun.slice(0, 3), ortalama: h.ortalama }))} margin={{ left: -15 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 24% 89%)" vertical={false} />
                    <XAxis dataKey="gun" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => sayi(v, 1)} />
                    <Bar dataKey="ortalama" name="Ortalama" fill="hsl(222 47% 24%)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Kart>
            <Kart baslik="Haftalık olumsuzluk oranı">
              <table className="tablo">
                <thead><tr><th>Hafta</th><th className="text-right">İçerik</th><th className="text-right">Olumsuz</th><th className="text-right">Oran</th></tr></thead>
                <tbody>{p.haftalik.slice(-10).map((h) => (
                  <tr key={h.hafta}><td>{h.hafta}</td><td className="text-right sayi">{sayi(h.toplam, 0)}</td><td className="text-right sayi">{sayi(h.olumsuz, 0)}</td><td className="text-right sayi">{yuzde(h.olumsuz_oran)}</td></tr>
                ))}</tbody>
              </table>
            </Kart>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Kart baslik="Kaynak dağılımı">
              <table className="tablo"><tbody>{p.kaynak_dagilimi.map((k) => (
                <tr key={k.kaynak}><td>{k.ad}</td><td className="text-right sayi">{sayi(k.adet, 0)}</td><td className="text-right sayi text-muted-foreground">{yuzde(k.adet / p.toplam)}</td></tr>
              ))}</tbody></table>
            </Kart>
            <Kart baslik="Olumsuz içeriklerde öne çıkan konular" aciklama="Otomatik kriz tipi etiketi (SCCT); hatalı olabilir, içeriklerden doğrulayın.">
              {p.konular.length === 0 ? <Bos>Konu etiketi çıkarılamadı.</Bos> : (
                <table className="tablo"><tbody>{p.konular.map((k) => (
                  <tr key={k.konu}><td>{k.konu}</td><td className="text-right sayi">{sayi(k.adet, 0)}</td></tr>
                ))}</tbody></table>
              )}
            </Kart>
          </div>
          <Kart baslik="Kaynak profili">
            <table className="tablo">
              <thead><tr><th>Kaynak</th><th>Durum</th><th className="text-right">İçerik</th><th className="text-right">Kapsam</th><th>Not</th></tr></thead>
              <tbody>{p.kaynak_ozeti.filter((k) => k.etkin).map((k) => (
                <tr key={k.kaynak}><td>{k.ad}</td><td><Rozet renk={DURUM[k.durum][1]}>{DURUM[k.durum][0]}</Rozet></td>
                  <td className="text-right sayi">{sayi(k.icerik, 0)}</td><td className="text-right sayi">{yuzde(k.kapsam_orani, 0)}</td>
                  <td className="text-xs text-muted-foreground">{k.mesaj}</td></tr>
              ))}</tbody>
            </table>
          </Kart>
          <Uyari renk="mavi">{p.sinirlama}</Uyari>
        </div>
      )}
    </Sayfa>
  );
}
