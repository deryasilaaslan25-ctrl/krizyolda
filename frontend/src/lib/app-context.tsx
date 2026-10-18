import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { benApi, emailDegistirApi, girisApi, kayitApi } from "./api";
import { apiHataMesaji, tokenOku, tokenSil, tokenYaz } from "./api-client";
import type { Kullanici } from "./domain";

type Sonuc = { basarili: true } | { basarili: false; hata: string };

interface Baglam {
  kullanici: Kullanici | null;
  yukleniyor: boolean;
  giris: (email: string, sifre: string) => Promise<Sonuc>;
  kayit: (email: string, sifre: string, tekrar: string, kurum: string, sektor: string, ek: string[]) => Promise<Sonuc>;
  cikis: () => void;
  yenile: () => Promise<void>;
  emailDegistir: (yeni: string, sifre: string) => Promise<Sonuc>;
}

const Ctx = createContext<Baglam | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [kullanici, setKullanici] = useState<Kullanici | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);

  const yenile = useCallback(async () => {
    if (!tokenOku()) { setKullanici(null); return; }
    try { setKullanici(await benApi()); } catch { tokenSil(); setKullanici(null); }
  }, []);

  useEffect(() => { yenile().finally(() => setYukleniyor(false)); }, [yenile]);

  const giris = async (email: string, sifre: string): Promise<Sonuc> => {
    try { const r = await girisApi(email, sifre); tokenYaz(r.access_token); setKullanici(r.kullanici); return { basarili: true }; }
    catch (e) { return { basarili: false, hata: apiHataMesaji(e, "E-posta veya şifre hatalı.") }; }
  };
  const kayit = async (email: string, sifre: string, tekrar: string, kurum: string, sektor: string, ek: string[]): Promise<Sonuc> => {
    try { const r = await kayitApi(email, sifre, tekrar, kurum, sektor, ek); tokenYaz(r.access_token); setKullanici(r.kullanici); return { basarili: true }; }
    catch (e) { return { basarili: false, hata: apiHataMesaji(e, "Hesap oluşturulamadı.") }; }
  };
  const emailDegistir = async (yeni: string, sifre: string): Promise<Sonuc> => {
    try { const r = await emailDegistirApi(yeni, sifre); tokenYaz(r.access_token); setKullanici(r.kullanici); return { basarili: true }; }
    catch (e) { return { basarili: false, hata: apiHataMesaji(e, "E-posta güncellenemedi.") }; }
  };
  const cikis = () => { tokenSil(); setKullanici(null); };

  return <Ctx.Provider value={{ kullanici, yukleniyor, giris, kayit, cikis, yenile, emailDegistir }}>{children}</Ctx.Provider>;
}

export function useApp() {
  const c = useContext(Ctx);
  if (!c) throw new Error("AppProvider eksik");
  return c;
}
