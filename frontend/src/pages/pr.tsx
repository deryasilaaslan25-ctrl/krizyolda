import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { alarmlarApi, kontrolIsaretleApi, kontrolListesiApi, prOlcutleriApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { sayi, tarihSaat, yuzde } from "@/lib/format";
import { Bos, Gosterge, Kart, Rozet, Sayfa, Sekmeler, girdiSinifi } from "@/components/ortak";
import PRDanisman from "@/pages/pr-danisman";

type Sekme = "danisman" | "liste" | "olcut";
const dk = (v: number | null) => (v === null ? "—" : v < 90 ? `${sayi(v, 0)} dk` : `${sayi(v / 60, 1)} sa`);

export default function PR() {
  const baslangicAlarm = Number(new URLSearchParams(window.location.search).get("alarm") ?? 0) || 0;
  const [sekme, setSekme] = useState<Sekme>(baslangicAlarm ? "liste" : "danisman");
  return (
    <Sayfa baslik="PR Danışmanı">
      <Sekmeler deger={sekme} degistir={setSekme} secenekler={[
        { kod: "danisman", ad: "Danışman" }, { kod: "liste", ad: "Kriz kontrol listesi" }, { kod: "olcut", ad: "Süreç ölçütleri" }]} />
      {sekme === "danisman" ? <PRDanisman /> : sekme === "liste" ? <Liste baslangic={baslangicAlarm} /> : <Olcutler />}
    </Sayfa>
  );
}

function Liste({ baslangic }: { baslangic: number }) {
  const qc = useQueryClient();
  const [alarm, setAlarm] = useState(baslangic);
  const alarmlar = useQuery({ queryKey: ["alarmlar"], queryFn: alarmlarApi });
  const q = useQuery({ queryKey: ["kontrol", alarm], queryFn: () => kontrolListesiApi(alarm) });
  const isaret = useMutation({
    mutationFn: (v: { madde: string; tamam: boolean }) => kontrolIsaretleApi(v.madde, v.tamam, alarm),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kontrol", alarm] }), onError: (e) => toast.error(apiHataMesaji(e)),
  });
  if (!q.data) return <Bos>Yükleniyor…</Bos>;
  const k = q.data;
  const tamam = new Set(k.tamamlanan);
  const gorunen = alarm ? k.evreler.filter((e) => e.kod !== "hazirlik") : k.evreler.filter((e) => e.kod === "hazirlik");

  return (
    <div className="space-y-4">
      <Kart>
        <div className="grid gap-4 md:grid-cols-[1fr_2fr] items-end">
          <label className="block text-xs font-medium">Liste
            <select className={`${girdiSinifi} mt-1`} value={alarm} onChange={(e) => setAlarm(Number(e.target.value))}>
              <option value={0}>Genel hazırlık (alarmdan bağımsız)</option>
              {alarmlar.data?.map((a) => <option key={a.id} value={a.id}>Alarm {a.id} — {tarihSaat(a.baslangic)} {a.acik ? "(açık)" : ""}</option>)}
            </select>
          </label>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Her alarm için ayrı işaretlenir. Madde işaretlemek sistemde kayıt tutar; kimsenin yerine iş yapmaz ve herhangi bir mesajı otomatik yayımlamaz.
            Evre yapısı <a className="underline" href={k.kaynak.url} target="_blank" rel="noreferrer noopener">{k.kaynak.ad}</a> yazısından uyarlanmıştır.
          </p>
        </div>
      </Kart>
      {gorunen.map((e) => {
        const maddeler = k.maddeler.filter((m) => m.evre === e.kod);
        const bitti = maddeler.filter((m) => tamam.has(m.kod)).length;
        return (
          <Kart key={e.kod} baslik={e.ad} aciklama={e.aciklama} sag={<Rozet renk={bitti === maddeler.length ? "yesil" : "gri"}>{bitti}/{maddeler.length}</Rozet>}>
            <ul className="space-y-2">
              {maddeler.map((m) => (
                <li key={m.kod}>
                  <label className="flex items-start gap-3 text-sm cursor-pointer">
                    <input type="checkbox" className="mt-1" checked={tamam.has(m.kod)} onChange={(ev) => isaret.mutate({ madde: m.kod, tamam: ev.target.checked })} />
                    <span className={tamam.has(m.kod) ? "text-muted-foreground line-through" : ""}>{m.metin}</span>
                  </label>
                </li>
              ))}
            </ul>
          </Kart>
        );
      })}
      <Kart baslik="Önerilen ilk yanıt hedefleri" aciklama="Öneridir; kurumunuz kendi iletişim ve hukuk süreçlerine göre belirler. Hangi şeyin söyleneceği için Danışman sekmesindeki SCCT stratejisine bakın.">
        <table className="tablo">
          <thead><tr><th>Kriz türü</th><th>Yaklaşım</th><th>İlk yanıt hedefi</th></tr></thead>
          <tbody>{k.yanit_hedefleri.map((h) => <tr key={h.tur}><td className="font-medium">{h.tur}</td><td>{h.yaklasim}</td><td>{h.hedef}</td></tr>)}</tbody>
        </table>
      </Kart>
    </div>
  );
}

function Olcutler() {
  const q = useQuery({ queryKey: ["pr-olcut"], queryFn: prOlcutleriApi });
  if (!q.data) return <Bos>Yükleniyor…</Bos>;
  const { ozet, alarmlar } = q.data;
  return (
    <div className="space-y-4">
      <Kart>
        <div className="grid gap-6 sm:grid-cols-3">
          <Gosterge etiket="Yüksek ve üzeri alarm" deger={ozet.alarm_sayisi} />
          <Gosterge etiket="İlk yanıt süresi (medyan)" deger={dk(ozet.ilk_yanit_medyan_dk)} alt="alarm başlangıcından ilk kamuya yanıta" />
          <Gosterge etiket="Çözüm süresi (medyan)" deger={dk(ozet.cozum_medyan_dk)} alt="alarm başlangıcından çözüme" />
        </div>
        <p className="text-xs text-muted-foreground mt-4">Süreler, Alarm Merkezi’nde girdiğiniz yanıt ve çözüm zamanlarından hesaplanır; girilmeyen zaman eksik sayılır, sıfır sayılmaz.</p>
      </Kart>
      <Kart baslik="Alarm bazında">
        {!alarmlar.length ? <Bos>Henüz Yüksek seviye alarm yok.</Bos> : (
          <table className="tablo">
            <thead><tr><th>Alarm</th><th>Başlangıç</th><th className="text-right">İlk yanıt</th><th className="text-right">Çözüm</th><th className="text-right">Sosyal içerik</th><th className="text-right">Olumsuz oran</th></tr></thead>
            <tbody>{alarmlar.map((a) => (
              <tr key={a.alarm_id}><td>#{a.alarm_id} {a.acik && <Rozet renk="kirmizi">Açık</Rozet>}</td><td>{tarihSaat(a.baslangic)}</td>
                <td className="text-right sayi">{dk(a.ilk_yanit_dk)}</td><td className="text-right sayi">{dk(a.cozum_dk)}</td>
                <td className="text-right sayi">{sayi(a.sosyal_icerik, 0)}</td><td className="text-right sayi">{yuzde(a.olumsuz_oran)}</td></tr>
            ))}</tbody>
          </table>
        )}
      </Kart>
    </div>
  );
}
