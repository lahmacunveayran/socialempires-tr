"""Oyun varlıkları (SWF, görsel, müzik) ve Türkçeleştirilmiş oyun SWF'si.

Varlıklar depoda tutulmaz (~1,3 GB). Yerelde olmayan bir dosya istendiğinde
orijinal koruma projesinden indirilip download_assets/ altında saklanır.
Tamamını önceden indirmek için: python varliklari_indir.py
"""

import http.client
import os
import re
import shutil
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request

from flask import request, send_file, send_from_directory
from werkzeug.utils import safe_join

from oyun import fx_yama, ruffle as Ruffle
from oyun import swf_yama
from oyun.sunucu import OYUN_DILI, app
from oyun.yollar import ASSETS_DIR, INDIRILEN_DIR

STATIK = "/default01.static.socialpointgames.com/static/socialempires"
INDIRILEN_VARLIKLAR = os.path.join(INDIRILEN_DIR, "assets")
VARLIK_KAYNAKLARI = (
    "https://raw.githubusercontent.com/AcidCaos/socialemperors/main/assets/{path}",
    "https://static.socialpointgames.com/static/socialempires/assets/{path}",
)
# İstemcinin istediği ama arşivde başka adla bulunan dosyalar
ESDEGERLER = {
    "swf/05122012_projectiles.swf": "swf/20130417_projectiles.swf",
    "swf/05122012_magicParticles.swf": "swf/20131010_magicParticles.swf",
    "swf/05122012_dynamic.swf": "swf/120608_dynamic.swf",
}


def _gecerli_dosya(yol):
    """İndirilen dosya boş ya da bir HTML hata sayfası olmasın."""
    try:
        if os.path.getsize(yol) < 64:
            return False
        with open(yol, "rb") as f:
            return not f.read(4).startswith(b"<")
    except OSError:
        return False


def _indir(path, hedef):
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    for kalip in VARLIK_KAYNAKLARI:
        url = kalip.format(path=urllib.parse.quote(path))
        fd, gecici = tempfile.mkstemp(dir=os.path.dirname(hedef), prefix="indir-", suffix=".tmp")
        os.close(fd)
        try:
            with urllib.request.urlopen(url, timeout=30) as yanit, open(gecici, "wb") as f:
                shutil.copyfileobj(yanit, f)
            if not _gecerli_dosya(gecici):
                raise OSError("indirilen dosya gecersiz")
            os.replace(gecici, hedef)  # atomik: yarım dosya sunulmaz
            print(f" [+] Varlik indirildi: {url}")
            return True
        except (urllib.error.URLError, http.client.HTTPException, OSError) as hata:
            print(f" ! Varlik indirilemedi: {url} ({hata})")
            if os.path.exists(gecici):
                os.remove(gecici)
    return False


def _turet(path):
    """Arşivde olmayan efekti oyunun benzer efektinden türetip önbelleğe yazar."""
    hedef = safe_join(os.path.join(INDIRILEN_DIR, "turetilen"), path)
    if hedef and os.path.isfile(hedef):
        return hedef
    kaynak = varlik_yolu(fx_yama.TURETILEN[path])
    if kaynak is None or not hedef:
        return None
    with open(kaynak, "rb") as f:
        veri = fx_yama.sinifi_yeniden_adlandir(f.read(), fx_yama.sinif_adi(fx_yama.TURETILEN[path]),
                                              fx_yama.sinif_adi(path))
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=os.path.dirname(hedef), suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(veri)
    os.replace(gecici, hedef)
    print(f" [+] Eksik efekt turetildi: {path}")
    return hedef


def varlik_yolu(path):
    """Varlığın diskteki yolunu döndürür; gerekirse indirir. Yoksa None."""
    path = ESDEGERLER.get(path, path)
    if path in fx_yama.TURETILEN:
        try:
            return _turet(path)
        except (OSError, ValueError, IndexError):
            traceback.print_exc()
            return None
    # Boşluk gerekli: ör. "swf/music/Spirit of Eternity.mp3"
    if not re.fullmatch(r"[A-Za-z0-9_./\- ]+", path) or ".." in path.split("/"):
        return None
    yerel = safe_join(ASSETS_DIR, path)
    if yerel and os.path.isfile(yerel):
        return yerel
    indirilen = safe_join(INDIRILEN_VARLIKLAR, path)
    if not indirilen:
        return None
    if os.path.isfile(indirilen):
        if _gecerli_dosya(indirilen):
            return indirilen
        try:
            os.remove(indirilen)  # yarım/bozuk indirme: yeniden dene
        except OSError:
            pass
    return indirilen if _indir(path, indirilen) else None


@app.route(STATIK + "/<path:path>")
def statik_varlik(path):
    yol = varlik_yolu(str(path).replace("\\", "/"))
    if yol is None:
        return ("", 404)
    return send_from_directory(os.path.dirname(yol), os.path.basename(yol))


def _oyun_swf_mi(dosya):
    """SocialEmpires<sürüm>.swf biçiminde mi? (Düzenli ifade yok: uzun ve
    kötü niyetli adlarda yavaşlamasın.)"""
    surum = dosya[len("SocialEmpires"):-len(".swf")]
    return (dosya.startswith("SocialEmpires") and dosya.endswith(".swf")
            and surum.isascii() and surum.isalnum())


@app.route(STATIK + "/flash/<dosya>")
def oyun_swf(dosya):
    """Oyun SWF'sini sabit arayüz yazıları Türkçeleştirilmiş olarak sunar."""
    kaynak = varlik_yolu(f"flash/{dosya}")
    if kaynak is None:
        return ("", 404)
    if OYUN_DILI == "tr" and _oyun_swf_mi(dosya):
        try:
            kaynak = swf_yama.onbellekli_turkcelestir(kaynak, os.path.join(INDIRILEN_DIR, "tr"))
        except Exception:
            traceback.print_exc()
            print(" ! SWF Turkcelestirilemedi; orijinali sunuluyor")
    return send_file(kaynak, mimetype="application/x-shockwave-flash")


@app.route("/ruffle/<surum>/<dosya>")
def ruffle_dosyasi(surum, dosya):
    """Sabitlenmiş Ruffle sürümü; önceden sıkıştırılmış hâli varsa o gönderilir."""
    if surum != Ruffle.SURUM or not Ruffle.hazirla():
        return ("", 404)
    bulunan = Ruffle.dosya(dosya, request.headers.get("Accept-Encoding", ""))
    if bulunan is None:
        return ("", 404)
    yol, tur, kodlama = bulunan
    yanit = send_file(yol, mimetype=tur, max_age=31536000)
    yanit.vary.add("Accept-Encoding")
    if kodlama:
        yanit.headers["Content-Encoding"] = kodlama
    return yanit
