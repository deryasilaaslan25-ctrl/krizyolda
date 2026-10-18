import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "wouter";
import { beyinApi } from "@/lib/api";
import { sayi, yuzde } from "@/lib/format";
import { Bos, Gosterge, Kart, RiskRozeti, Sayfa, Uyari } from "@/components/ortak";

const gun = (iso: string) => new Date(iso.endsWith("Z") ? iso : iso + "Z").toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });

export default function Beyinler() {
  const q = useQuery({ queryKey: ["beyin"], queryFn: beyinApi, refetchInterval: 120_000 });
  if (q.isLoading || !q.data) return <Sayfa baslik="İki Beyin"><Bos>Yükleniyor…</Bos></Sayfa>;
  const { beyin2, gostergeler, karsilastirma: k } = q.data;
  const agirlikVeri = gostergeler.map((g) => ({ kod: g.kod, "1. beyin": Number(g.agirlik1.toFixed(2)), "2. beyin": g.agirlik2 !== null ? Number(g.agirlik2.toFixed(2)) : null }));

  return (
    <Sayfa baslik="İki Beyin"
      aciklama="Aynı 13 gösterge, aynı veri, iki farklı ağırlıklandırma. 1. beyin tüm göstergelere eşit ağırlık verir ve alarmları belirler. 2. beyin göstergelerin ağırlığını uzman görüşlerinden alır; sonuçlar yan yana raporlanır, fark gözlenir.">
      <div className="grid gap-4 md:grid-cols-2 mb-4">
        <Kart baslik="1. beyin — eşit ağırlık">
          <p className="text-sm text-muted-foreground leading-relaxed">13 göstergenin her biri 100/13 = {sayi(100 / 13, 4)} puan ağırlık taşır (toplam 100). Bir gösterge ölçülemezse kalan göstergelere eşit pay verilir. Eşit ağırlık bir başlangıç varsayımıdır; en iyi ağırlık olduğu iddia edilmez.</p>
        </Kart>
        <Kart baslik="2. beyin — uzman ağırlıklı" sag={<span className={`text-xs font-medium ${beyin2.etkin ? "text-emerald-700" : "text-muted-foreground"}`}>{beyin2.etkin ? "Etkin" : "Pasif"}</span>}>
          {beyin2.etkin ? (
            <div className="text-sm text-muted-foreground leading-relaxed space-y-1">
              <p>Form {beyin2.form} · {beyin2.uzman_sayisi} uzman · birleştirme: {beyin2.birlestirme} · ölçek {beyin2.olcek?.[0]}–{beyin2.olcek?.[1]}.</p>
              <p>Uzmanlar arası uyum (Kendall W): <b className="text-foreground">{beyin2.kendall_w !== null && beyin2.kendall_w !== undefined ? sayi(beyin2.kendall_w, 2) : "hesaplanamadı"}</b>. Değer 1’e yaklaştıkça uzmanlar göstergeleri benzer sıralamıştır.</p>
              <p className="text-xs">Soru: {beyin2.soru}</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground leading-relaxed">{beyin2.aciklama} Uzman puanı gelene kadar sahte ya da varsayılan puan kullanılmaz ve 2. beyin hiçbir sonucu etkilemez.</p>
          )}
        </Kart>
      </div>

      {!k ? <Uyari renk="mavi">Henüz analiz yok. Karşılaştırma ilk analizden sonra görünür.</Uyari> : !k.etkin ? null : (
        <div className="space-y-4 mb-4">
          <Kart baslik="Son pencere karşılaştırması">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <Gosterge etiket="1. beyin risk" deger={sayi(k.son?.r1, 1)} alt={k.son?.seviye1 !== null && k.son?.seviye1 !== undefined ? <RiskRozeti seviye={k.son.seviye1} /> : "Karar yok (geriye dönük)"} />
              <Gosterge etiket="2. beyin risk" deger={sayi(k.son?.r2, 1)} alt={k.son?.seviye2 !== null && k.son?.seviye2 !== undefined ? <RiskRozeti seviye={k.son.seviye2} /> : undefined} />
              <Gosterge etiket="Fark (2. − 1.)" deger={sayi(k.son?.fark, 1)} alt={`Z farkı ${sayi((k.son?.z2 ?? 0) - (k.son?.z1 ?? 0), 2)}`} />
              <Gosterge etiket="Dönem korelasyonu" deger={sayi(k.donem?.korelasyon, 2)} alt={`${k.donem?.n} pencere · ort. mutlak fark ${sayi(k.donem?.ortalama_mutlak_fark, 1)}`} />
            </div>
            <p className="text-xs text-muted-foreground mt-4 leading-relaxed">
              2. beyin seviyesi, kendi risk geçmişinden aynı eşik yöntemiyle bulunur ve histerezissiz “ham” seviyedir; yalnız karşılaştırma içindir. Kendi geçmişine göre
              aşım yüzdeliği: 1. beyin {yuzde(k.son?.yuzdelik1 ?? null, 1)}, 2. beyin {yuzde(k.son?.yuzdelik2 ?? null, 1)}.
            </p>
          </Kart>
          <Kart baslik="Risk puanı: iki beyin" aciklama="Uzun dönemlerde 6 saatlik blokta en yüksek değer gösterilir.">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={(k.seri ?? []).map((s) => ({ x: gun(s.bas), r1: s.r1, r2: s.r2 }))} margin={{ left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 24% 89%)" />
                  <XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={40} /><YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => sayi(v, 1)} /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line dataKey="r1" name="1. beyin" stroke="hsl(189 94% 36%)" dot={false} strokeWidth={1.5} />
                  <Line dataKey="r2" name="2. beyin" stroke="hsl(222 47% 24%)" dot={false} strokeWidth={1.5} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Kart>
          <Kart baslik="Farkı doğuran göstergeler" aciklama="Son pencerede iki ağırlıklandırmanın KRE’ye katkı farkı; mutlak farka göre sıralı.">
            <div className="overflow-x-auto">
              <table className="tablo">
                <thead><tr><th>Gösterge</th><th className="text-right">Skor</th><th className="text-right">Ağırlık 1</th><th className="text-right">Ağırlık 2</th><th className="text-right">Katkı 1</th><th className="text-right">Katkı 2</th><th className="text-right">Fark</th></tr></thead>
                <tbody>
                  {k.katkilar?.map((g) => (
                    <tr key={g.kod}>
                      <td><span className="font-mono text-[11px] text-muted-foreground mr-2">{g.kod}</span>{g.ad}</td>
                      <td className="text-right sayi">{sayi(g.skor, 2)}</td>
                      <td className="text-right sayi">{yuzde(g.w1, 2)}</td><td className="text-right sayi">{yuzde(g.w2, 2)}</td>
                      <td className="text-right sayi">{sayi(g.katki1, 3)}</td><td className="text-right sayi">{sayi(g.katki2, 3)}</td>
                      <td className="text-right sayi font-medium">{sayi(g.fark, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Kart>
        </div>
      )}

      <Kart baslik="Gösterge ağırlıkları" aciklama="Yüzde puan; her beyinde toplam 100.">
        <div className="h-64 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={agirlikVeri} margin={{ left: -15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 24% 89%)" vertical={false} />
              <XAxis dataKey="kod" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} /><Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="1. beyin" fill="hsl(189 94% 36%)" /><Bar dataKey="2. beyin" fill="hsl(222 47% 24%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="overflow-x-auto">
          <table className="tablo">
            <thead><tr><th>Gösterge</th><th>Boyut</th><th className="text-right">1. beyin</th><th className="text-right">Uzman puanı</th><th className="text-right">2. beyin</th><th className="text-right">Uzman dağılımı</th></tr></thead>
            <tbody>
              {gostergeler.map((g) => (
                <tr key={g.kod}>
                  <td><span className="font-mono text-[11px] text-muted-foreground mr-2">{g.kod}</span>{g.ad}</td><td>{g.boyut}</td>
                  <td className="text-right sayi">{sayi(g.agirlik1, 2)}</td>
                  <td className="text-right sayi">{g.uzman_puani !== null ? sayi(g.uzman_puani, 2) : "—"}</td>
                  <td className="text-right sayi">{g.agirlik2 !== null ? sayi(g.agirlik2, 2) : "—"}</td>
                  <td className="text-right sayi text-xs text-muted-foreground">{g.yayilim ? `${sayi(g.yayilim.min, 1)}–${sayi(g.yayilim.max, 1)} (σ ${sayi(g.yayilim.std, 2)})` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground mt-3">Yöntem kararları ve kaynaklar için <Link href="/literatur" className="underline">Yöntem ve Literatür</Link> sayfasına bakın.</p>
      </Kart>
    </Sayfa>
  );
}
