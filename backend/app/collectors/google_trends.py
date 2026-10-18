"""Google Trends — pytrends (isteğe bağlı) veya CSV içe aktarma. pytrends resmî
değil ve arşivlendi; Google'ın resmî Trends API'si alfa aşamasında.
Başarısızlıkta G4 eksik sayılır [PYTRENDS_DOC; GTRENDS_API_DOC] (Rapor Bölüm 6).

CSV: Tasarım kararı 28 ('<1' değeri 0 okunur; CSV saatleri kullanıcının
belirttiği UTC farkıyla UTC'ye çevrilir, varsayılan +3 Türkiye)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from app.collectors.base import KaynakDurumu

BELGE = ["PYTRENDS_DOC", "GTRENDS_API_DOC"]


def pytrends_topla(terim: str, etkin: bool) -> tuple[dict[datetime, float], KaynakDurumu]:
    """Saatlik çözünürlük yalnız son 7 gün için mevcuttur; daha eski saatler ilk taramalarda biriken kayıtlardan gelir."""
    if not etkin:
        return {}, KaynakDurumu("google_trends", "atlandi", mesaj="Google Trends kapalı; CSV içe aktarılabilir", belge=BELGE)
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl="tr-TR", tz=0)
        py.build_payload([terim], timeframe="now 7-d", geo="TR")
        df = py.interest_over_time()
        if df is None or df.empty:
            return {}, KaynakDurumu("google_trends", "hata", mesaj="boş yanıt", belge=BELGE)
        saatlik: dict[datetime, list[float]] = {}
        for zaman, satir in df.iterrows():
            z = zaman.to_pydatetime().replace(tzinfo=None, minute=0, second=0, microsecond=0)
            saatlik.setdefault(z, []).append(float(satir[terim]))
        sonuc = {z: sum(v) / len(v) for z, v in saatlik.items()}
        return sonuc, KaynakDurumu("google_trends", "tamam", adet=len(sonuc), belge=BELGE,
                                   ulasilan_bas=min(sonuc), ulasilan_bit=max(sonuc),
                                   mesaj="Saatlik veri yalnız son 7 gün; değerler her çekimde 0–100 göreli ölçeklenir")
    except Exception as e:
        return {}, KaynakDurumu("google_trends", "hata", mesaj=str(e)[:300], belge=BELGE)


def _zaman(s: str) -> datetime | None:
    for bicim in ("%Y-%m-%dT%H", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), bicim)
        except ValueError:
            continue
    return None


def csv_ayristir(metin: str, utc_farki_saat: float = 3.0) -> dict[datetime, float]:
    """Google Trends 'multiTimeline.csv' dışa aktarımı: başlık satırlarından sonra
    'Zaman,<terim>' satırları. Saatlik olmayan (günlük) satırlar reddedilir."""
    sonuc: dict[datetime, float] = {}
    for satir in csv.reader(io.StringIO(metin.lstrip("\ufeff"))):
        if len(satir) < 2:
            continue
        z = _zaman(satir[0])
        if z is None:
            continue
        d = satir[1].strip()
        deger = 0.0 if d.startswith("<") else float(d.replace(",", "."))
        z = (z - timedelta(hours=utc_farki_saat)).replace(minute=0, second=0, microsecond=0)
        sonuc[z] = deger
    return sonuc
