"""docs/KAYNAKCA.md, docs/GOSTERGELER.md ve docs/TASARIM_KARARLARI.md dosyalarını
app/literatur.py kataloğundan üretir; böylece belge ile kod birbirinden ayrışamaz.
Kullanım (backend klasöründen):  python -m scripts.belge_uret"""
from pathlib import Path

from app import literatur as L

DOCS = Path(__file__).resolve().parents[2] / "docs"


def main() -> None:
    j = L.katalog_json()
    DOCS.mkdir(exist_ok=True)
    s = ["# Kaynakça", "", "app/literatur.py kataloğundan otomatik üretilmiştir. \"v5 ek\" işaretli kaynaklar ERKİS v4 raporunda",
         "bulunmayıp v5'te kuruma özgü eşik katmanı için eklenenlerdir.", ""]
    for k in j["kaynaklar"]:
        s.append(f"- **{k['kimlik']}** — {k['atif']} {k['url']}{' (v5 ek)' if k['ek'] else ''}")
    (DOCS / "KAYNAKCA.md").write_text("\n".join(s) + "\n", encoding="utf-8")

    g = ["# Göstergeler", "", "app/literatur.py kataloğundan otomatik üretilmiştir.", ""]
    adlar = {"SECILDI": "Seçilen göstergeler (KRE formülüne girer)", "KALITE": "Veri kalitesi (formül dışı)",
             "CERCEVE": "Çerçeve değişkenleri (formül dışı)", "ELENDI": "Elenen adaylar"}
    for grup, baslik in adlar.items():
        g += [f"## {baslik}", "", "| Kod | Gösterge | Boyut | w | Ölçüm | Gerekçe | Kaynak |", "|---|---|---|---|---|---|---|"]
        for x in j["gostergeler"]:
            if x["grup"] != grup:
                continue
            w = j["agirliklar"].get(x["kod"])
            hucre = lambda v: str(v or "—").replace("|", "\\|").replace("\n", " ")
            g.append(f"| {x['kod']} | {hucre(x['ad'])} | {j['boyut_adlari'].get(x['boyut'], 'formül dışı')} | "
                     f"{'%.4f' % w if w is not None else '—'} | {hucre(x['olcum'])} | {hucre(x['gerekce'])} | {', '.join(x['kaynaklar'])} |")
        g.append("")
    (DOCS / "GOSTERGELER.md").write_text("\n".join(g), encoding="utf-8")

    t = ["# Tasarım kararları", "", "Literatürden doğrudan gelmeyen her uygulama seçimi burada listelenir. Bunlara kaynak",
         "atfedilmemiştir. \"rapor\" kaynaklı olanlar ERKİS v4 raporunun Bölüm 7'sinde yer alan kararlardır; \"v5\" olanlar",
         "bu uygulamada eklenmiştir.", ""]
    for k in j["tasarim_kararlari"]:
        t.append(f"{k['no']}. **{k['baslik']}** ({'ERKİS v4 raporu' if k['kaynak'] == 'rapor' else 'v5 uygulaması'}) — {k['aciklama']}")
    t += ["", "## Sınırlılıklar", ""] + [f"- {x}" for x in j["sinirliliklar"]]
    (DOCS / "TASARIM_KARARLARI.md").write_text("\n".join(t) + "\n", encoding="utf-8")
    print("Belgeler üretildi:", DOCS)


if __name__ == "__main__":
    main()
