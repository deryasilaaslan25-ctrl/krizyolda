"""
Olumsuz davranış niyeti (G12): boykot / satın almama / başkalarını uyarma
[COOMBS_HOLLADAY2007; COOMBS2007; KLEIN2004].

İfadeler bu kavramların Türkçe operasyonelleştirmesidir; literatürde
yayımlanmış bir Türkçe sözlük değildir (Tasarım kararı 2). Eşleşme SCCT
tohumlarıyla aynı kuralla yapılır (sözcük başında başlar, son sözcük önek).
"""
from __future__ import annotations

from app.nlp.normalize import duz_metin, sozcukler

NIYET_IFADELERI: dict[str, list[str]] = {
    # Klein vd. (2004): boykota katılım
    "boykot": ["boykot"],
    # Coombs & Holladay (2007): satın alma niyetinin düşmesi
    "satin_almama": ["bir daha almam", "bir daha almayacağ", "asla almam", "almayın", "satın almayın",
                     "almayacağım", "kullanmayacağım", "kullanmayın", "tercih etmeyin", "bir daha gitmem",
                     "gitmeyin", "aboneliğimi iptal", "üyeliğimi iptal"],
    # Coombs & Holladay (2007): olumsuz ağızdan ağıza iletişim (başkalarını uyarma)
    "baskalarini_uyarma": ["herkesi uyarıyorum", "sakın almayın", "dikkatli olun", "uzak durun",
                           "paylaşın herkes duysun", "herkes duysun", "yaymayı unutmayın", "sizi uyarıyorum"],
}


def _eslesir(duz: str, ifade: str) -> bool:
    return (" " + " ".join(sozcukler(ifade))) in duz


def niyet_tespit(metin: str) -> list[str]:
    duz = duz_metin(metin)
    return [tur for tur, ifadeler in NIYET_IFADELERI.items() if any(_eslesir(duz, i) for i in ifadeler)]
