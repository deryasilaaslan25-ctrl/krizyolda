import { useEffect, useState, type FormEvent } from "react";
import { Link } from "wouter";
import { epostaDogrulaApi, sifreSifirlaApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { Alan, Dugme, girdiSinifi } from "@/components/ortak";

/** E-postadaki bağlantılardan açılan oturumsuz sayfalar: e-posta doğrulama ve şifre sıfırlama. */
export default function HesapIslemleri({ tur }: { tur: "dogrula" | "sifirla" }) {
  const token = new URLSearchParams(window.location.search).get("token") ?? "";
  const [durum, setDurum] = useState<"bekliyor" | "tamam" | "hata">("bekliyor");
  const [mesaj, setMesaj] = useState("");
  const [sifre, setSifre] = useState("");

  useEffect(() => {
    if (tur !== "dogrula") return;
    if (!token) { setDurum("hata"); setMesaj("Bağlantı eksik."); return; }
    epostaDogrulaApi(token).then(() => setDurum("tamam")).catch((e) => { setDurum("hata"); setMesaj(apiHataMesaji(e)); });
  }, [tur, token]);

  async function sifirla(e: FormEvent) {
    e.preventDefault();
    try { await sifreSifirlaApi(token, sifre); setDurum("tamam"); } catch (err) { setDurum("hata"); setMesaj(apiHataMesaji(err)); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="surface-card p-8 w-full max-w-sm space-y-4">
        <div className="font-semibold text-lg">krizyolda<span className="text-signal">.com</span></div>
        {tur === "dogrula" ? (
          <p className="text-sm">{durum === "tamam" ? "E-posta adresiniz doğrulandı." : durum === "hata" ? mesaj : "Doğrulanıyor…"}</p>
        ) : durum === "tamam" ? (
          <p className="text-sm">Şifreniz güncellendi. Yeni şifrenizle giriş yapabilirsiniz.</p>
        ) : (
          <form onSubmit={sifirla} className="space-y-4">
            <Alan etiket="Yeni şifre" yardim="En az 8 karakter.">
              <input type="password" className={girdiSinifi} value={sifre} onChange={(e) => setSifre(e.target.value)} required minLength={8} maxLength={72} />
            </Alan>
            {durum === "hata" && <p className="text-sm text-destructive">{mesaj}</p>}
            <Dugme type="submit" className="w-full" disabled={!token}>Şifreyi güncelle</Dugme>
          </form>
        )}
        <Link href="/" className="block text-sm text-muted-foreground hover:text-foreground">Girişe dön</Link>
      </div>
    </div>
  );
}
