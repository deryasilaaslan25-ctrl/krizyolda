import { useMemo } from "react";
import { Link } from "wouter";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { useApp } from "@/lib/app-context";
import { literaturApi, sonAnalizApi, taramaBaslatApi, taramaListesiApi, yenidenHesaplaApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import type { AnalizSonucu, Gosterge as GostergeTanimi } from "@/lib/domain";
import { RISK_EYLEMI } from "@/lib/domain";
import { sayi, tarihSaat, yuzde } from "@/lib/format";
import { Bos, Dugme, Gosterge, Kart, RiskRozeti, Rozet, Sayfa, Uyari } from "@/components/ortak";

const AKTIF = ["bekliyor", "calisiyor"];
const gunKisa = (iso: string) => new Date(iso.endsWith("Z") ? iso : iso + "Z").toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });

export default function Panel() {
  const { kullanici } = useApp();
  const qc = useQueryClient();
  const analiz = useQuery({ queryKey: ["analiz"], queryFn: sonAnalizApi, refetchInterval: 60_000 });
  const isler = useQuery({
    queryKey: ["tarama"], queryFn: taramaListesiApi,
    refetchInterval: (q) => (q.state.data?.isler.some((j) => AKTIF.includes(j.durum)) ? 4000 : 30_000),
  });
  const lit = useQuery({ queryKey: ["literatur"], queryFn: literaturApi, staleTime: Infinity });
  const tanimlar = useMemo(() => {
    const m: Record<string, GostergeTanimi> = {};
    ((lit.data?.gostergeler as GostergeTanimi[] | undefined) ?? []).forEach((g) => { m[g.kod] = g; });
    return m;
  }, [lit.data]);

  const aktifIs = isler.data?.isler.find((j) => AKTIF.includes(j.durum));
  const yeniler = () => { qc.invalidateQueries({ queryKey: ["analiz"] }); qc.invalidateQueries({ queryKey: ["tarama"] }); qc.invalidateQueries({ queryKey: ["alarmlar"] }); };
  const baslat = useMutation({ mutationFn: taramaBaslatApi, onSuccess: () => { yeniler(); toast.success("Tarama kuyruğa alındı."); }, onError: (e) => toast.error(apiHataMesaji(e)) });
  const hesapla = useMutation({ mutationFn: yenidenHesaplaApi, onSuccess: () => { yeniler(); toast.success("Analiz yeniden hesaplandı."); }, onError: (e) => toast.error(apiHataMesaji(e)) });

  const a: AnalizSonucu | undefined = analiz.data?.durum === "analiz_yok" ? undefined : analiz.data;
  const seri = useSeri(a);
  const gunluk = useGunluk(a);
  const plan = isler.data?.plan;

  const baslik = (
    <Sayfa baslik="Genel Bakış"
      aciklama={a ? <>Aralık: {tarihSaat(a.aralik.bas)} – {tarihSaat(a.aralik.bit)}{a.aralik.canli ? "" : " (geriye dönük inceleme: alarm ve bildirim üretilmez)"}</> :
        "Kaynaklardan veri toplanıp analiz edildiğinde sonuçlar burada görünür."}
      sag={<>
        <Dugme ikincil onClick={() => hesapla.mutate()} disabled={hesapla.isPending || !a}>Yeniden hesapla</Dugme>
        <Dugme onClick={() => baslat.mutate()} disabled={baslat.isPending || !!aktifIs}>{aktifIs ? "Tarama sürüyor" : "Şimdi tara"}</Dugme>
      </>}>
      <div className="text-xs text-muted-foreground -mt-3 mb-4">
        {aktifIs && <span>Tarama {aktifIs.durum === "bekliyor" ? "sırada" : "çalışıyor"} ({aktifIs.tur === "gecmis" ? "geçmiş tarama" : "rutin tarama"}). </span>}
        {plan && kullanici && (plan.tekrar_plani === "tek_seferlik"
          ? <span>Tekrarlama planı: tek seferlik{plan.tek_seferlik_yapildi ? " (tamamlandı)" : ""}.</span>
          : <span>Sistem taramayı risk düzeyine göre {kullanici.tarama_min_dk}–{kullanici.tarama_max_dk} dk arasında seçer
            {plan.aralik_dk ? <> · şu an her {plan.aralik_dk} dk</> : null}{plan.sonraki ? <> · sonraki: {tarihSaat(plan.sonraki)}</> : null}.</span>)}
      </div>
    </Sayfa>
  );

  if (analiz.isLoading) return <>{baslik}<Bos>Yükleniyor…</Bos></>;
  if (!a) return <>{baslik}<BosDurum aktif={!!aktifIs} /></>;

  const s = a.son;
  const risk = s.risk;
  const kaynakSorun = a.kaynak_ozeti.filter((k) => k.etkin && (k.durum === "hata" || k.durum === "kapsam_yok" || k.durum === "taranmadi"));
  const acikAlarm = a.alarm_donemleri.filter((d) => d.acik);

  return (
    <>
      {baslik}
      <div className="space-y-4">
        {a.isinmada && <Uyari renk="mavi">Normalleştirme ısınma aşamasında ({a.isinma_pencere} pencere); skorlar bu süre boyunca belirsizdir.</Uyari>}
        {kaynakSorun.length > 0 && (
          <Uyari>
            Bazı kaynaklar bu dönemi eksiksiz kapsamıyor: {kaynakSorun.map((k) => `${k.ad} (${k.durum === "hata" ? "hata" : "kapsam yok"})`).join(", ")}.
            Kapsanmayan pencerelerde ilgili göstergeler “veri yok” sayılır, sıfır sayılmaz. <Link href="/kaynaklar" className="underline font-medium">Kaynak durumu</Link>
          </Uyari>
        )}
        {a.eksik_gostergeler.length > 0 && <Uyari renk="mavi">Dönem boyunca ölçülemeyen göstergeler: {a.eksik_gostergeler.join(", ")}. Ağırlıklar ölçülebilen göstergeler üzerinden yeniden dağıtılır.</Uyari>}
        {a.uyarilar.map((u) => <Uyari key={u} renk="mavi">{u}</Uyari>)}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Kart>
            <Gosterge etiket="Risk düzeyi (1. beyin)" deger={risk ? sayi(risk.puan, 1) : "—"}
              alt={risk ? <span className="inline-flex items-center gap-2"><RiskRozeti seviye={risk.nihai_seviye} /> Yüksek eşik {sayi(risk.esikler.yuksek, 1)}</span> : "Karar bu dönemde üretilmez"} />
            {risk && <p className="text-xs text-muted-foreground mt-3 leading-snug">{RISK_EYLEMI[risk.nihai_seviye]}</p>}
          </Kart>
          <Kart>
            <Gosterge etiket="Açık alarm" deger={acikAlarm.length} alt={acikAlarm.length ? `En yüksek: ${acikAlarm[0].max_etiket}` : "Eşik aşımı yok"} />
            <Link href="/krizler" className="text-xs text-accent-foreground underline mt-3 inline-block">Alarm merkezi</Link>
          </Kart>
          <Kart>
            <Gosterge etiket="Kaynak kapsamı" deger={yuzde(kapsamOrtalama(a), 0)} alt={`${a.kaynak_ozeti.filter((k) => k.etkin).length} etkin kaynak`} />
            <Link href="/kaynaklar" className="text-xs text-accent-foreground underline mt-3 inline-block">Kaynaklar</Link>
          </Kart>
          <Kart>
            <Gosterge etiket="2. beyin (uzman)" deger={a.beyin.etkin ? sayi(a.beyin.son?.r2, 1) : "Pasif"}
              alt={a.beyin.etkin ? `1. beyinle fark ${sayi(a.beyin.son?.fark, 1)} puan` : a.beyin.aciklama} />
            <Link href="/beyinler" className="text-xs text-accent-foreground underline mt-3 inline-block">İki beyin karşılaştırması</Link>
          </Kart>
        </div>

        <Kart baslik="Risk puanı" aciklama="1. beyin: 13 gösterge eşit ağırlık. Kesik çizgi bu kuruma özgü Yüksek eşiktir.">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={seri} margin={{ left: -10, right: 8, top: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 24% 89%)" />
                <XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={40} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => sayi(v, 1)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="r1" name="Risk (1. beyin)" stroke="hsl(189 94% 36%)" fill="hsl(189 94% 43% / .12)" strokeWidth={1.5} dot={false} connectNulls={false} />
                {a.beyin.etkin && <Line type="monotone" dataKey="r2" name="Risk (2. beyin)" stroke="hsl(222 47% 24%)" strokeWidth={1.2} dot={false} />}
                <Line type="stepAfter" dataKey="esik" name="Yüksek eşik" stroke="hsl(0 72% 50%)" strokeDasharray="5 4" dot={false} strokeWidth={1.2} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Kart>

        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <Kart baslik="13 gösterge" aciklama="Son pencere. Skor: normalleştirilmiş ve ±3σ'da kırpılmış z-değeri. Ağırlık: ölçülebilen göstergelere eşit pay.">
            <div className="overflow-x-auto">
              <table className="tablo">
                <thead><tr><th>Gösterge</th><th className="text-right">Değer</th><th className="text-right">Skor</th><th className="text-right">Ağırlık</th><th className="text-right">Katkı</th></tr></thead>
                <tbody>
                  {Array.from({ length: 13 }, (_, i) => `G${i + 1}`).map((kod) => {
                    const deger = s.gostergeler[kod];
                    const olculdu = deger !== null && deger !== undefined;
                    return (
                      <tr key={kod}>
                        <td><span className="font-mono text-[11px] text-muted-foreground mr-2">{kod}</span>{tanimlar[kod]?.ad ?? kod}</td>
                        <td className="text-right sayi">{olculdu ? sayi(deger, 3) : <span className="text-muted-foreground">veri yok</span>}</td>
                        <td className="text-right sayi">{s.kirpilmis[kod] !== undefined ? sayi(s.kirpilmis[kod], 2) : "—"}</td>
                        <td className="text-right sayi">{s.agirliklar[kod] !== undefined ? yuzde(s.agirliklar[kod], 2) : "—"}</td>
                        <td className="text-right sayi">{s.katkilar[kod] !== undefined ? sayi(s.katkilar[kod], 3) : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Q1 (kopya/koordinasyon şüphesi, formüle girmez): {yuzde(s.gostergeler.Q1 ?? null)}. Bu oran kanıtlanmış bir manipülasyon değil, benzer içeriklerin oranıdır.
            </p>
          </Kart>

          <Kart baslik="İçerik hacmi" aciklama="Günlük toplam (sosyal + haber). Kapsanmayan günler boş görünür.">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={gunluk} margin={{ left: -15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 24% 89%)" vertical={false} />
                  <XAxis dataKey="x" tick={{ fontSize: 10 }} minTickGap={30} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="sosyal" name="Sosyal" stackId="a" fill="hsl(189 94% 36%)" />
                  <Bar dataKey="haber" name="Haber" stackId="a" fill="hsl(222 47% 24%)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {a.kaynak_ozeti.filter((k) => k.etkin).map((k) => <Rozet key={k.kaynak} renk={k.durum === "icerik_var" ? "yesil" : k.durum === "icerik_yok" ? "mavi" : k.durum === "hata" ? "kirmizi" : "sari"}>{k.ad}: {k.icerik}</Rozet>)}
            </div>
          </Kart>
        </div>
      </div>
    </>
  );
}

function BosDurum({ aktif }: { aktif: boolean }) {
  return (
    <Kart baslik={aktif ? "İlk tarama sürüyor" : "Henüz analiz yok"}>
      <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
        {aktif
          ? "Seçtiğiniz aralık için geçmiş veriler toplanıyor. Uzun aralıklarda bu işlem birkaç dakika sürebilir; sayfa kendiliğinden güncellenir."
          : "Sistem, kurum profilindeki terimler ve seçili kaynaklarla taramaya başlar. Kaynakları ve izleme aralığını Ayarlar ile Kaynaklar sayfalarından düzenleyebilir, “Şimdi tara” ile hemen başlatabilirsiniz."}
      </p>
      <div className="mt-4 flex gap-3 text-sm">
        <Link href="/ayarlar" className="underline text-accent-foreground">Ayarlar</Link>
        <Link href="/kaynaklar" className="underline text-accent-foreground">Kaynaklar</Link>
      </div>
    </Kart>
  );
}

function kapsamOrtalama(a: AnalizSonucu) {
  const e = a.kaynak_ozeti.filter((k) => k.etkin);
  return e.length ? e.reduce((t, k) => t + k.kapsam_orani, 0) / e.length : 0;
}

/** Çizim için en çok ~720 nokta: daha uzun dönemlerde 6 saatlik blokta en yüksek değer. */
function useSeri(a?: AnalizSonucu) {
  return useMemo(() => {
    if (!a) return [];
    const ham = a.pencereler.map((p) => ({ bas: p.bas, r1: p.risk_puani ?? null, r2: p.risk_uzman ?? null, esik: p.risk_esik_yuksek ?? null }));
    const adim = Math.max(1, Math.ceil(ham.length / 720));
    const cikti = [];
    for (let i = 0; i < ham.length; i += adim) {
      const b = ham.slice(i, i + adim);
      const en = (k: "r1" | "r2" | "esik") => { const v = b.map((x) => x[k]).filter((x): x is number => x !== null); return v.length ? Math.max(...v) : null; };
      cikti.push({ x: gunKisa(b[0].bas), r1: en("r1"), r2: en("r2"), esik: en("esik") });
    }
    return cikti;
  }, [a]);
}

function useGunluk(a?: AnalizSonucu) {
  return useMemo(() => {
    if (!a) return [];
    const m = new Map<string, { x: string; sosyal: number; haber: number }>();
    for (const p of a.pencereler) {
      const g = gunKisa(p.bas);
      const o = m.get(g) ?? { x: g, sosyal: 0, haber: 0 };
      o.sosyal += p.sosyal_sayisi; o.haber += p.haber_sayisi;
      m.set(g, o);
    }
    return [...m.values()];
  }, [a]);
}
