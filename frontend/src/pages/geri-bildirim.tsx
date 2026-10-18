import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { epostaGeriBildirimApi, epostaOnizleApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { RISK_ETIKETI } from "@/lib/domain";
import { tarihSaat } from "@/lib/format";
import { Dugme } from "@/components/ortak";

/** E-postadaki bağlantının açtığı onay sayfası. Etiket yalnız düğmeyle kaydedilir (e-posta tarayıcıları bağlantıyı otomatik açabilir). */
export default function GeriBildirim() {
  const p = new URLSearchParams(window.location.search);
  const token = p.get("token") ?? "";
  const oneri = p.get("karar") === "gercek_kriz" ? "gercek_kriz" : "onemsiz";
  const [karar, setKarar] = useState<"gercek_kriz" | "onemsiz">(oneri);
  const onizle = useQuery({ queryKey: ["gb-onizle", token], queryFn: () => epostaOnizleApi(token), enabled: !!token, retry: false });
  const kaydet = useMutation({ mutationFn: () => epostaGeriBildirimApi(token, karar) });
  useEffect(() => { document.title = "Geri bildirim — Krizyolda"; }, []);
  const a = kaydet.data ?? onizle.data;

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <div className="w-full max-w-lg surface-card p-6 space-y-5">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-9 rounded-full bg-signal" />
          <h1 className="font-display font-bold text-xl">Kriz uyarısı geri bildirimi</h1>
        </div>
        {!token || onizle.isError ? (
          <p className="text-sm text-red-700">{!token ? "Bağlantı eksik." : apiHataMesaji(onizle.error, "Bağlantı geçersiz ya da süresi dolmuş.")}</p>
        ) : !a ? <p className="text-sm text-muted-foreground">Yükleniyor...</p> : (
          <>
            <div className="rounded-xl border border-border p-4 text-sm space-y-1">
              <p className="font-semibold">{a.kurum}</p>
              <p>{RISK_ETIKETI[a.max_seviye]} · başlangıç {tarihSaat(a.baslangic)} · en yüksek risk puanı {a.max_risk?.toFixed(1) ?? "—"}/100</p>
              {a.terimler.length > 0 && <p className="text-xs text-muted-foreground">Öne çıkan sözcükler: {a.terimler.join(", ")}</p>}
            </div>
            {kaydet.isSuccess ? (
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 p-4 text-sm space-y-1">
                <p className="font-semibold">Teşekkürler, geri bildiriminiz kaydedildi: {a.geri_bildirim === "gercek_kriz" ? "Gerçek kriz" : "Önemsiz"}.</p>
                {a.geri_bildirim === "yanlis_alarm"
                  ? <p>Bu kriz için bir daha e-posta göndermeyeceğiz ve eşik geri bildiriminizle yeniden ayarlanacak. Krizin çok daha ciddi bir seviyeye çıkması dışında benzer krizler de bildirilmez.</p>
                  : <p>Bu alarm gerçek kriz olarak kaydedildi; eşik hesabında normal dönemden dışlanır ve benzer krizler için bilgi notu düşülür.</p>}
              </div>
            ) : (
              <>
                <p className="text-sm">Bu alarm sizce gerçek bir kriz mi?</p>
                <div className="flex gap-2">
                  {(["gercek_kriz", "onemsiz"] as const).map((k) => (
                    <button key={k} onClick={() => setKarar(k)}
                      className={`flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium ${karar === k ? (k === "gercek_kriz" ? "bg-red-700 text-white border-red-700" : "bg-primary text-primary-foreground") : "bg-card"}`}>
                      {k === "gercek_kriz" ? "Gerçek kriz" : "Önemsiz"}</button>))}
                </div>
                {a.geri_bildirim && <p className="text-xs text-muted-foreground">Mevcut etiket: {a.geri_bildirim === "gercek_kriz" ? "Gerçek kriz" : "Önemsiz"}</p>}
                <Dugme onClick={() => kaydet.mutate()} disabled={kaydet.isPending} className="w-full">Geri bildirimi kaydet</Dugme>
                {kaydet.isError && <p className="text-sm text-red-700">{apiHataMesaji(kaydet.error)}</p>}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
