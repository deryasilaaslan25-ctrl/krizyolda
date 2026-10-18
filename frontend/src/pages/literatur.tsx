import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { literaturApi } from "@/lib/api";
import type { Gosterge, TasarimKarari } from "@/lib/domain";
import { BOYUT_ADI } from "@/lib/domain";
import { Atif, Bos, Kart, RiskRozeti } from "@/components/ortak";

const GRUPLAR: [string, string, string][] = [
  ["SECILDI", "Seçilen göstergeler (KRE formülüne girer)", "Altı boyut eşit ağırlıklı; boyut içinde göstergeler eşit ağırlıklıdır."],
  ["KALITE", "Veri kalitesi göstergesi (formül dışı)", "Panelde uyarı olarak gösterilir."],
  ["CERCEVE", "Çerçeve değişkenleri (formül dışı)", "Kriz tipi, geçmiş ve önceki itibar gibi yorum bağlamı."],
  ["ELENDI", "Elenen adaylar ve eleme gerekçeleri", "Raporda değerlendirilip sisteme alınmayan göstergeler."],
];

type Kaynak = { kimlik: string; atif: string; url: string; url_notu?: string; ek: boolean; grup: string };
type Sabit = { ad: string; deger: string; kaynaklar: string[] };
type Weco = { kural: number; kosul: string; seviye: number; etiket: string };
type EsikParam = { ad: string; deger: string; tur: string; gerekce: string; plan: string; kaynaklar: string[] };
type LptiKarar = { kod: string; kaynak: string; baslik: string; varsayilan: string; aciklama: string; kaynaklar: string[] };
type Strateji = { ad: string; durus: string; tanim_tr: string; benoit_karsiligi: string | null };
type Kural = { no: number; metin: string };
type Evre = { kod: string; no: number; ad: string; tanim: string; kaynaklar: string[] };

const KAYNAK_GRUP_ADI: Record<string, string> = { v4: "ERKİS göstergeler raporu", v5: "Uygulama kararları", krizyolda: "Krizyolda kararları", esik: "Kriz Eşiği Metodolojisi", lpti: "L-PTİ raporu", pr: "PR danışmanlığı (v5.1)" };

export default function Literatur() {
  const q = useQuery({ queryKey: ["literatur"], queryFn: literaturApi, staleTime: Infinity });
  useEffect(() => {
    if (q.data && window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "center" });
  }, [q.data]);
  if (!q.data) return <Bos>Yükleniyor...</Bos>;
  const d = q.data;
  const gostergeler = d.gostergeler as Gosterge[];
  const kaynaklar = d.kaynaklar as Kaynak[];
  const agirlik = d.agirliklar as Record<string, number>;
  const pr = d.pr as { evreler: Evre[]; temel_yanit: { kod: string; ad: string; tanim: string; uygulama_notu: string }[];
    stratejiler: Record<string, Strateji>; kurallar: Kural[] };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Literatür ve yöntem kataloğu</h1>
        <p className="text-sm text-muted-foreground mt-1">Koddaki her sabit, gösterge ve karar kuralı bu katalogdan okunur. Literatürden
          gelmeyen her seçim "Tasarım kararları" bölümünde açıkça listelenmiştir; bunlara kaynak atfedilmemiştir.</p>
      </div>

      {GRUPLAR.map(([grup, baslik, aciklama]) => (
        <Kart key={grup} baslik={baslik} aciklama={aciklama}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead><tr className="text-xs text-muted-foreground text-left border-b border-border">
                <th className="py-2 pr-3">Kod</th><th className="pr-3">Gösterge</th><th className="pr-3">Boyut</th><th className="pr-3">w</th><th>Ölçüm</th><th>Gerekçe</th><th>Kaynak</th></tr></thead>
              <tbody>{gostergeler.filter((g) => g.grup === grup).map((g) => (
                <tr key={g.kod} className="border-b border-border/60 align-top">
                  <td className="py-2 pr-3 font-mono text-xs">{g.kod}</td>
                  <td className="pr-3 font-medium">{g.ad}</td>
                  <td className="text-xs pr-3">{g.boyut && BOYUT_ADI[g.boyut] ? BOYUT_ADI[g.boyut] : "formül dışı"}</td>
                  <td className="font-mono text-xs pr-3">{agirlik[g.kod] !== undefined ? agirlik[g.kod].toFixed(4) : "—"}</td>
                  <td className="text-xs pr-3 max-w-xs">{g.olcum && g.olcum !== "-" ? g.olcum : "—"}</td>
                  <td className="text-xs pr-3 max-w-sm">{g.gerekce}</td>
                  <td><Atif kimlikler={g.kaynaklar} /></td>
                </tr>))}</tbody>
            </table>
          </div>
        </Kart>
      ))}

      <div className="grid lg:grid-cols-2 gap-6">
        <Kart baslik="Sabitler">
          <ul className="space-y-2 text-sm">{(d.sabitler as Sabit[]).map((s) => (
            <li key={s.ad} className="flex justify-between gap-3"><span>{s.ad} = <span className="font-mono">{s.deger}</span></span><Atif kimlikler={s.kaynaklar} /></li>
          ))}</ul>
        </Kart>
        <Kart baslik="Western Electric kuralları (üst taraf)" sag={<Atif kimlikler={["WECO1956", "NIST_WECO"]} />}>
          <ul className="space-y-2 text-sm">{(d.weco_kurallari as Weco[]).map((w) => (
            <li key={w.kural} className="flex justify-between gap-3"><span>Kural {w.kural}: {w.kosul}</span><span className="font-medium">{w.etiket}</span></li>
          ))}</ul>
          <p className="text-xs text-muted-foreground mt-3">Birden fazla kural ihlal edilirse en yüksek seviye alınır. İlk {String(d.isinma_pencere)} pencere ısınma dönemidir.</p>
        </Kart>
      </div>

      <Kart baslik="Tasarım kararları (literatür dışı, açıkça belirtilmiş)">
        <ol className="space-y-3 text-sm">{(d.tasarim_kararlari as TasarimKarari[]).map((t) => (
          <li key={t.no}><span className="font-semibold">{t.no}. {t.baslik}</span>
            <span className="text-[10px] ml-2 px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{KAYNAK_GRUP_ADI[t.kaynak] ?? t.kaynak}</span>
            <p className="text-muted-foreground mt-0.5">{t.aciklama}</p></li>
        ))}</ol>
      </Kart>

      <Kart baslik="Sınırlılıklar">
        <ul className="list-disc pl-5 space-y-1.5 text-sm">{(d.sinirliliklar as string[]).map((s) => <li key={s}>{s}</li>)}</ul>
      </Kart>

      <Kart baslik={`Kaynakça (${kaynaklar.length})`}>
        <ol className="space-y-2 text-sm">{kaynaklar.map((k) => (
          <li key={k.kimlik} id={k.kimlik} className="scroll-mt-24 target:bg-signal/10 rounded px-1">
            <span className="font-mono text-[11px] text-muted-foreground mr-2">{k.kimlik}</span>{k.atif}{" "}
            {k.url && <a className="text-chart-3 underline break-all" href={k.url} target="_blank" rel="noreferrer">{k.url}</a>}
            {!k.url && k.url_notu && <span className="text-xs text-muted-foreground italic">{k.url_notu}</span>}
            <span className="text-[10px] ml-2 px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{KAYNAK_GRUP_ADI[k.grup] ?? k.grup}</span>
          </li>
        ))}</ol>
      </Kart>

      <Kart baslik="Kuruma özgü kriz eşiği — risk seviyeleri" aciklama="'Yüksek Risk' ve üstü kriz kaydı açar ve kayıt e-postasına uyarı gönderir.">
        <div className="flex flex-wrap gap-3">{(d.risk_seviyeleri as { seviye: number; etiket: string; eylem: string }[]).map((r) => (
          <div key={r.seviye} className="rounded-lg border border-border p-3 text-sm"><RiskRozeti seviye={r.seviye} /><p className="text-xs text-muted-foreground mt-1 max-w-[220px]">{r.eylem}</p></div>
        ))}</div>
      </Kart>

      <Kart baslik="Kuruma özgü kriz eşiği — parametreler (Metodoloji Bölüm 13)"
        aciklama="'Politika' türündeki parametreler veriden türetilemez; bu sürümdeki değerler gerekçeli başlangıç değerleridir.">
        <div className="overflow-x-auto"><table className="w-full text-sm min-w-[900px]">
          <thead><tr className="text-xs text-muted-foreground text-left border-b border-border">
            <th className="py-2 pr-3">Parametre</th><th className="pr-3">Değer</th><th className="pr-3">Tür</th><th className="pr-3">Gerekçe</th><th className="pr-3">Kalibrasyon planı</th><th>Kaynak</th></tr></thead>
          <tbody>{(d.esik_parametreleri as EsikParam[]).map((p) => (
            <tr key={p.ad} className="border-b border-border/60 align-top">
              <td className="py-2 pr-3 font-medium">{p.ad}</td><td className="font-mono text-xs pr-3">{p.deger}</td>
              <td className="pr-3"><span className={`text-[10px] px-1.5 py-0.5 rounded ${p.tur === "Politika" ? "bg-amber-100 text-amber-900" : "bg-muted"}`}>{p.tur}</span></td>
              <td className="text-xs pr-3 max-w-xs">{p.gerekce}</td><td className="text-xs pr-3 max-w-[160px] text-muted-foreground">{p.plan}</td>
              <td><Atif kimlikler={p.kaynaklar} /></td></tr>))}</tbody>
        </table></div>
      </Kart>

      <Kart baslik="Kuruma özgü kriz eşiği — sınırlılıklar">
        <ul className="list-disc pl-5 space-y-1.5 text-sm">{(d.esik_sinirliliklari as string[]).map((s) => <li key={s}>{s}</li>)}</ul>
      </Kart>

      <Kart baslik="L-PTİ — literatüre dayanmayan tasarım kararları (Rapor Bölüm 12 + uygulama)">
        <ol className="space-y-3 text-sm">{(d.lpti_kararlari as LptiKarar[]).map((k) => (
          <li key={k.kod}><span className="font-semibold">{k.kod}. {k.baslik}</span>
            <span className="text-[10px] ml-2 px-1.5 py-0.5 rounded bg-muted text-muted-foreground">varsayılan: {k.varsayilan}</span>
            <span className="text-[10px] ml-2 px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{k.kaynak === "rapor" ? "L-PTİ raporu" : "v5.1 uygulaması"}</span>
            <p className="text-muted-foreground mt-0.5">{k.aciklama}</p>
            {k.kaynaklar.length > 0 && <div className="mt-1"><Atif kimlikler={k.kaynaklar} /></div>}</li>
        ))}</ol>
      </Kart>

      <Kart baslik="L-PTİ — sınırlılıklar">
        <ul className="list-disc pl-5 space-y-1.5 text-sm">{(d.lpti_sinirliliklari as string[]).map((s) => <li key={s}>{s}</li>)}</ul>
      </Kart>

      <Kart baslik="PR danışmanlığı — Coombs (2007) kriz evreleri ve strateji kataloğu" sag={<Atif kimlikler={["COOMBS2007", "PEARSON_MITROFF1993"]} />}>
        <div className="flex flex-wrap gap-2 mb-4">{pr.evreler.map((e) => (
          <span key={e.kod} className="text-xs rounded-full border border-border px-3 py-1">{e.no}. {e.ad}</span>))}</div>
        <div className="overflow-x-auto"><table className="w-full text-sm min-w-[700px] mb-4">
          <thead><tr className="text-xs text-muted-foreground text-left border-b border-border"><th className="py-2 pr-3">Strateji</th><th className="pr-3">Duruş</th><th>Tanım</th></tr></thead>
          <tbody>{Object.entries(pr.stratejiler).map(([kod, s]) => (
            <tr key={kod} className="border-b border-border/60 align-top">
              <td className="py-2 pr-3 font-medium">{s.ad}</td><td className="text-xs pr-3">{s.durus}</td><td className="text-xs">{s.tanim_tr}</td></tr>))}</tbody>
        </table></div>
        <p className="text-sm font-medium mb-1">SCCT strateji kılavuzu (8 kural)</p>
        <ol className="text-sm space-y-1 list-decimal list-inside text-muted-foreground">{pr.kurallar.map((k) => <li key={k.no}>{k.metin}</li>)}</ol>
      </Kart>
    </div>
  );
}
