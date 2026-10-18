import type { ReactNode } from "react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";
import { RISK_ETIKETI, SEVIYE_ETIKETI, SEVIYE_RENK } from "@/lib/domain";

export function Kart({ baslik, aciklama, children, className, sag }: {
  baslik?: ReactNode; aciklama?: ReactNode; children: ReactNode; className?: string; sag?: ReactNode;
}) {
  return (
    <section className={cn("surface-card p-5", className)}>
      {(baslik || sag) && (
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            {baslik && <h2 className="font-display font-semibold text-base text-foreground">{baslik}</h2>}
            {aciklama && <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{aciklama}</p>}
          </div>
          {sag}
        </div>
      )}
      {children}
    </section>
  );
}

export function SeviyeRozeti({ seviye, buyuk }: { seviye: number; buyuk?: boolean }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border font-semibold tracking-wide",
      buyuk ? "px-4 py-1.5 text-sm" : "px-2.5 py-0.5 text-[11px]", SEVIYE_RENK[seviye] ?? SEVIYE_RENK[0])}>
      {SEVIYE_ETIKETI[seviye] ?? "—"}
    </span>
  );
}

/** Kuruma özgü eşik katmanının seviyesi (karar). */
export function RiskRozeti({ seviye, buyuk }: { seviye: number; buyuk?: boolean }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border font-semibold tracking-wide",
      buyuk ? "px-4 py-1.5 text-sm" : "px-2.5 py-0.5 text-[11px]", SEVIYE_RENK[seviye] ?? SEVIYE_RENK[0])}>
      {RISK_ETIKETI[seviye] ?? "—"}
    </span>
  );
}

/** Kod içi kaynak kimliğine literatür sekmesinden bağlantı. */
export function Atif({ kimlikler }: { kimlikler: string[] }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      {kimlikler.map((k) => (
        <Link key={k} href={`/literatur#${k}`}
          className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground hover:text-foreground hover:bg-secondary">
          {k}
        </Link>
      ))}
    </span>
  );
}

export function Bos({ children }: { children: ReactNode }) {
  return <div className="text-sm text-muted-foreground py-8 text-center">{children}</div>;
}

export function Dugme({ children, onClick, disabled, ikincil, type = "button", className }: {
  children: ReactNode; onClick?: () => void; disabled?: boolean; ikincil?: boolean; type?: "button" | "submit"; className?: string;
}) {
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={cn("inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        ikincil ? "border border-border bg-card hover:bg-muted text-foreground" : "bg-primary text-primary-foreground hover:bg-primary/90", className)}>
      {children}
    </button>
  );
}

export const girdiSinifi = "w-full rounded-lg border border-input bg-card px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring/40";

export function Alan({ etiket, yardim, children }: { etiket: string; yardim?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-foreground mb-1">{etiket}</span>
      {children}
      {yardim && <span className="block text-[11px] text-muted-foreground mt-1 leading-snug">{yardim}</span>}
    </label>
  );
}

const ROZET: Record<string, string> = {
  yesil: "bg-emerald-50 text-emerald-800 border-emerald-200", sari: "bg-amber-50 text-amber-800 border-amber-200",
  turuncu: "bg-orange-50 text-orange-800 border-orange-300", kirmizi: "bg-red-50 text-red-800 border-red-300",
  gri: "bg-muted text-muted-foreground border-border", mavi: "bg-accent text-accent-foreground border-accent-border",
};
export function Rozet({ renk = "gri", children }: { renk?: keyof typeof ROZET; children: ReactNode }) {
  return <span className={cn("inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap", ROZET[renk])}>{children}</span>;
}

export function Sekmeler<T extends string>({ deger, degistir, secenekler }: {
  deger: T; degistir: (v: T) => void; secenekler: { kod: T; ad: string }[];
}) {
  return (
    <div className="flex gap-1 border-b border-border mb-5 overflow-x-auto">
      {secenekler.map((s) => (
        <button key={s.kod} type="button" onClick={() => degistir(s.kod)}
          className={cn("px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors",
            deger === s.kod ? "border-signal text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}>
          {s.ad}
        </button>
      ))}
    </div>
  );
}

export function Sayfa({ baslik, aciklama, sag, children }: { baslik: string; aciklama?: ReactNode; sag?: ReactNode; children: ReactNode }) {
  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <h1 className="text-xl font-semibold">{baslik}</h1>
          {aciklama && <p className="text-sm text-muted-foreground mt-1 max-w-3xl">{aciklama}</p>}
        </div>
        {sag && <div className="flex gap-2 flex-wrap">{sag}</div>}
      </div>
      {children}
    </div>
  );
}

export function Uyari({ renk = "sari", children }: { renk?: "sari" | "kirmizi" | "mavi"; children: ReactNode }) {
  const s = { sari: "bg-amber-50 border-amber-200 text-amber-900", kirmizi: "bg-red-50 border-red-200 text-red-900", mavi: "bg-accent border-accent-border text-accent-foreground" }[renk];
  return <div className={cn("rounded-lg border px-4 py-3 text-sm leading-relaxed", s)}>{children}</div>;
}

export function Gosterge({ etiket, deger, alt }: { etiket: string; deger: ReactNode; alt?: ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground font-semibold">{etiket}</div>
      <div className="text-2xl font-semibold sayi mt-0.5">{deger}</div>
      {alt && <div className="text-xs text-muted-foreground mt-0.5">{alt}</div>}
    </div>
  );
}
