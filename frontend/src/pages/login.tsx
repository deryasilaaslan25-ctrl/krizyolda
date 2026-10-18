import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { useApp } from "@/lib/app-context";
import { sifreSifirlaIsteApi } from "@/lib/api";
import { apiHataMesaji } from "@/lib/api-client";
import { Alan, Dugme, girdiSinifi } from "@/components/ortak";

type Mod = "giris" | "kayit" | "unuttum";

export default function Login() {
  const { giris, kayit } = useApp();
  const [mod, setMod] = useState<Mod>("giris");
  const [f, setF] = useState({ email: "", sifre: "", tekrar: "", kurum: "", sektor: "", ek: "" });
  const [hata, setHata] = useState("");
  const [mesgul, setMesgul] = useState(false);
  const al = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));

  async function gonder(e: FormEvent) {
    e.preventDefault();
    setHata("");
    setMesgul(true);
    try {
      if (mod === "unuttum") {
        await sifreSifirlaIsteApi(f.email);
        toast.success("Bu adres kayıtlıysa sıfırlama bağlantısı gönderildi.");
        setMod("giris");
        return;
      }
      const ek = f.ek.split(/[,\s;]+/).filter(Boolean);
      const s = mod === "giris" ? await giris(f.email, f.sifre) : await kayit(f.email, f.sifre, f.tekrar, f.kurum, f.sektor, ek);
      if (!s.basarili) setHata(s.hata);
    } catch (err) {
      setHata(apiHataMesaji(err));
    } finally {
      setMesgul(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden lg:flex flex-col justify-between bg-sidebar text-sidebar-foreground p-12">
        <div className="text-white font-semibold text-xl tracking-tight">krizyolda<span className="text-signal">.com</span></div>
        <div className="max-w-md">
          <h1 className="text-white text-3xl font-semibold leading-tight">Krizi, görünür hale gelmeden önce fark edin.</h1>
          <p className="mt-4 text-sm leading-relaxed text-sidebar-foreground/80">
            Kurumunuzla ilgili haber ve sosyal medya içeriklerini sürekli izler, 13 literatür göstergesiyle kuruma özgü risk düzeyini
            hesaplar ve eşik aşıldığında kayıtlı e-posta adreslerinize bildirir.
          </p>
          <dl className="mt-8 grid grid-cols-3 gap-4 text-xs">
            <div><dt className="text-sidebar-foreground/50">Gösterge</dt><dd className="text-white text-lg font-semibold mt-1">13</dd></div>
            <div><dt className="text-sidebar-foreground/50">Değerlendirme</dt><dd className="text-white text-lg font-semibold mt-1">2 beyin</dd></div>
            <div><dt className="text-sidebar-foreground/50">Geçmiş tarama</dt><dd className="text-white text-lg font-semibold mt-1">6 aya kadar</dd></div>
          </dl>
        </div>
        <p className="text-[11px] text-sidebar-foreground/50">Yalnızca erişilebilen kaynaklar taranır; kapsam her sonuçla birlikte gösterilir.</p>
      </div>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={gonder} className="w-full max-w-sm space-y-4">
          <div>
            <h2 className="text-xl font-semibold">{mod === "giris" ? "Giriş yap" : mod === "kayit" ? "Kurum hesabı oluştur" : "Şifre sıfırlama"}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {mod === "unuttum" ? "Kayıtlı e-posta adresinize sıfırlama bağlantısı göndeririz." : "Kurumunuzun izleme paneline erişin."}
            </p>
          </div>
          {mod === "kayit" && (
            <>
              <Alan etiket="Kurum adı"><input className={girdiSinifi} value={f.kurum} onChange={al("kurum")} required minLength={2} /></Alan>
              <Alan etiket="Sektör"><input className={girdiSinifi} value={f.sektor} onChange={al("sektor")} /></Alan>
            </>
          )}
          <Alan etiket="E-posta" yardim={mod === "kayit" ? "Kriz uyarıları ve haftalık raporlar bu adrese gönderilir." : undefined}>
            <input type="email" className={girdiSinifi} value={f.email} onChange={al("email")} required autoComplete="email" />
          </Alan>
          {mod !== "unuttum" && (
            <Alan etiket="Şifre" yardim={mod === "kayit" ? "En az 8 karakter." : undefined}>
              <input type="password" className={girdiSinifi} value={f.sifre} onChange={al("sifre")} required minLength={8} maxLength={72}
                autoComplete={mod === "giris" ? "current-password" : "new-password"} />
            </Alan>
          )}
          {mod === "kayit" && (
            <>
              <Alan etiket="Şifre (tekrar)"><input type="password" className={girdiSinifi} value={f.tekrar} onChange={al("tekrar")} required minLength={8} /></Alan>
              <Alan etiket="Ek bildirim adresleri (isteğe bağlı)" yardim="Virgülle ayırın; en fazla 5. Her adrese ayrı e-posta gider.">
                <input className={girdiSinifi} value={f.ek} onChange={al("ek")} placeholder="iletisim@kurum.com, hukuk@kurum.com" />
              </Alan>
            </>
          )}
          {hata && <p className="text-sm text-destructive">{hata}</p>}
          <Dugme type="submit" disabled={mesgul} className="w-full">
            {mod === "giris" ? "Giriş yap" : mod === "kayit" ? "Hesap oluştur" : "Bağlantı gönder"}
          </Dugme>
          <div className="flex justify-between text-sm">
            {mod === "giris" ? (
              <>
                <button type="button" className="text-muted-foreground hover:text-foreground" onClick={() => setMod("unuttum")}>Şifremi unuttum</button>
                <button type="button" className="font-medium text-accent-foreground hover:underline" onClick={() => setMod("kayit")}>Hesap oluştur</button>
              </>
            ) : (
              <button type="button" className="text-muted-foreground hover:text-foreground" onClick={() => setMod("giris")}>Girişe dön</button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
