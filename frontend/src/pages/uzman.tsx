import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { uzmanFormDurumApi, uzmanFormOlusturApi, uzmanFormlariApi, uzmanGostergeleriApi, uzmanKaydetApi, uzmanPuanlariApi, uzmanSilApi, beyinApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { sayi } from "@/lib/format";
import { Alan, Bos, Dugme, Kart, Rozet, Sayfa, Uyari, girdiSinifi } from "@/components/ortak";

export default function Uzman() {
  const qc = useQueryClient();
  const formlar = useQuery({ queryKey: ["uzman-formlar"], queryFn: uzmanFormlariApi });
  const beyin = useQuery({ queryKey: ["beyin"], queryFn: beyinApi });
  const [secili, setSecili] = useState<number | null>(null);
  useEffect(() => { if (secili === null && formlar.data?.length) setSecili((formlar.data.find((f) => f.aktif) ?? formlar.data[0]).id); }, [formlar.data, secili]);
  const yenile = () => { qc.invalidateQueries({ queryKey: ["uzman-formlar"] }); qc.invalidateQueries({ queryKey: ["uzman-puan"] }); qc.invalidateQueries({ queryKey: ["beyin"] }); };
  const durum = useMutation({ mutationFn: (v: { id: number; aktif: boolean }) => uzmanFormDurumApi(v.id, v.aktif), onSuccess: () => { yenile(); toast.success("Güncellendi."); }, onError: (e) => toast.error(apiHataMesaji(e)) });
  const form = formlar.data?.find((f) => f.id === secili);

  return (
    <Sayfa baslik="Uzman Paneli"
      aciklama="2. beyin için uzman puanlarının girildiği yönetici ekranı. Form sürümü; uzmana sorulan soruyu, puan ölçeğini ve birleştirme yöntemini sabitler. Uzmanlar kodla (U01…) kaydedilir, ad saklanmaz. Yeterli uzmanın 13 gösterge puanı girilip form etkinleştirilmedikçe 2. beyin hesaplanmaz.">
      <div className="space-y-4">
        {beyin.data && !beyin.data.beyin2.etkin && <Uyari renk="mavi">2. beyin şu an pasif: {beyin.data.beyin2.aciklama}</Uyari>}
        <YeniForm onTamam={(id) => { yenile(); setSecili(id); }} />
        <Kart baslik="Form sürümleri">
          {!formlar.data?.length ? <Bos>Henüz form yok. Yukarıdan ilk sürümü oluşturun.</Bos> : (
            <table className="tablo">
              <thead><tr><th>Sürüm</th><th>Ölçek</th><th>Birleştirme</th><th className="text-right">Uzman (tam/girilen)</th><th>Durum</th><th /></tr></thead>
              <tbody>{formlar.data.map((f) => (
                <tr key={f.id} className={f.id === secili ? "bg-accent/40" : ""}>
                  <td className="font-medium">{f.surum}</td><td>{f.olcek_min}–{f.olcek_max}</td><td>{f.birlestirme}</td>
                  <td className="text-right sayi">{f.tam_uzman}/{f.uzman_sayisi} (gerekli {f.min_uzman})</td>
                  <td>{f.aktif ? <Rozet renk="yesil">Etkin</Rozet> : <Rozet>Pasif</Rozet>}</td>
                  <td className="text-right whitespace-nowrap">
                    <Dugme ikincil onClick={() => setSecili(f.id)}>Aç</Dugme>{" "}
                    <Dugme ikincil onClick={() => durum.mutate({ id: f.id, aktif: !f.aktif })}>{f.aktif ? "Pasifleştir" : "Etkinleştir"}</Dugme>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </Kart>
        {form && <Puanlar key={form.id} id={form.id} onDegisti={yenile} />}
      </div>
    </Sayfa>
  );
}

function YeniForm({ onTamam }: { onTamam: (id: number) => void }) {
  const [f, setF] = useState({ surum: "", soru: "Göstergenin kriz tespitindeki önem derecesini puanlayın.", min: 1, max: 9, birlestirme: "ortalama" as "ortalama" | "medyan", gerekli: 12 });
  const olustur = useMutation({
    mutationFn: () => uzmanFormOlusturApi({ surum: f.surum, soru: f.soru, olcek_min: f.min, olcek_max: f.max, birlestirme: f.birlestirme, min_uzman: f.gerekli }),
    onSuccess: (r) => { toast.success("Form oluşturuldu (pasif)."); setF({ ...f, surum: "" }); onTamam(r.id); }, onError: (e) => toast.error(apiHataMesaji(e)),
  });
  return (
    <Kart baslik="Yeni form sürümü" aciklama="Ölçek, soru ve birleştirme yöntemi araştırmacı kararıdır. Puan girildikten sonra değiştirilemez; değişiklik için yeni sürüm açın.">
      <div className="grid gap-4 md:grid-cols-6">
        <div className="md:col-span-1"><Alan etiket="Sürüm adı"><input className={girdiSinifi} value={f.surum} onChange={(e) => setF({ ...f, surum: e.target.value })} placeholder="F1" /></Alan></div>
        <div className="md:col-span-5"><Alan etiket="Uzmana sorulan soru (puanın anlamı)"><input className={girdiSinifi} value={f.soru} onChange={(e) => setF({ ...f, soru: e.target.value })} /></Alan></div>
        <Alan etiket="Ölçek alt"><input type="number" className={girdiSinifi} value={f.min} onChange={(e) => setF({ ...f, min: +e.target.value })} /></Alan>
        <Alan etiket="Ölçek üst"><input type="number" className={girdiSinifi} value={f.max} onChange={(e) => setF({ ...f, max: +e.target.value })} /></Alan>
        <Alan etiket="Birleştirme"><select className={girdiSinifi} value={f.birlestirme} onChange={(e) => setF({ ...f, birlestirme: e.target.value as "ortalama" | "medyan" })}><option value="ortalama">Ortalama</option><option value="medyan">Medyan</option></select></Alan>
        <Alan etiket="Gerekli uzman sayısı"><input type="number" min={1} className={girdiSinifi} value={f.gerekli} onChange={(e) => setF({ ...f, gerekli: +e.target.value })} /></Alan>
        <div className="md:col-span-2 flex items-end"><Dugme disabled={olustur.isPending || !f.surum || f.soru.length < 10} onClick={() => olustur.mutate()}>Formu oluştur</Dugme></div>
      </div>
    </Kart>
  );
}

function Puanlar({ id, onDegisti }: { id: number; onDegisti: () => void }) {
  const q = useQuery({ queryKey: ["uzman-puan", id], queryFn: () => uzmanPuanlariApi(id) });
  const g = useQuery({ queryKey: ["uzman-gostergeler"], queryFn: uzmanGostergeleriApi, staleTime: Infinity });
  const [kod, setKod] = useState("");
  const [puan, setPuan] = useState<Record<string, string>>({});
  const [gerekce, setGerekce] = useState<Record<string, string>>({});
  const kaydet = useMutation({
    mutationFn: () => uzmanKaydetApi(id, kod.toUpperCase(),
      Object.fromEntries(Object.entries(puan).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v.replace(",", "."))])),
      Object.fromEntries(Object.entries(gerekce).filter(([, v]) => v.trim()))),
    onSuccess: () => { toast.success("Uzman puanları kaydedildi."); onDegisti(); }, onError: (e) => toast.error(apiHataMesaji(e)),
  });
  const sil = useMutation({ mutationFn: (k: string) => uzmanSilApi(id, k), onSuccess: () => { toast.success("Uzman silindi."); onDegisti(); }, onError: (e) => toast.error(apiHataMesaji(e)) });
  if (!q.data) return <Bos>Yükleniyor…</Bos>;
  const { form, uzmanlar } = q.data;
  const ac = (k: string) => {
    setKod(k);
    setPuan(Object.fromEntries(Object.entries(uzmanlar[k]?.puanlar ?? {}).map(([a, b]) => [a, String(b)])));
    setGerekce(uzmanlar[k]?.gerekceler ?? {});
  };
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
      <Kart baslik={`Uzmanlar — form ${form.surum}`} aciklama={form.soru}>
        {!Object.keys(uzmanlar).length ? <Bos>Henüz uzman puanı girilmedi.</Bos> : (
          <table className="tablo">
            <thead><tr><th>Uzman</th><th className="text-right">Girilen gösterge</th><th /></tr></thead>
            <tbody>{Object.entries(uzmanlar).map(([k, u]) => {
              const n = Object.keys(u.puanlar).length;
              return (
                <tr key={k}><td className="font-medium">{k}</td><td className="text-right sayi">{n}/13 {n === 13 ? <Rozet renk="yesil">tam</Rozet> : <Rozet renk="sari">eksik</Rozet>}</td>
                  <td className="text-right whitespace-nowrap"><Dugme ikincil onClick={() => ac(k)}>Düzenle</Dugme>{" "}<Dugme ikincil onClick={() => sil.mutate(k)}>Sil</Dugme></td></tr>
              );
            })}</tbody>
          </table>
        )}
      </Kart>
      <Kart baslik="Uzman puanı gir" aciklama={`Ölçek ${form.olcek_min}–${form.olcek_max}. Boş bırakılan gösterge sıfır sayılmaz; uzman tüm 13 göstergeyi puanlamadan hesaba katılmaz.`}>
        <div className="mb-4 max-w-xs"><Alan etiket="Uzman kodu" yardim="U01 … U99 (kimlik bilgisi girmeyin)."><input className={girdiSinifi} value={kod} onChange={(e) => setKod(e.target.value)} placeholder="U01" /></Alan></div>
        <div className="space-y-2 max-h-[34rem] overflow-y-auto pr-1">
          {g.data?.map((x) => (
            <div key={x.kod} className="grid grid-cols-[1fr_5rem] gap-2 items-start border-b border-border pb-2">
              <div>
                <div className="text-sm"><span className="font-mono text-[11px] text-muted-foreground mr-2">{x.kod}</span>{x.ad}</div>
                <input className={`${girdiSinifi} mt-1 text-xs`} placeholder="Gerekçe (isteğe bağlı)" value={gerekce[x.kod] ?? ""} onChange={(e) => setGerekce({ ...gerekce, [x.kod]: e.target.value })} />
              </div>
              <input inputMode="decimal" className={girdiSinifi} value={puan[x.kod] ?? ""} onChange={(e) => setPuan({ ...puan, [x.kod]: e.target.value })} aria-label={`${x.kod} puanı`} />
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Dugme disabled={kaydet.isPending || !/^[uU]\d{2}$/.test(kod) || !Object.values(puan).some((v) => v !== "")} onClick={() => kaydet.mutate()}>Kaydet</Dugme>
          <span className="text-xs text-muted-foreground">{Object.values(puan).filter((v) => v !== "").length}/13 gösterge · ortalama {sayi(avg(puan), 2)}</span>
        </div>
      </Kart>
    </div>
  );
}

function avg(p: Record<string, string>) {
  const v = Object.values(p).filter((x) => x !== "").map((x) => Number(x.replace(",", "."))).filter((x) => !Number.isNaN(x));
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}
