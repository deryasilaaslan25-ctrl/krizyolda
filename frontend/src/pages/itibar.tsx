import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { itibarDalgalariApi, itibarKaliteApi, itibarPuanlaApi, itibarSkorApi, itibarSurucuApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { GRUP_ADI, LPTI_DURUM_ADI, SURUCU_ADI, type LptiDurum } from "@/lib/domain";
import { sayi, yuzde } from "@/lib/format";
import { Atif, Bos, Dugme, Kart } from "@/components/ortak";

const DURUM_RENK: Record<LptiDurum, string> = {
  ok: "bg-emerald-50 border-emerald-200 text-emerald-900",
  insufficient_data: "bg-amber-50 border-amber-200 text-amber-900",
  invalid_instrument: "bg-red-50 border-red-200 text-red-900",
  invariance_not_established: "bg-amber-50 border-amber-200 text-amber-900",
};

export default function Itibar() {
  const qc = useQueryClient();
  const dalgalar = useQuery({ queryKey: ["lpti-dalgalar"], queryFn: itibarDalgalariApi });
  const [secili, setSecili] = useState<number | null>(null);
  const wid = secili ?? dalgalar.data?.[0]?.id ?? null;

  const skor = useQuery({ queryKey: ["lpti-skor", wid], queryFn: () => itibarSkorApi(wid!), enabled: !!wid });
  const surucu = useQuery({ queryKey: ["lpti-surucu", wid], queryFn: () => itibarSurucuApi(wid!), enabled: !!wid });
  const kalite = useQuery({ queryKey: ["lpti-kalite", wid], queryFn: () => itibarKaliteApi(wid!), enabled: !!wid });


  const puanla = useMutation({
    mutationFn: () => itibarPuanlaApi(wid!, { precision_target: 20, dogrulama_zorunlu: false, min_items: 3 }),
    onSuccess: async () => { await Promise.all([qc.invalidateQueries({ queryKey: ["lpti-skor", wid] }), qc.invalidateQueries({ queryKey: ["lpti-surucu", wid] })]); toast.success("Yeniden puanlandı"); },
    onError: (e) => toast.error(apiHataMesaji(e)),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold">İtibar skoru (L-PTİ)</h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            Literatür-Temelli Paydaş İtibar Endeksi: paydaş anketine dayalı, olasılık değil 0–100 algı endeksi. Veri yoksa skor yoktur;
            sistem hiçbir zaman 50 varsayılanı basmaz. Ana skor sürücülerin ortalaması değildir; sürücüler ayrı bir karne olarak raporlanır.
          </p>
        </div>
        <div className="flex items-center gap-2"><Atif kimlikler={["PONZI2011", "FOMBRUN2015"]} /></div>
      </div>

      {!dalgalar.data?.length ? (
        <Kart baslik="Henüz anket dalgası yok">
          <Bos>Paydaş anketi dalgaları API üzerinden (/api/reputation) tanımlanır ve yanıtlar yüklenir. Anket verisi girilmedikçe itibar skoru üretilmez.
            RepTrak maddeleri ticari bir yönteme aittir; sistem lisanslı madde metni içermez.</Bos>
        </Kart>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {dalgalar.data.map((d) => (
              <button key={d.id} onClick={() => setSecili(d.id)}
                className={`text-xs px-3 py-1.5 rounded-lg border ${d.id === wid ? "bg-primary text-primary-foreground" : "bg-card"}`}>
                {d.name || `Dalga ${d.id}`} · {d.yanit_sayisi} yanıt</button>
            ))}
          </div>

          {skor.data && (
            <Kart baslik="Grup skorları" aciklama="Her skorla birlikte ham n, etkin örneklem büyüklüğü (n_eff), standart hata ve %95 güven aralığı zorunludur."
              sag={<Dugme ikincil disabled={puanla.isPending} onClick={() => puanla.mutate()}>Yeniden puanla</Dugme>}>
              {skor.data.overall_score !== null && skor.data.overall_score !== undefined && (
                <div className="rounded-lg border border-border p-3 mb-4 inline-block">
                  <p className="text-xs text-muted-foreground">Kurum geneli skor</p>
                  <p className="text-2xl font-bold font-mono">{sayi(skor.data.overall_score, 1)}</p>
                </div>
              )}
              <div className="grid sm:grid-cols-2 gap-4">
                {skor.data.stakeholder_scores.map((g) => (
                  <div key={g.group} className={`rounded-xl border p-4 ${DURUM_RENK[g.status]}`}>
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{GRUP_ADI[g.group] ?? g.group}</p>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-white/70 border">{LPTI_DURUM_ADI[g.status]}</span>
                    </div>
                    {g.score !== null ? (
                      <>
                        <p className="text-2xl font-bold font-mono mt-1">{sayi(g.score, 1)}</p>
                        <p className="text-xs mt-1">%95 GA [{sayi(g.ci95?.[0], 1)}, {sayi(g.ci95?.[1], 1)}] · SE {sayi(g.se, 1)} · n={g.n}, n_eff={sayi(g.n_eff, 1)}</p>
                      </>
                    ) : (
                      <p className="text-xs mt-1">{g.reason ?? "Skor yayımlanamadı."} {g.estimate !== null && `(nokta tahmini ${sayi(g.estimate, 1)}, henüz güvenilir değil)`}</p>
                    )}
                  </div>
                ))}
              </div>
              {skor.data.comparison?.durum === "ok" && skor.data.comparison.delta.length > 0 && (
                <div className="mt-4 text-sm">
                  <p className="font-medium mb-1">Önceki dalgaya göre değişim (Δ)</p>
                  <ul className="space-y-1">{skor.data.comparison.delta.map((d) => (
                    <li key={d.group}>{GRUP_ADI[d.group] ?? d.group}: {d.delta >= 0 ? "+" : ""}{sayi(d.delta, 1)}
                      {d.anlamli ? <span className="text-emerald-700"> (anlamlı)</span> : <span className="text-muted-foreground"> (GA örtüşüyor, doğrudan bakılmaz)</span>}</li>))}</ul>
                </div>
              )}
              {skor.data.comparison?.durum === "invariance_not_established" && (
                <p className="text-xs text-amber-700 mt-3">Dalgalar arası karşılaştırma yapılmadı: ölçüm değişmezliği (≥ skaler) henüz doğrulanmadı.</p>
              )}
              <div className="mt-3"><Atif kimlikler={["VALLIANT2018", "LUMLEY2004", "MAZZA2015"]} /></div>
            </Kart>
          )}

          {surucu.data && surucu.data.drivers.length > 0 && (
            <Kart baslik="Sürücü karnesi" aciklama="Ayrı bir karnedir; ana skora toplanmaz. Sürücülerin önem ağırlığı paydaşa ve pazara göre değişir."
              sag={<Atif kimlikler={["FOMBRUN2015", "REPTRAK2026"]} />}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                  <thead><tr className="text-xs text-muted-foreground text-left border-b border-border"><th className="py-2">Sürücü</th><th>Grup</th><th className="text-right">Skor</th><th className="text-right">%95 GA</th></tr></thead>
                  <tbody>{surucu.data.drivers.map((d, i) => (
                    <tr key={i} className="border-b border-border/60">
                      <td className="py-2">{SURUCU_ADI[d.driver] ?? d.driver_adi ?? d.driver}</td>
                      <td className="text-xs text-muted-foreground">{GRUP_ADI[d.group] ?? d.group}</td>
                      <td className="text-right font-mono">{sayi(d.score, 1)}</td>
                      <td className="text-right font-mono text-xs">{d.ci95 ? `[${sayi(d.ci95[0], 1)}, ${sayi(d.ci95[1], 1)}]` : "—"}</td>
                    </tr>))}</tbody>
                </table>
              </div>
            </Kart>
          )}

          {kalite.data && (
            <Kart baslik="Ölçüm kalitesi" aciklama="Formül ancak ölçüm aracı doğrulandıktan sonra status=ok üretir; ω (omega) alfa yerine önerilir.">
              <div className="grid sm:grid-cols-2 gap-3 text-sm">
                {kalite.data.quality.gruplar?.map((g) => (
                  <div key={g.group} className="rounded-lg border border-border p-3">
                    <p className="font-medium">{GRUP_ADI[g.group] ?? g.group}</p>
                    <p className="text-xs text-muted-foreground mt-1">ω = {g.omega === null ? "—" : sayi(g.omega, 2)} ({g.estimator || "hesaplanmadı"})</p>
                    <p className="text-xs text-muted-foreground">Doğrulama: {g.dogrulama_durumu} {g.dogrulama_kaynagi && `(${g.dogrulama_kaynagi})`}</p>
                    <p className="text-xs text-muted-foreground">Eksik yanıt oranı: {g.missing_rate === null ? "—" : yuzde(g.missing_rate)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3"><Atif kimlikler={["FLORA2020", "MCNEISH2018", "MCNEISH_WOLF2023", "LEITGOB2023"]} /></div>
            </Kart>
          )}
        </>
      )}
    </div>
  );
}
