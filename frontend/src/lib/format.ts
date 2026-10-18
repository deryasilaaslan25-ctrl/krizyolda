export const sayi = (v: number | null | undefined, basamak = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : v.toLocaleString("tr-TR", { maximumFractionDigits: basamak, minimumFractionDigits: 0 });
export const yuzde = (v: number | null | undefined, basamak = 1) =>
  v === null || v === undefined ? "—" : `%${(v * 100).toLocaleString("tr-TR", { maximumFractionDigits: basamak })}`;
/** Backend UTC (tz'siz ISO) verir; yerel saate çevrilir. */
export const tarihSaat = (iso: string) => new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z")
  .toLocaleString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
