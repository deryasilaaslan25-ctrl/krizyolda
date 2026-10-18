import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { iceriklerApi } from "@/lib/api";
import { PLATFORM_ADI, type Icerik } from "@/lib/domain";
import { sayi, tarihSaat } from "@/lib/format";
import { Bos, Dugme, Kart, Rozet, Sayfa, girdiSinifi } from "@/components/ortak";

const SAYFA = 25;
const DUYGU: Record<string, { ad: string; renk: "yesil" | "kirmizi" | "gri" }> = {
  olumlu: { ad: "Olumlu", renk: "yesil" }, olumsuz: { ad: "Olumsuz", renk: "kirmizi" }, notr: { ad: "Nötr", renk: "gri" },
};
const TUR_ADI: Record<string, string> = { bahsetme: "Bahsetme", yorum: "Yorum", gonderi: "Gönderi", haber: "Haber" };

export default function Icerikler() {
  const [f, setF] = useState({ tur: "", platform: "", duygu: "", icerik_turu: "", arama: "" });
  const [sayfa, setSayfa] = useState(0);
  const [acik, setAcik] = useState<number | null>(null);
  const params = { ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), sayfa: sayfa + 1, boyut: SAYFA };
  const q = useQuery({ queryKey: ["icerikler", params], queryFn: () => iceriklerApi(params), placeholderData: (p) => p });
  const guncelle = (k: keyof typeof f, v: string) => { setF((p) => ({ ...p, [k]: v })); setSayfa(0); };
  const toplam = q.data?.toplam ?? 0;

  return (
    <Sayfa baslik="Bahsetmeler" aciklama="Kurumunuzla ilgili toplanan haber ve sosyal medya içerikleri. Duygu etiketi otomatiktir; hatalı olabilir, bu yüzden kanıt sözcükleri gösterilir.">
      <Kart className="mb-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <input className={girdiSinifi} placeholder="Metinde ara" value={f.arama} onChange={(e) => guncelle("arama", e.target.value)} />
          <select className={girdiSinifi} value={f.tur} onChange={(e) => guncelle("tur", e.target.value)}>
            <option value="">Tüm türler</option><option value="sosyal">Sosyal</option><option value="haber">Haber</option>
          </select>
          <select className={girdiSinifi} value={f.platform} onChange={(e) => guncelle("platform", e.target.value)}>
            <option value="">Tüm kaynaklar</option>
            {Object.entries(PLATFORM_ADI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className={girdiSinifi} value={f.duygu} onChange={(e) => guncelle("duygu", e.target.value)}>
            <option value="">Tüm duygular</option><option value="olumlu">Olumlu</option><option value="olumsuz">Olumsuz</option><option value="notr">Nötr</option>
          </select>
          <select className={girdiSinifi} value={f.icerik_turu} onChange={(e) => guncelle("icerik_turu", e.target.value)}>
            <option value="">Tüm içerik türleri</option>
            {Object.entries(TUR_ADI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </Kart>

      <Kart>
        {q.isLoading ? <Bos>Yükleniyor…</Bos> : toplam === 0 ? <Bos>Bu filtreyle içerik bulunamadı. Tarama henüz yapılmamış ya da seçilen kaynaklarda içerik yok olabilir; Kaynaklar sayfasında her kaynağın durumunu görebilirsiniz.</Bos> : (
          <>
            <div className="divide-y divide-border">
              {q.data!.ogeler.map((i: Icerik) => (
                <article key={i.id} className="py-3.5">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mb-1">
                    <span className="font-medium text-foreground">{PLATFORM_ADI[i.platform] ?? i.platform}</span>
                    <Rozet renk="mavi">{TUR_ADI[i.icerik_turu] ?? i.icerik_turu}</Rozet>
                    {i.erisim === "bagli" && <Rozet renk="gri">Kurum hesabı</Rozet>}
                    {i.duygu_etiketi && <Rozet renk={DUYGU[i.duygu_etiketi].renk}>{DUYGU[i.duygu_etiketi].ad}</Rozet>}
                    {i.scct?.tip_adi && <Rozet renk="sari">{i.scct.tip_adi}</Rozet>}
                    <span>{tarihSaat(i.tarih)}</span>{i.yazar && <span>· {i.yazar}</span>}
                    {i.tur === "sosyal" && <span className="sayi">· {sayi(i.begeni, 0)} beğeni · {sayi(i.yorum, 0)} yorum · {sayi(i.paylasim, 0)} paylaşım</span>}
                  </div>
                  {i.baslik && i.baslik !== i.metin && <h3 className="text-sm font-medium">{i.baslik}</h3>}
                  <p className="text-sm leading-relaxed text-foreground/90 line-clamp-3">{i.metin}</p>
                  <div className="flex gap-3 mt-1.5 text-xs">
                    {i.url && <a href={i.url} target="_blank" rel="noreferrer noopener" className="text-accent-foreground underline">Kaynağa git</a>}
                    <button className="text-muted-foreground hover:text-foreground" onClick={() => setAcik(acik === i.id ? null : i.id)}>{acik === i.id ? "Kanıtı gizle" : "Etiket kanıtı"}</button>
                  </div>
                  {acik === i.id && (
                    <div className="mt-2 rounded-lg bg-muted/60 p-3 text-xs space-y-1">
                      <div>Duygu motoru: {i.duygu?.motor ?? "—"} · öfke {i.duygu?.ofke ?? 0} · korku {i.duygu?.korku ?? 0} · iğrenme {i.duygu?.igrenme ?? 0} · {i.duygu?.toplam_sozcuk ?? 0} sözcük</div>
                      {i.duygu?.kanitlar?.length ? <div>Eşleşen sözcükler: {i.duygu.kanitlar.slice(0, 12).map((k) => `${k.sozcuk}${k.olumsuzlandi ? " (olumsuzlandı)" : ""}`).join(", ")}</div> : <div>Sözlük eşleşmesi yok.</div>}
                      {i.niyet?.length > 0 && <div>Davranış niyeti ifadeleri: {i.niyet.join(", ")}</div>}
                      {i.scct?.seviye !== undefined && <div>SCCT sorumluluk düzeyi: {i.scct.seviye} / 3</div>}
                    </div>
                  )}
                </article>
              ))}
            </div>
            <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
              <span>{toplam.toLocaleString("tr-TR")} içerik</span>
              <div className="flex gap-2 items-center">
                <Dugme ikincil disabled={sayfa === 0} onClick={() => setSayfa(sayfa - 1)}>Önceki</Dugme>
                <span>{sayfa + 1} / {Math.max(1, Math.ceil(toplam / SAYFA))}</span>
                <Dugme ikincil disabled={(sayfa + 1) * SAYFA >= toplam} onClick={() => setSayfa(sayfa + 1)}>Sonraki</Dugme>
              </div>
            </div>
          </>
        )}
      </Kart>
    </Sayfa>
  );
}
