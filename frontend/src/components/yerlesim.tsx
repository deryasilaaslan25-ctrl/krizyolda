import { useState, type ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { useApp } from "@/lib/app-context";
import { dogrulamaGonderApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Uyari } from "@/components/ortak";

type Oge = { yol: string; ad: string; yonetici?: boolean };
const GRUPLAR: { baslik: string; ogeler: Oge[] }[] = [
  { baslik: "İzleme", ogeler: [
    { yol: "/panel", ad: "Genel Bakış" }, { yol: "/icerikler", ad: "Bahsetmeler" },
    { yol: "/krizler", ad: "Alarm Merkezi" }, { yol: "/profil", ad: "Kurum Profili" } ] },
  { baslik: "Analiz", ogeler: [
    { yol: "/beyinler", ad: "İki Beyin" }, { yol: "/itibar", ad: "İtibar Ölçümü" }, { yol: "/literatur", ad: "Yöntem ve Literatür" } ] },
  { baslik: "Danışmanlık", ogeler: [ { yol: "/pr", ad: "PR Danışmanı" } ] },
  { baslik: "Yönetim", ogeler: [
    { yol: "/kaynaklar", ad: "Kaynaklar" }, { yol: "/ayarlar", ad: "Ayarlar" }, { yol: "/uzman", ad: "Uzman Paneli", yonetici: true } ] },
];

export function Yerlesim({ children }: { children: ReactNode }) {
  const { kullanici, cikis } = useApp();
  const [konum] = useLocation();
  const [acik, setAcik] = useState(false);
  const dogrulama = useMutation({
    mutationFn: dogrulamaGonderApi,
    onSuccess: () => toast.success("Doğrulama e-postası kuyruğa alındı."),
    onError: (e) => toast.error(apiHataMesaji(e)),
  });

  const menu = (
    <nav className="flex-1 overflow-y-auto py-4 px-3">
      {GRUPLAR.map((g) => (
        <div key={g.baslik} className="mb-5">
          <div className="px-3 mb-1.5 text-[10px] uppercase tracking-[0.12em] font-semibold text-sidebar-foreground/50">{g.baslik}</div>
          {g.ogeler.filter((o) => !o.yonetici || kullanici?.rol === "yonetici").map((o) => {
            const aktif = konum === o.yol || (o.yol !== "/panel" && konum.startsWith(o.yol));
            return (
              <Link key={o.yol} href={o.yol} onClick={() => setAcik(false)}
                className={cn("block rounded-md px-3 py-2 text-[13px] transition-colors",
                  aktif ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium border-l-2 border-signal" : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-white")}>
                {o.ad}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen lg:flex">
      <aside className={cn("bg-sidebar text-sidebar-foreground flex-col w-64 shrink-0 lg:sticky lg:top-0 lg:h-screen lg:flex",
        acik ? "flex fixed inset-y-0 left-0 z-40" : "hidden")}>
        <div className="px-6 py-5 border-b border-sidebar-border">
          <div className="text-white font-semibold text-lg tracking-tight">krizyolda<span className="text-signal">.com</span></div>
          <div className="text-[11px] text-sidebar-foreground/60 mt-0.5">Kriz erken uyarı ve itibar izleme</div>
        </div>
        {menu}
        <div className="border-t border-sidebar-border px-5 py-4">
          <div className="text-sm text-white font-medium truncate">{kullanici?.kurum}</div>
          <div className="text-[11px] text-sidebar-foreground/60 truncate">{kullanici?.email}</div>
          <button onClick={cikis} className="mt-2 text-xs text-sidebar-foreground hover:text-white underline underline-offset-2">Çıkış yap</button>
        </div>
      </aside>
      {acik && <div className="fixed inset-0 bg-black/40 z-30 lg:hidden" onClick={() => setAcik(false)} />}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="lg:hidden bg-sidebar text-white px-4 py-3 flex items-center justify-between sticky top-0 z-20">
          <span className="font-semibold">krizyolda<span className="text-signal">.com</span></span>
          <button onClick={() => setAcik(true)} className="text-sm border border-sidebar-border rounded px-3 py-1">Menü</button>
        </header>
        <main className="flex-1 w-full max-w-[1400px] mx-auto px-4 sm:px-8 py-7 space-y-4">
          {kullanici && !kullanici.eposta_dogrulandi && (
            <Uyari>
              E-posta adresiniz henüz doğrulanmadı. Doğrulama bağlantısı için gelen kutunuzu kontrol edin.{" "}
              <button className="underline font-medium" onClick={() => dogrulama.mutate()} disabled={dogrulama.isPending}>Yeniden gönder</button>
            </Uyari>
          )}
          {kullanici && !kullanici.eposta_gonderimi_hazir && (
            <Uyari renk="kirmizi">
              Sunucuda e-posta gönderimi (SMTP) yapılandırılmamış. Kriz uyarıları ve haftalık raporlar kuyrukta bekler, SMTP ayarlanana kadar gönderilmez.
            </Uyari>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
