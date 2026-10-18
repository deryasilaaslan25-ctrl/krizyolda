import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { prBrifApi, prHaftalikGonderApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import type { KrizStratejisi, PRBrif, Yapilacak } from "@/lib/domain";
import { sayi, yuzde } from "@/lib/format";
import { Atif, Bos, Dugme, Kart } from "@/components/ortak";

const EVRE_RENK: Record<string, string> = {
  sinyal_tespiti: "bg-sky-50 border-sky-200 text-sky-900", yoklama_onleme: "bg-sky-50 border-sky-200 text-sky-900",
  hasar_sinirlama: "bg-red-50 border-red-200 text-red-900", toparlanma: "bg-amber-50 border-amber-200 text-amber-900",
  ogrenme: "bg-violet-50 border-violet-200 text-violet-900",
};

export default function PRDanisman() {
  const brif = useQuery({ queryKey: ["pr-brif"], queryFn: prBrifApi, refetchInterval: 120_000 });
  const gonder = useMutation({
    mutationFn: prHaftalikGonderApi,
    onSuccess: (r) => toast.success(`Haftalık brif kuyruğa alındı: ${r.alicilar.join(", ")}`),
    onError: (e) => toast.error(apiHataMesaji(e)),
  });

  if (brif.isLoading) return <Bos>Yükleniyor...</Bos>;
  const b = brif.data;
  if (!b) return <Bos>Brif alınamadı.</Bos>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <p className="text-sm text-muted-foreground max-w-3xl">
          Her gün verinin kendisinden üretilen danışmanlık: sinyal radarı, itibar kırılganlığı ve geri bildirimle öğrenme. Çerçeve Pearson &amp; Mitroff (1993) beş evre,
          kriz anı stratejileri Coombs (2007) SCCT kılavuzu. Öneriler otomatik yayımlanmaz; yetkili iletişim ve hukuk ekibinin onayına sunulur.
        </p>
        <div className="flex items-center gap-2">
          <Atif kimlikler={["PEARSON_MITROFF1993", "COOMBS2007"]} />
          <Dugme ikincil disabled={gonder.isPending} onClick={() => gonder.mutate()}>Haftalık brifi şimdi gönder</Dugme>
        </div>
      </div>

      <Kart className={`border ${EVRE_RENK[b.evre.kod] ?? ""}`}
        baslik={`Evre ${b.evre.no}/5: ${b.evre.ad}`} aciklama={b.evre.neden}>
        <div className="flex flex-wrap gap-2">
          {b.evre.tum_evreler.map((e) => (
            <span key={e.kod} className={`text-xs px-2.5 py-1 rounded-full border ${e.kod === b.evre.kod ? "bg-foreground text-background border-foreground font-semibold" : "bg-card"}`}>
              {e.no}. {e.ad}</span>))}
        </div>
        {b.mesaj && <p className="text-sm mt-3">{b.mesaj}</p>}
      </Kart>

      {b.kriz_stratejisi && <StratejiKarti baslik="Açık kriz — önerilen yanıt stratejisi" v={b.kriz_stratejisi} vurgu />}

      {b.yapilacaklar.length > 0 && (
        <Kart baslik="Bu hafta yapılacaklar" aciklama="Önceliğe göre sıralı; gerekçe ve dayandığı kaynak her maddede verilir.">
          <ol className="space-y-2">{b.yapilacaklar.map((y: Yapilacak, i: number) => (
            <li key={i} className="rounded-lg border border-border p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium">{i + 1}. {y.baslik}</p>
                <Atif kimlikler={y.kaynaklar} />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{y.gerekce}</p>
            </li>))}</ol>
        </Kart>
      )}

      {b.sinyal_radari && <SinyalRadari sa={b.sinyal_radari} />}
      {b.kirilganlik && <Kirilganlik k={b.kirilganlik} />}
      {b.itibar && <ItibarOzet it={b.itibar} />}
      {b.ogrenme && <Ogrenme o={b.ogrenme} />}
    </div>
  );
}

function SinyalRadari({ sa }: { sa: NonNullable<PRBrif["sinyal_radari"]> }) {
  return (
    <Kart baslik="Sinyal radarı" aciklama="Kriz olsun olmasın her taramada güncellenir: kuruma özgü risk puanının eşiğe uzaklığı, zayıf sinyaller ve WECO işaretleri.">
      {sa.risk && (
        <div className="grid sm:grid-cols-3 gap-4 mb-4">
          <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Risk puanı / Yüksek eşik</p>
            <p className="text-lg font-bold font-mono">{sayi(sa.risk.puan, 1)} / {sayi(sa.risk.esikler.yuksek, 1)}</p>
            <p className="text-[11px] text-muted-foreground">{sa.risk.etiket}{sa.risk.donus_metni ? ` · ${sa.risk.donus_metni} görülür` : ""}</p></div>
          <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Son 7 gün Orta+ / Yüksek</p>
            <p className="text-lg font-bold font-mono">{sa.risk.son7_orta_ve_uzeri_saat} / {sa.risk.son7_yuksek_saat} saat</p>
            <p className="text-[11px] text-muted-foreground">{sa.risk.olculen_saat_son7} saat ölçüldü</p></div>
          <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Eşik kaynağı</p>
            <p className="text-sm font-medium">{sa.risk.kaynak}</p>
            <p className="text-[11px] text-muted-foreground">güvenilirlik Z = {sayi(sa.risk.guvenilirlik_z, 2)}, n = {sa.risk.n_blok}</p></div>
        </div>
      )}
      {sa.zayif_sinyaller.length > 0 ? (
        <div className="mb-4">
          <p className="text-sm font-medium mb-2">İzlenecek zayıf sinyaller <span className="text-xs text-muted-foreground">(son 24 pencerenin en az 3'ünde +1σ üstü)</span></p>
          <div className="flex flex-wrap gap-2">{sa.zayif_sinyaller.map((z) => (
            <span key={z.kod} className="text-xs rounded-full border border-amber-300 bg-amber-50 text-amber-900 px-3 py-1">
              {z.kod} {z.ad} · {z.pencere_sayisi}/24 pencere</span>))}</div>
        </div>
      ) : <p className="text-sm text-muted-foreground mb-4">İzlenecek zayıf sinyal yok.</p>}
      {sa.weco.sessiz_birikim && (
        <div className="rounded-lg border border-violet-300 bg-violet-50 text-violet-900 p-3 text-sm mb-4">
          WECO Kural 4 (sessiz birikim): 8 ardışık ölçüm +0σ üstünde — Fink'in prodromal evresiyle uyumlu bir erken sinyal. <Atif kimlikler={["WECO1956", "FINK1986"]} />
        </div>
      )}
      {sa.hafta && (
        <div className="text-sm">
          <p className="font-medium mb-1">Bu hafta vs. önceki hafta</p>
          <p className="text-muted-foreground text-xs">{sa.hafta.kanit}</p>
          <div className="grid sm:grid-cols-3 gap-3 mt-2">
            <MiniKarsilastirma ad="İçerik hacmi" simdi={sa.hafta.icerik.bu_hafta} onceki={sa.hafta.icerik.onceki_hafta} />
            <MiniKarsilastirma ad="Olumsuzluk (G6)" simdi={sa.hafta.olumsuzluk_G6.bu_hafta} onceki={sa.hafta.olumsuzluk_G6.onceki_hafta} yuzdelik />
            <MiniKarsilastirma ad="Haber olumsuzluğu (G7)" simdi={sa.hafta.haber_olumsuzlugu_G7.bu_hafta} onceki={sa.hafta.haber_olumsuzlugu_G7.onceki_hafta} />
          </div>
        </div>
      )}
      <div className="mt-3"><Atif kimlikler={sa.risk?.kaynaklar ?? []} /></div>
    </Kart>
  );
}

function MiniKarsilastirma({ ad, simdi, onceki, yuzdelik }: { ad: string; simdi: number | null; onceki: number | null; yuzdelik?: boolean }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted-foreground">{ad}</p>
      <p className="text-sm font-mono">{simdi === null ? "—" : yuzdelik ? yuzde(simdi) : sayi(simdi, 0)}
        <span className="text-muted-foreground text-xs"> (önceki {onceki === null ? "—" : yuzdelik ? yuzde(onceki) : sayi(onceki, 0)})</span></p>
    </div>
  );
}

function Kirilganlik({ k }: { k: NonNullable<PRBrif["kirilganlik"]> }) {
  return (
    <Kart baslik="İtibar kırılganlığı (SCCT)" aciklama="Son 30 gündeki baskın kriz tipleri ve yoğunlaştırıcılar; alarm olmasa bile hazırlık stratejisi burada."
      sag={<Atif kimlikler={k.kaynaklar} />}>
      <div className="grid sm:grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm font-medium mb-2">Son 30 gün kriz tipleri</p>
          {k.son30_kriz_tipleri.length ? (
            <ul className="text-sm space-y-1">{k.son30_kriz_tipleri.map((t) => (
              <li key={t.tip} className="flex justify-between border-b border-border/60 py-1">
                <span>{t.ad} <span className="text-xs text-muted-foreground">({t.kume_adi})</span></span><span className="font-mono">{t.adet}</span></li>))}</ul>
          ) : <p className="text-sm text-muted-foreground">Belirgin bir kriz tipi tespit edilmedi.</p>}
        </div>
        <div className="text-sm space-y-1">
          <p className="font-medium mb-2">Yoğunlaştırıcılar</p>
          <p>Kriz geçmişi: {k.yogunlastiricilar.kriz_gecmisi.length ? k.yogunlastiricilar.kriz_gecmisi.join(", ") : "girilmemiş"}</p>
          <p>Önceki itibar: {k.yogunlastiricilar.onceki_itibar ?? "bilinmiyor"} {k.yogunlastiricilar.onceki_itibar_kaynak && `(${k.yogunlastiricilar.onceki_itibar_kaynak})`}</p>
          <p className="text-xs text-muted-foreground">{k.yogunlastiricilar.aciklama}</p>
        </div>
      </div>
      <StratejiKarti baslik="Hazırlık stratejisi (henüz kriz yok)" v={k.hazirlik_stratejisi} />
    </Kart>
  );
}

function ItibarOzet({ it }: { it: NonNullable<PRBrif["itibar"]> }) {
  return (
    <Kart baslik="İtibar (L-PTİ)" sag={<Atif kimlikler={it.kaynaklar} />}>
      {it.durum === "yok" ? (
        <p className="text-sm text-muted-foreground">{it.mesaj}</p>
      ) : (
        <div className="text-sm space-y-2">
          <p>Dalga: <b>{it.dalga_adi}</b> {it.genel_skor !== null && it.genel_skor !== undefined && <>· kurum geneli skor <b className="font-mono">{sayi(it.genel_skor, 1)}</b></>}</p>
          {it.en_zayif_surucu && (
            <div className="rounded-lg border border-border p-3">
              <p className="font-medium">Önerilen iletişim odağı: {it.en_zayif_surucu.ad}</p>
              <p className="text-xs text-muted-foreground">Skor {sayi(it.en_zayif_surucu.skor, 1)}, %95 GA [{sayi(it.en_zayif_surucu.ci95[0], 1)}, {sayi(it.en_zayif_surucu.ci95[1], 1)}]. Özellikler: {it.en_zayif_surucu.ozellikler}.</p>
              <p className="text-xs mt-1">{it.en_zayif_surucu.oneri}</p>
            </div>
          )}
          <a href="/itibar" className="text-xs text-chart-3 underline">İtibar skoru sayfasına git →</a>
        </div>
      )}
    </Kart>
  );
}

function Ogrenme({ o }: { o: NonNullable<PRBrif["ogrenme"]> }) {
  return (
    <Kart baslik="Öğrenme" aciklama="Analist etiketleri hem bildirimi hem eşik hesabını bu kuruma göre ayarlar.">
      <div className="grid sm:grid-cols-4 gap-3 text-sm">
        <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Toplam alarm</p><p className="font-mono text-lg">{o.alarm_sayisi}</p></div>
        <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Gerçek / Önemsiz</p><p className="font-mono text-lg">{o.gercek} / {o.onemsiz}</p></div>
        <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Etiketsiz</p><p className="font-mono text-lg">{o.etiketsiz}</p></div>
        <div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Kesinlik</p><p className="font-mono text-lg">{o.kesinlik === null ? "—" : yuzde(o.kesinlik)}</p></div>
      </div>
      <p className="text-xs text-muted-foreground mt-3">{o.mesaj} {o.esik_etiket_duzeltmesi && "Yüksek eşik şu an etiketlerinizle maliyet-duyarlı olarak düzeltilmiş durumda."}</p>
    </Kart>
  );
}

function StratejiKarti({ baslik, v, vurgu }: { baslik: string; v: KrizStratejisi; vurgu?: boolean }) {
  if (v.durum !== "tamam") {
    return (
      <Kart baslik={baslik} className={vurgu ? "border-red-300" : undefined}>
        <p className="text-sm text-muted-foreground">{v.aciklama}</p>
        <div className="mt-2"><Atif kimlikler={v.kaynaklar} /></div>
      </Kart>
    );
  }
  return (
    <Kart baslik={baslik} className={vurgu ? "border-red-300" : undefined}
      aciklama={v.aciklama} sag={<Atif kimlikler={v.kaynaklar} />}>
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <p className="text-sm"><span className="text-muted-foreground">Kriz kümesi:</span> <b>{v.kume_adi}</b> ({v.tehdit} itibar tehdidi)
            {v.tip_adi && <> · tip: {v.tip_adi}</>}{v.yogunlastirici && <span className="text-amber-700"> · yoğunlaştırıcı etkin</span>}</p>
          <p className="text-sm mt-1"><span className="text-muted-foreground">Önerilen duruş:</span> <b>{v.durus}</b></p>
          <ol className="text-sm mt-2 space-y-1 list-decimal list-inside text-muted-foreground">
            {v.adimlar?.map((a, i) => <li key={i}>{a}</li>)}
          </ol>
        </div>
        <div className="text-sm space-y-2">
          {v.birincil.length > 0 && (
            <div><p className="font-medium mb-1">Birincil stratejiler</p>
              <ul className="space-y-1">{v.birincil.map((s) => <StratejiSatir key={s.kod} s={s} />)}</ul></div>
          )}
          {v.kosullu.map((k) => (
            <div key={k.kural} className="rounded-lg border border-amber-300 bg-amber-50 p-2">
              <p className="text-xs font-medium text-amber-900">Koşullu (kural {k.kural})</p>
              <p className="text-xs text-amber-900 mb-1">{k.kosul}</p>
              <ul className="space-y-1">{k.stratejiler.map((s) => <StratejiSatir key={s.kod} s={s} />)}</ul>
            </div>
          ))}
          <div><p className="font-medium mb-1">Destekleyici (tamamlayıcı)</p>
            <ul className="space-y-1">{v.destekleyici.map((s) => <StratejiSatir key={s.kod} s={s} />)}</ul></div>
        </div>
      </div>
      {v.kacinilacaklar && v.kacinilacaklar.length > 0 && (
        <ul className="text-xs text-red-700 mt-3 list-disc list-inside">{v.kacinilacaklar.map((k, i) => <li key={i}>{k}</li>)}</ul>
      )}
      <details className="mt-3"><summary className="text-xs text-muted-foreground cursor-pointer">Uygulanan kurallar (Coombs 2007)</summary>
        <ul className="text-xs text-muted-foreground mt-1 space-y-1">{v.kurallar.map((k) => <li key={k.no}>Kural {k.no}: {k.metin}</li>)}</ul>
      </details>
    </Kart>
  );
}

function StratejiSatir({ s }: { s: { kod: string; ad: string; tanim_tr: string; benoit_karsiligi: string | null } }) {
  return (
    <li className="rounded-md border border-border px-2.5 py-1.5">
      <p className="font-medium">{s.ad}</p>
      <p className="text-xs text-muted-foreground">{s.tanim_tr}</p>
    </li>
  );
}
