import { useEffect, type ComponentType } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Route, Switch, Router as WouterRouter, useLocation } from "wouter";
import { Toaster } from "sonner";
import { AppProvider, useApp } from "@/lib/app-context";
import { Yerlesim } from "@/components/yerlesim";
import Login from "@/pages/login";
import HesapIslemleri from "@/pages/hesap-islemleri";
import Panel from "@/pages/panel";
import Icerikler from "@/pages/icerikler";
import Krizler from "@/pages/krizler";
import Profil from "@/pages/profil";
import Beyinler from "@/pages/beyinler";
import Literatur from "@/pages/literatur";
import Ayarlar from "@/pages/ayarlar";
import Kaynaklar from "@/pages/kaynaklar";
import PR from "@/pages/pr";
import Itibar from "@/pages/itibar";
import Uzman from "@/pages/uzman";
import GeriBildirim from "@/pages/geri-bildirim";

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } });

function Korumali({ bilesen: B }: { bilesen: ComponentType }) {
  const { kullanici, yukleniyor } = useApp();
  const [, git] = useLocation();
  useEffect(() => { if (!yukleniyor && !kullanici) git("/"); }, [kullanici, yukleniyor, git]);
  if (!kullanici) return null;
  return <Yerlesim><B /></Yerlesim>;
}

function Yonlendirme() {
  const { kullanici, yukleniyor } = useApp();
  const [, git] = useLocation();
  useEffect(() => { if (!yukleniyor && kullanici) git("/panel"); }, [kullanici, yukleniyor, git]);
  return <Login />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
        <AppProvider>
          <Switch>
            <Route path="/" component={Yonlendirme} />
            <Route path="/geri-bildirim" component={GeriBildirim} />
            <Route path="/eposta-dogrula">{() => <HesapIslemleri tur="dogrula" />}</Route>
            <Route path="/sifre-sifirla">{() => <HesapIslemleri tur="sifirla" />}</Route>
            <Route path="/panel">{() => <Korumali bilesen={Panel} />}</Route>
            <Route path="/icerikler">{() => <Korumali bilesen={Icerikler} />}</Route>
            <Route path="/krizler">{() => <Korumali bilesen={Krizler} />}</Route>
            <Route path="/profil">{() => <Korumali bilesen={Profil} />}</Route>
            <Route path="/beyinler">{() => <Korumali bilesen={Beyinler} />}</Route>
            <Route path="/pr">{() => <Korumali bilesen={PR} />}</Route>
            <Route path="/itibar">{() => <Korumali bilesen={Itibar} />}</Route>
            <Route path="/literatur">{() => <Korumali bilesen={Literatur} />}</Route>
            <Route path="/kaynaklar">{() => <Korumali bilesen={Kaynaklar} />}</Route>
            <Route path="/ayarlar">{() => <Korumali bilesen={Ayarlar} />}</Route>
            <Route path="/uzman">{() => <Korumali bilesen={Uzman} />}</Route>
            <Route>{() => <div className="text-center py-24 text-muted-foreground">Sayfa bulunamadı.</div>}</Route>
          </Switch>
          <Toaster position="top-right" richColors />
        </AppProvider>
      </WouterRouter>
    </QueryClientProvider>
  );
}
