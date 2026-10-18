import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_ANAHTARI = "krizyolda:token";

export const tokenOku = () => sessionStorage.getItem(TOKEN_ANAHTARI);
export const tokenYaz = (t: string) => sessionStorage.setItem(TOKEN_ANAHTARI, t);
export const tokenSil = () => sessionStorage.removeItem(TOKEN_ANAHTARI);

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = tokenOku();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e?.response?.status === 401) tokenSil();
    return Promise.reject(e);
  },
);

export function apiHataMesaji(hata: unknown, varsayilan = "Bir hata oluştu, lütfen tekrar deneyin."): string {
  if (axios.isAxiosError(hata)) {
    const d = hata.response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, "");
    if (hata.code === "ERR_NETWORK") return "Sunucuya bağlanılamadı. Backend'in çalıştığından emin olun.";
  }
  return varsayilan;
}
