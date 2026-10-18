import { useState } from "react";
import { Link } from "wouter";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { alarmYanitApi, alarmlarApi, bildirimlerApi, geriBildirimApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { BILDIRIM_DURUMU, KUME_ADI, type Alarm } from "@/lib/domain";
import { sayi, tarihSaat } from "@/lib/format";
import { Bos, Dugme, Kart, Rozet, Sayfa, SeviyeRozeti, girdiSinifi } from "@/components/ortak";

const KUYRUK_ADI: Record<string, string> = {
  kuyrukta: "kuyrukta", gonderiliyor: "gönderiliyor", smtp_kabul: "SMTP kabul etti", tekrar_bekliyor: "yeniden denenecek",
  kalici_hata: "gönderilemedi", bastirildi: "bastırıldı",
};
const yerel = (iso: string | null) => (iso ? new Date(iso.endsWith("Z") ? iso : iso + "Z").toISOString().slice(0, 16) : "");

export default function Krizler() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["alarmlar"], queryFn: alarmlarApi, refetchInterval: 60_000 });
  const bildirim = useQuery({ queryKey: ["bildirimler"], queryFn: bildirimlerApi, refetchInterval: 60_000 });
  const [acik, setAcik] = useState<number | null>(null);
  const yenile = () => { qc.invalidateQueries({ queryKey: ["alarmlar"] }); qc.invalidateQueries({ queryKey: ["bildirimler"] }); };
  const geri = useMutation({
    mutationFn: (v: { id: number; k: string | null }) => geriBildirimApi(v.id, v.k),
    onSuccess: yenile, onError: (e) => toast.error(apiHataMesaji(e)),
  });

  return (
    <Sayfa baslik="Alarm Merkezi" aciklama="Kuruma özgü eşiğin aşıldığı dönemler. Bir alarm için e-posta bir kez gönderilir; sonraki e-postalar yalnızca seviye yükselirse ve bekleme süresi dolduysa gider.">
      {(bildirim.data?.ozet.kalici_hata ?? 0) > 0 && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 text-red-900 text-sm px-4 py-3">
          {bildirim.data!.ozet.kalici_hata} bildirim gönderilemedi. SMTP ayarlarını ve alıcı adreslerini kontrol edin (Ayarlar → Bildirim).
        </div>
      )}
      <Kart>
        {q.isLoading ? <Bos>Yükleniyor…</Bos> : !q.data?.length ? <Bos>Seçilen aralıkta Orta üzeri alarm yok.</Bos> : (
          <div className="overflow-x-auto">
            <table className="tablo">
              <thead><tr><th>Başlangıç</th><th>Durum</th><th>Seviye</th><th className="text-right">En yüksek risk</th><th>Tür</th><th>Bildirim</th><th /></tr></thead>
              <tbody>
                {q.data.map((a: Alarm) => (
                  <>
                    <tr key={a.id} className="cursor-pointer hover:bg-muted/40" onClick={() => setAcik(acik === a.id ? null : a.id)}>
                      <td>{tarihSaat(a.baslangic)}</td>
                      <td>{a.acik ? <Rozet renk="kirmizi">Açık</Rozet> : <Rozet>Kapandı</Rozet>}</td>
                      <td><SeviyeRozeti seviye={a.max_seviye} /></td>
                      <td className="text-right sayi">{sayi(a.max_risk, 1)}</td>
                      <td>{a.baskin_kume ? KUME_ADI[a.baskin_kume] : "—"}</td>
                      <td>
                        {BILDIRIM_DURUMU[a.bildirim_durumu] ?? a.bildirim_durumu}
                        {Object.keys(a.bildirim_kuyrugu ?? {}).length > 0 && (
                          <div className="text-[11px] text-muted-foreground">{Object.entries(a.bildirim_kuyrugu).map(([d, n]) => `${n} ${KUYRUK_ADI[d] ?? d}`).join(", ")}</div>
                        )}
                      </td>
                      <td className="text-muted-foreground text-xs">{acik === a.id ? "Kapat" : "Ayrıntı"}</td>
                    </tr>
                    {acik === a.id && (
                      <tr key={`d${a.id}`}><td colSpan={7} className="bg-muted/30">
                        <Ayrinti a={a} onGeri={(k) => geri.mutate({ id: a.id, k })} onYanit={yenile} />
                      </td></tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Kart>
    </Sayfa>
  );
}

function Ayrinti({ a, onGeri, onYanit }: { a: Alarm; onGeri: (k: string | null) => void; onYanit: () => void }) {
  const [ilk, setIlk] = useState(yerel(a.ilk_yanit_zamani));
  const [coz, setCoz] = useState(yerel(a.cozum_zamani));
  const kaydet = useMutation({
    mutationFn: () => alarmYanitApi(a.id, { ilk_yanit_zamani: ilk ? new Date(ilk).toISOString() : null, cozum_zamani: coz ? new Date(coz).toISOString() : null }),
    onSuccess: () => { toast.success("Yanıt zamanları kaydedildi."); onYanit(); }, onError: (e) => toast.error(apiHataMesaji(e)),
  });
  return (
    <div className="grid gap-5 lg:grid-cols-3 py-2">
      <div className="space-y-2 text-sm">
        <div className="font-medium">Süre ve kapsam</div>
        <div className="text-muted-foreground">{tarihSaat(a.baslangic)} – {tarihSaat(a.bitis)} · {a.saat_sayisi} saat</div>
        {a.terimler?.length > 0 && <div>Öne çıkan terimler: {a.terimler.join(", ")}</div>}
        {a.tehdit && <div>Sorumluluk değerlendirmesi: {a.tehdit}</div>}
        {a.bastirma_nedeni && <div className="text-amber-800">Bildirim bastırıldı: {a.bastirma_nedeni}</div>}
        <Link href={`/pr?alarm=${a.id}`} className="inline-block underline text-accent-foreground">Bu alarm için PR danışmanı ve kontrol listesi</Link>
      </div>
      <div className="space-y-2 text-sm">
        <div className="font-medium">Bu alarm gerçek bir kriz miydi?</div>
        <p className="text-xs text-muted-foreground">Cevabınız bu kurumun eşiğini ve benzer alarmların bildirimini ayarlar.</p>
        <div className="flex gap-2 flex-wrap">
          <Dugme ikincil onClick={() => onGeri(a.geri_bildirim === "gercek_kriz" ? null : "gercek_kriz")} className={a.geri_bildirim === "gercek_kriz" ? "ring-2 ring-signal" : ""}>Gerçek kriz</Dugme>
          <Dugme ikincil onClick={() => onGeri(a.geri_bildirim === "yanlis_alarm" ? null : "onemsiz")} className={a.geri_bildirim === "yanlis_alarm" ? "ring-2 ring-signal" : ""}>Önemsiz</Dugme>
        </div>
      </div>
      <div className="space-y-2 text-sm">
        <div className="font-medium">Kurumun yanıt zamanları</div>
        <label className="block text-xs text-muted-foreground">İlk kamuya yanıt<input type="datetime-local" className={girdiSinifi} value={ilk} onChange={(e) => setIlk(e.target.value)} /></label>
        <label className="block text-xs text-muted-foreground">Çözüm<input type="datetime-local" className={girdiSinifi} value={coz} onChange={(e) => setCoz(e.target.value)} /></label>
        <Dugme onClick={() => kaydet.mutate()} disabled={kaydet.isPending}>Kaydet</Dugme>
      </div>
    </div>
  );
}
