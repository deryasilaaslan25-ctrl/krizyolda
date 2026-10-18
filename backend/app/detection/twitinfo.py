"""
TwitInfo Algoritma 1 [MARCUS2011].

İki kullanım:
  1) AkisNormallestirici: her gösterge için ayrı çalışan akış kestiricisi
     (Rapor Bölüm 3.2). Skor güncellemeden ÖNCEKİ duruma göre hesaplanır:
         s_t = (x_t − μ_{t−1}) / (√(π/2) · OMS_{t−1})        [GEARY1935]
     Güncelleme (Algoritma 1, update):
         diff = |μ_{t−1} − x_t|
         OMS_t = α·diff + (1−α)·OMS_{t−1}
         μ_t  = α·x_t + (1−α)·μ_{t−1}                         α = 0,125 [MARCUS2011; RFC6298; JACOBSON1988]
     Başlatma: μ = C1, OMS = variance(C1..Cp), p = 5 (popülasyon varyansı:
     Rapor Bölüm 7, karar 4). OMS = 0 ise skor tanımsız → eksik.

  2) zirve_pencereleri: Algoritma 1'in çevrimdışı zirve bulma döngüsü
     (τ = 2). Panelde G1 hacim zirvelerini işaretlemek için kullanılır;
     KRE formülüne girmez.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.literatur import ALFA, OMS_SIGMA_CARPANI, P_BASLATMA, TAU


def guncelle(ortalama: float, oms: float, deger: float, alfa: float = ALFA) -> tuple[float, float]:
    """Algoritma 1 'update' fonksiyonu [MARCUS2011]."""
    fark = abs(ortalama - deger)
    yeni_oms = alfa * fark + (1.0 - alfa) * oms
    yeni_ortalama = alfa * deger + (1.0 - alfa) * ortalama
    return yeni_ortalama, yeni_oms


def populasyon_varyansi(degerler: Sequence[float]) -> float:
    n = len(degerler)
    m = sum(degerler) / n
    return sum((d - m) ** 2 for d in degerler) / n


@dataclass
class AkisDurumu:
    ortalama: Optional[float] = None
    oms: Optional[float] = None
    baslatma_tamponu: list[float] = field(default_factory=list)

    @property
    def hazir(self) -> bool:
        return self.ortalama is not None


class AkisNormallestirici:
    """Tek bir gösterge için akış tabanlı z-skoru (Rapor Bölüm 3.2)."""

    def __init__(self, alfa: float = ALFA, p: int = P_BASLATMA):
        self.alfa = alfa
        self.p = p
        self.durum = AkisDurumu()

    def esik_karsiligi(self, k_sigma: float) -> Optional[float]:
        """Bir sonraki pencere için +kσ'ya karşılık gelen HAM değer:
        x* = μ + k·√(π/2)·OMS  (Bölüm 3.2 formülünün tersi). Kuruma özgüdür,
        çünkü μ ve OMS o kurumun kendi akışından gelir."""
        d = self.durum
        if not d.hazir or not d.oms:
            return None
        return d.ortalama + k_sigma * OMS_SIGMA_CARPANI * d.oms

    def adim(self, x: Optional[float]) -> Optional[float]:
        """Bir pencereyi işler; skor (tanımsızsa None) döndürür.
        x None ise gösterge eksiktir; durum güncellenmez (Tasarım kararı 13)."""
        if x is None:
            return None
        d = self.durum
        if not d.hazir:
            d.baslatma_tamponu.append(float(x))
            if len(d.baslatma_tamponu) == self.p:
                tampon = d.baslatma_tamponu
                d.ortalama = tampon[0]                      # μ = C1
                d.oms = populasyon_varyansi(tampon)         # OMS = variance(C1..Cp)
                for c in tampon[1:]:                        # döngü i = 2'den başlar
                    d.ortalama, d.oms = guncelle(d.ortalama, d.oms, c, self.alfa)
                d.baslatma_tamponu = []
            return None
        skor: Optional[float]
        if d.oms and d.oms > 0:
            skor = (x - d.ortalama) / (OMS_SIGMA_CARPANI * d.oms)
        else:
            skor = None                                     # OMS = 0 → tanımsız
        d.ortalama, d.oms = guncelle(d.ortalama, d.oms, float(x), self.alfa)
        return skor


def zirve_pencereleri(C: Sequence[float], alfa: float = ALFA, tau: float = TAU,
                      p: int = P_BASLATMA) -> list[tuple[int, int]]:
    """TwitInfo Algoritma 1, find_peak_windows (0 tabanlı indeksler) [MARCUS2011].

    Makaledeki sözde kodun doğrudan çevirisidir. meandev = 0 iken bölme
    tanımsız olduğundan o adımda zirve testi yapılmaz, yalnız güncelleme yapılır.
    """
    n = len(C)
    if n < max(2, p):
        return []
    pencereler: list[tuple[int, int]] = []
    ortalama = float(C[0])
    oms = populasyon_varyansi(C[:p])

    def asti(i: int) -> bool:
        return oms > 0 and abs(C[i] - ortalama) / oms > tau and C[i] > C[i - 1]

    i = 1
    while i < n:
        if asti(i):
            bas = i - 1
            son = i
            while i < n and C[i] > C[i - 1]:
                ortalama, oms = guncelle(ortalama, oms, C[i], alfa)
                son = i
                i += 1
            while i < n and C[i] > C[bas]:
                if asti(i):
                    i -= 1
                    son = i
                    break
                ortalama, oms = guncelle(ortalama, oms, C[i], alfa)
                son = i
                i += 1
            pencereler.append((bas, son))
        else:
            ortalama, oms = guncelle(ortalama, oms, C[i], alfa)
        i += 1
    return pencereler
