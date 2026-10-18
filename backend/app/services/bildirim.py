"""
E-posta / Slack bildirimi (Tasarım kararı 38: iletim tercihi, tespit kuralı değildir).

Kriz eşiği (kuruma özgü YÜKSEK RİSK eşiği) aşıldığında kurumun kayıt e-postasına (ve varsa ek alıcılara) uyarı
gönderilir. E-postadaki "Gerçek kriz" / "Önemsiz" bağlantıları imzalı, süreli bir belirteç taşır ve panelde bir onay
sayfası açar (e-posta tarayıcılarının bağlantıyı otomatik açıp etiketi yanlışlıkla kaydetmesini önlemek için
etiket yalnız onay düğmesiyle kaydedilir).
"""
from __future__ import annotations

import html
import logging
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Optional, Sequence
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import token_olustur
from app.literatur import RISK_SEVIYE_ETIKETLERI, gosterge
from app.models.orm import Alarm, BildirimKuyrugu, DenetimKaydi, Kullanici

log = logging.getLogger(__name__)
_TR = timezone(timedelta(hours=3))          # Türkiye kalıcı UTC+3
_EPOSTA = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def yerel(t: datetime) -> str:
    return t.replace(tzinfo=timezone.utc).astimezone(_TR).strftime("%d.%m.%Y %H:%M")


def eposta_alicilari(k: Kullanici) -> list[str]:
    """Kayıt e-postası + geçerli ek alıcılar (yinelenenler atılır)."""
    liste = [k.email] + [e.strip().lower() for e in (k.bildirim_ek_epostalar or []) if isinstance(e, str)]
    return list(dict.fromkeys(e for e in liste if _EPOSTA.match(e)))


def geri_bildirim_baglantisi(k: Kullanici, alarm: Alarm, karar: str) -> str:
    token = token_olustur({"amac": "geri_bildirim", "alarm": alarm.id, "kurum": k.id},
                          sure=timedelta(days=settings.GERI_BILDIRIM_TOKEN_GUN))
    return f"{settings.PANEL_URL.rstrip('/')}/geri-bildirim?karar={karar}&token={quote(token)}"


def smtp_yapilandirildi() -> bool:
    return bool(settings.SMTP_HOST and (settings.SMTP_FROM or settings.SMTP_USER))


class KalıcıHata(Exception):
    """Yeniden denemenin anlamsız olduğu SMTP hatası (alıcı reddedildi vb.)."""


def smtp_gonder(alici: str, konu: str, metin: str, html_govde: Optional[str] = None) -> None:
    """Tek alıcıya tek mesaj. Hata durumunda istisna fırlatır; kuyruk katmanı sınıflandırır."""
    m = EmailMessage()
    m["Subject"] = konu
    m["From"] = settings.SMTP_FROM or settings.SMTP_USER
    m["To"] = alici
    m["Date"] = formatdate(localtime=False)
    m["Message-ID"] = make_msgid(domain=(settings.SMTP_FROM or settings.SMTP_USER).split("@")[-1] or None)
    m.set_content(metin)
    if html_govde:
        m.add_alternative(html_govde, subtype="html")
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
                if settings.SMTP_USER:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(m)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
                if settings.SMTP_STARTTLS:
                    s.starttls()
                if settings.SMTP_USER:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(m)
    except smtplib.SMTPRecipientsRefused as e:
        raise KalıcıHata(f"Alıcı reddedildi: {e}") from e
    except smtplib.SMTPResponseException as e:
        if 500 <= e.smtp_code < 600 and e.smtp_code not in (530, 535, 534):
            raise KalıcıHata(f"SMTP {e.smtp_code}: {e.smtp_error!r}") from e
        raise


def metinden_html(metin: str) -> str:
    """Düz metin gövdeyi aynı içerik ve bağlantılarla HTML'e çevirir."""
    govde = []
    for satir in metin.split("\n"):
        k = html.escape(satir)
        k = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', k)
        govde.append(k)
    return ('<div style="font-family:Arial,Helvetica,sans-serif;max-width:640px;margin:auto;color:#0f172a;line-height:1.5">'
            + "<br>".join(govde) + "</div>")


# ---------------------------------------------------------------------------
# Kalıcı kuyruk: her alıcıya ayrı mesaj, tekilleştirme, artan beklemeli yeniden deneme
# ---------------------------------------------------------------------------
def kuyruga_ekle(db: Session, *, kurum_id: Optional[int], tur: str, anahtar: str, alicilar: Sequence[str], konu: str,
                 metin: str, html_govde: Optional[str] = None, alarm_id: Optional[int] = None) -> int:
    """Her alıcı için bir kayıt; (anahtar, alıcı) zaten varsa atlanır. Eklenen kayıt sayısını döndürür."""
    eklenen = 0
    for a in dict.fromkeys(alicilar):
        if db.query(BildirimKuyrugu.id).filter_by(anahtar=anahtar, alici=a).first():
            continue
        db.add(BildirimKuyrugu(kurum_id=kurum_id, alarm_id=alarm_id, tur=tur, anahtar=anahtar, alici=a, konu=konu[:300],
                               metin=metin, html=html_govde or metinden_html(metin)))
        eklenen += 1
    db.flush()
    return eklenen


def _bekleme(deneme: int) -> timedelta:
    return timedelta(minutes=min(2 ** deneme * 2, 240))


def kuyrugu_isle(db: Session, simdi: Optional[datetime] = None, limit: int = 50) -> dict:
    """Vadesi gelen bildirimleri gönderir. SMTP kabulü 'smtp_kabul' olarak kaydedilir (gelen kutusu teslimi değildir)."""
    simdi = simdi or datetime.now(timezone.utc).replace(tzinfo=None)
    ozet = {"gonderilen": 0, "tekrar": 0, "kalici_hata": 0, "bekleyen_smtp_yok": 0}
    for b in db.query(BildirimKuyrugu).filter(BildirimKuyrugu.durum == "gonderiliyor",
                                              BildirimKuyrugu.sonraki_deneme < simdi - timedelta(minutes=10)).all():
        b.durum = "tekrar_bekliyor"                      # işçi gönderim sırasında durmuş
    db.commit()
    if not smtp_yapilandirildi():
        ozet["bekleyen_smtp_yok"] = db.query(BildirimKuyrugu).filter(
            BildirimKuyrugu.durum.in_(("kuyrukta", "tekrar_bekliyor"))).count()
        return ozet
    vadeli = (db.query(BildirimKuyrugu).filter(BildirimKuyrugu.durum.in_(("kuyrukta", "tekrar_bekliyor")),
                                               BildirimKuyrugu.sonraki_deneme <= simdi)
              .order_by(BildirimKuyrugu.tur != "kriz", BildirimKuyrugu.sonraki_deneme).limit(limit).all())
    for b in vadeli:
        b.durum, b.deneme, b.sonraki_deneme = "gonderiliyor", (b.deneme or 0) + 1, simdi
        db.commit()
        try:
            smtp_gonder(b.alici, b.konu, b.metin, b.html)
            b.durum, b.gonderim, b.son_hata = "smtp_kabul", simdi, ""
            ozet["gonderilen"] += 1
        except KalıcıHata as e:
            b.durum, b.son_hata = "kalici_hata", str(e)[:500]
            ozet["kalici_hata"] += 1
        except Exception as e:                           # ağ, zaman aşımı, kimlik doğrulama
            b.son_hata = f"{type(e).__name__}: {str(e)[:400]}"
            if b.deneme >= settings.BILDIRIM_EN_FAZLA_DENEME:
                b.durum = "kalici_hata"
                ozet["kalici_hata"] += 1
            else:
                b.durum, b.sonraki_deneme = "tekrar_bekliyor", simdi + _bekleme(b.deneme)
                ozet["tekrar"] += 1
        if b.durum == "kalici_hata":
            log.error("Bildirim kalıcı olarak gönderilemedi (id=%s, tür=%s): %s", b.id, b.tur, b.son_hata)
            db.add(DenetimKaydi(kurum_id=b.kurum_id, islem="bildirim_kalici_hata",
                                ayrinti={"bildirim": b.id, "tur": b.tur, "hata": b.son_hata}))
        db.commit()
    return ozet


def kuyruk_durumu(db: Session, kurum_id: Optional[int] = None) -> dict:
    from sqlalchemy import func
    q = db.query(BildirimKuyrugu.durum, func.count(BildirimKuyrugu.id))
    if kurum_id is not None:
        q = q.filter(BildirimKuyrugu.kurum_id == kurum_id)
    return dict(q.group_by(BildirimKuyrugu.durum).all())


def eposta_dogrula_baglantisi(k: Kullanici) -> str:
    token = token_olustur({"amac": "eposta_dogrula", "kurum": k.id, "email": k.email}, sure=timedelta(days=7))
    return f"{settings.PANEL_URL.rstrip('/')}/eposta-dogrula?token={quote(token)}"


def dogrulama_gonder(db: Session, k: Kullanici) -> int:
    metin = (f"Merhaba,\n\n{k.kurum} için Krizyolda hesabınızın e-posta adresini doğrulamak için bağlantıya tıklayın "
             f"(7 gün geçerlidir):\n{eposta_dogrula_baglantisi(k)}\n\nBu işlemi siz başlatmadıysanız bu e-postayı yok sayın.")
    return kuyruga_ekle(db, kurum_id=k.id, tur="dogrulama", anahtar=f"dogrulama:{k.id}:{k.email}:{int(datetime.now().timestamp() // 600)}",
                        alicilar=[k.email], konu="[Krizyolda] E-posta adresinizi doğrulayın", metin=metin)


def sifre_sifirlama_gonder(db: Session, k: Kullanici) -> int:
    token = token_olustur({"amac": "sifre_sifirla", "kurum": k.id, "h": k.hashed_password[-8:]}, sure=timedelta(hours=1))
    link = f"{settings.PANEL_URL.rstrip('/')}/sifre-sifirla?token={quote(token)}"
    metin = (f"Merhaba,\n\nŞifrenizi sıfırlamak için bağlantıya tıklayın (1 saat geçerlidir, bir kez kullanılabilir):\n{link}\n\n"
             "Bu işlemi siz başlatmadıysanız bu e-postayı yok sayın; şifreniz değişmez.")
    return kuyruga_ekle(db, kurum_id=k.id, tur="sifre", anahtar=f"sifre:{k.id}:{int(datetime.now().timestamp() // 300)}",
                        alicilar=[k.email], konu="[Krizyolda] Şifre sıfırlama", metin=metin)


# ---------------------------------------------------------------------------
# Alarm e-postası
# ---------------------------------------------------------------------------
def _katkilar(sonuc: dict, n: int = 3) -> list[tuple[str, float]]:
    kat = (sonuc.get("son") or {}).get("katkilar") or {}
    liste = sorted(((k, v) for k, v in kat.items() if v is not None), key=lambda kv: -kv[1])
    return [(f"{k} — {gosterge(k)['ad']}", v) for k, v in liste[:n] if v > 0]


def _ornekler(alarm: Alarm, icerikler: Sequence, n: int = 3) -> list[str]:
    aralik = [i for i in icerikler if alarm.baslangic <= i.tarih < (alarm.bitis or datetime.utcnow())]
    secili = [i for i in aralik if i.duygu_etiketi == "olumsuz" or i.scct_seviye > 0] or aralik
    secili.sort(key=lambda i: -(i.begeni + i.yorum + i.paylasim))
    return [f"[{i.platform}] {(i.metin or '').strip().replace(chr(10), ' ')[:180]}" for i in secili[:n]]


def alarm_eposta_govdesi(k: Kullanici, alarm: Alarm, sonuc: dict, icerikler: Sequence, *, guncelleme: bool,
                         benzer_gercek: Sequence[tuple[Alarm, float]] = (), zirve: Optional[dict] = None) -> tuple[str, str, str]:
    from app.pr.strateji import kriz_stratejisi
    risk = zirve or (sonuc.get("son") or {}).get("risk") or {}      # alarmın en yüksek puanlı ölçümü
    etiket = RISK_SEVIYE_ETIKETLERI[alarm.max_seviye]
    konu = (f"[Krizyolda] KRİZ UYARISI — {k.kurum}: {etiket}" + (" (seviye yükseldi)" if guncelleme else ""))
    esikler = risk.get("esikler") or {}
    tip = (alarm.parmak_izi or {}).get("tip")
    itibar_olumsuz = ((sonuc.get("onceki_itibar") or {}).get("deger") == "olumsuz")
    st = kriz_stratejisi(efektif_kume=alarm.baskin_kume, tip=tip, kriz_gecmisi=k.kriz_gecmisi or [],
                         onceki_itibar_olumsuz=itibar_olumsuz)
    gercek_link = geri_bildirim_baglantisi(k, alarm, "gercek_kriz")
    onemsiz_link = geri_bildirim_baglantisi(k, alarm, "onemsiz")
    panel = f"{settings.PANEL_URL.rstrip('/')}/pr"
    satirlar = [
        f"{k.kurum} için kuruma özgü kriz eşiği {'yükseldi' if guncelleme else 'aşıldı'}.",
        "",
        f"Seviye: {etiket}",
        f"Alarm başlangıcı: {yerel(alarm.baslangic)} (Türkiye saati)",
        f"En yüksek risk puanı: {alarm.max_risk:.1f}/100" if alarm.max_risk is not None else "",
        (f"Kurumunuz için Yüksek eşik: {esikler['yuksek']:.1f}, Kritik eşik: {esikler['kritik']:.1f}"
         if esikler.get("yuksek") is not None else ""),
        (f"Bu puan kurumun normal döneminde {risk['donus_metni']} görülür." if risk.get("donus_metni") else ""),
    ]
    kat = _katkilar(sonuc)
    if kat:
        satirlar += ["", "Sinyale en çok katkı yapan göstergeler:"] + [f"  • {ad} (katkı {v:.2f})" for ad, v in kat]
    if st["durum"] == "tamam":
        satirlar += ["", f"SCCT (Coombs 2007): {st['kume_adi']} kümesi, {st['tehdit']} itibar tehdidi"
                         + (f", baskın tip: {st['tip_adi']}" if st.get("tip_adi") else ""),
                     f"Önerilen yanıt duruşu: {st['durus']}"]
    ornek = _ornekler(alarm, icerikler)
    if ornek:
        satirlar += ["", "Örnek içerikler:"] + [f"  • {o}" for o in ornek]
    if benzer_gercek:
        b = benzer_gercek[0][0]
        satirlar += ["", f"Not: Bu alarm, daha önce 'gerçek kriz' işaretlediğiniz {yerel(b.baslangic)} tarihli alarmla benzer."]
    satirlar += ["", "Bu bir gerçek kriz mi?",
                 f"  Gerçek kriz: {gercek_link}", f"  Önemsiz: {onemsiz_link}",
                 "'Önemsiz' işaretlerseniz sistem bu kriz için bir daha e-posta göndermez ve eşiği bu geri bildirimle yeniden ayarlar.",
                 f"Kriz stratejisi ve PR danışmanlığı: {panel}"]
    metin = "\n".join(s for s in satirlar if s is not None)

    def e(x: str) -> str:
        return html.escape(x)
    liste = "".join(f"<li>{e(ad)} (katkı {v:.2f})</li>" for ad, v in kat)
    ornek_html = "".join(f"<li>{e(o)}</li>" for o in ornek)
    h = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:620px;margin:auto;color:#0f172a">
<h2 style="margin:0 0 4px">{e(k.kurum)}: kriz eşiği {'yükseldi' if guncelleme else 'aşıldı'}</h2>
<p style="display:inline-block;background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;border-radius:999px;padding:3px 12px;font-weight:bold">{e(etiket)}</p>
<p>Alarm başlangıcı: <b>{e(yerel(alarm.baslangic))}</b> (Türkiye saati)<br>
{f'En yüksek risk puanı: <b>{alarm.max_risk:.1f}/100</b><br>' if alarm.max_risk is not None else ''}
{f'Kurumunuz için Yüksek eşik <b>{esikler["yuksek"]:.1f}</b>, Kritik eşik <b>{esikler["kritik"]:.1f}</b>.<br>' if esikler.get('yuksek') is not None else ''}
{f'Bu puan kurumun normal döneminde {e(risk["donus_metni"])} görülür.' if risk.get('donus_metni') else ''}</p>
{f'<p><b>Sinyale en çok katkı yapan göstergeler</b></p><ul>{liste}</ul>' if kat else ''}
{f'<p><b>SCCT (Coombs 2007):</b> {e(st["kume_adi"])} kümesi, {e(st["tehdit"])} itibar tehdidi. <b>Önerilen duruş:</b> {e(st["durus"])}</p>' if st['durum']=='tamam' else ''}
{f'<p><b>Örnek içerikler</b></p><ul>{ornek_html}</ul>' if ornek else ''}
<p><b>Bu bir gerçek kriz mi?</b></p>
<p><a href="{e(gercek_link)}" style="background:#b91c1c;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;margin-right:8px">Gerçek kriz</a>
<a href="{e(onemsiz_link)}" style="background:#e2e8f0;color:#0f172a;padding:10px 16px;border-radius:8px;text-decoration:none">Önemsiz</a></p>
<p style="font-size:12px;color:#475569">'Önemsiz' işaretlerseniz sistem bu kriz için bir daha e-posta göndermez ve eşiği bu geri bildirimle yeniden ayarlar.</p>
<p><a href="{e(panel)}">Kriz stratejisi ve PR danışmanlığı →</a></p></div>"""
    return konu, metin, h


def mesaj_olustur(kurum: str, alarm: Alarm) -> str:
    return (f"[Krizyolda] {kurum}: {RISK_SEVIYE_ETIKETLERI[alarm.max_seviye]} — kriz eşiği aşıldı "
            f"(başlangıç {yerel(alarm.baslangic)}; R = {alarm.max_risk if alarm.max_risk is None else round(alarm.max_risk, 1)}; "
            f"SCCT tehdidi: {alarm.tehdit or 'belirsiz'}).")


def alarm_bildir(db: Session, k: Kullanici, alarm: Alarm, sonuc: dict, icerikler: Sequence, *, guncelleme: bool,
                 benzer_gercek: Sequence[tuple[Alarm, float]] = ()) -> list[str]:
    """E-postayı kalıcı kuyruğa yazar (gönderimi işçi yapar). Dönüş: kuyruğa alınan kanallar."""
    kanallar: list[str] = []
    if k.bildirim_email:
        from app.models.orm import RiskOlcumu
        from app.services.kurum_esik_servisi import olcum_ozeti
        z = db.query(RiskOlcumu).filter(RiskOlcumu.alarm_id == alarm.id).order_by(RiskOlcumu.risk.desc()).first()
        konu, metin, h = alarm_eposta_govdesi(k, alarm, sonuc, icerikler, guncelleme=guncelleme, benzer_gercek=benzer_gercek,
                                              zirve=olcum_ozeti(z) if z else None)
        n = kuyruga_ekle(db, kurum_id=k.id, tur="kriz_guncelleme" if guncelleme else "kriz",
                         anahtar=f"kriz:{alarm.id}:{alarm.max_seviye}", alicilar=eposta_alicilari(k),
                         konu=konu, metin=metin, html_govde=h, alarm_id=alarm.id)
        if n:
            kanallar.append("email")
    if k.bildirim_slack and settings.SLACK_WEBHOOK_URL:
        try:
            httpx.post(settings.SLACK_WEBHOOK_URL, json={"text": mesaj_olustur(k.kurum, alarm)}, timeout=15).raise_for_status()
            kanallar.append("slack")
        except Exception as ex:
            log.warning("Slack bildirimi gönderilemedi: %s", ex)
    return kanallar


def haftalik_kuyruga_ekle(db: Session, k: Kullanici, konu: str, metin: str, donem_anahtari: str) -> int:
    """Haftalık brif; dönem anahtarı aynı dönemin ikinci kez gönderilmesini engeller."""
    return kuyruga_ekle(db, kurum_id=k.id, tur="haftalik", anahtar=f"haftalik:{k.id}:{donem_anahtari}",
                        alicilar=eposta_alicilari(k), konu=konu, metin=metin)
