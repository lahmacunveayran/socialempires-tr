"""İmparatorluğu ev ağı (Wi-Fi) üzerinden bir cihazdan ötekine taşıma (/tasima): bilgisayar <-> tablet.

Gönderen cihaz "Bu cihazdan gönder" ile 10 dakikalığına ayrı, küçük bir sunucu açar (PORT); bu sunucu
yalnızca imparatorluk listesini ve yedek zarfını (kayit_yedek.zarf) verir, o da yalnızca ekranda görünen
6 haneli kodla. Oyunun asıl sunucusu ev ağına açılmaz. Alan cihaz adresi ve kodu girer, imparatorluğu seçer;
kayıt yedek yüklemedeki denetimlerden geçer (özet, şema, kimlik), eski hâli .bak olarak saklanır.
Tek kişilik kullanım içindir: aynı kişinin kendi cihazları arasında kayıt taşınır.
"""

import hmac
import ipaddress
import json
import secrets
import threading
import time
import urllib.error
import urllib.request

from flask import Flask, render_template, request, session

from oyun import kayit_yedek
from oyun.hile import _hile_izinli as yerel_mi
from oyun.kayit import all_saves_userid, save_info, session as kayit_oturumu
from oyun import sunucu
from oyun.sunucu import app
from oyun.surum import version_name

PORT = 5051
SURE = 10 * 60
EN_COK_YANLIS = 10
ZAMAN_ASIMI = 15

_kilit = threading.Lock()
_gonderim = {"sunucu": None, "kod": None, "bitis": 0, "yanlis": 0, "gonderilen": 0}


def _oyuncu_kayitlari():
    """Botlar dışındaki imparatorluklar."""
    return [save_info(uid) for uid in all_saves_userid()
            if not (kayit_oturumu(uid) or {}).get("playerInfo", {}).get("bot")]


# --- Gönderen cihaz: yalnızca iki uç sunan ayrı sunucu ---
gonderici = Flask("tasima")


def _kod_dogru():
    kod = request.args.get("kod", "")
    beklenen = _gonderim["kod"]
    if beklenen and time.time() < _gonderim["bitis"] and hmac.compare_digest(kod, beklenen):
        return True
    _gonderim["yanlis"] += 1
    if _gonderim["yanlis"] >= EN_COK_YANLIS:  # kod tahmin edilmeye çalışılıyorsa kapat
        threading.Thread(target=gonderimi_durdur, daemon=True).start()
    return False


@gonderici.route("/liste")
def gonderici_liste():
    if not _kod_dogru():
        return {"hata": "kod"}, 403
    return {"imparatorluklar": _oyuncu_kayitlari()}


@gonderici.route("/kayit/<uid>")
def gonderici_kayit(uid):
    if not _kod_dogru():
        return {"hata": "kod"}, 403
    if uid not in {k["userid"] for k in _oyuncu_kayitlari()}:
        return {"hata": "yok"}, 404
    _gonderim["gonderilen"] += 1
    return app.response_class(json.dumps(kayit_yedek.zarf(uid), ensure_ascii=False), mimetype="application/json")


def gonderimi_baslat():
    from waitress.server import create_server
    with _kilit:
        if _gonderim["sunucu"] is None:
            sunucu = create_server(gonderici, host="0.0.0.0", port=PORT, threads=2)
            threading.Thread(target=sunucu.run, name="tasima-gonderici", daemon=True).start()
            _gonderim["sunucu"] = sunucu
        _gonderim.update(kod=f"{secrets.randbelow(10**6):06d}", bitis=time.time() + SURE, yanlis=0, gonderilen=0)
        zamanlayici = threading.Timer(SURE, _suresi_doldu, args=(_gonderim["bitis"],))
        zamanlayici.daemon = True
        zamanlayici.start()
    return gonderim_durumu()


def _suresi_doldu(bitis):
    if _gonderim["bitis"] == bitis:  # bu arada yeniden başlatılmadıysa
        gonderimi_durdur()


def gonderimi_durdur():
    with _kilit:
        sunucu = _gonderim["sunucu"]
        _gonderim.update(sunucu=None, kod=None, bitis=0)
    if sunucu is not None:
        sunucu.close()


def gonderim_durumu():
    acik = _gonderim["sunucu"] is not None
    return {"acik": acik, "adres": sunucu.yerel_ag_adresi() if acik else None, "kod": _gonderim["kod"],
            "kalan": max(0, int(_gonderim["bitis"] - time.time())) if acik else 0,
            "gonderilen": _gonderim["gonderilen"]}


# --- Alan cihaz ---
class TasimaHatasi(ValueError):
    pass


def _ev_agi_adresi(adres):
    """Yalnızca ev ağı (özel IPv4) adresleri: 192.168.x.x, 10.x.x.x, 172.16-31.x.x."""
    try:
        ip = ipaddress.IPv4Address((adres or "").strip())
    except ValueError:
        raise TasimaHatasi("adres")
    if not ip.is_private or ip.is_loopback or ip.is_link_local:
        raise TasimaHatasi("adres")
    return str(ip)


def _getir(adres, yol, kod):
    url = f"http://{_ev_agi_adresi(adres)}:{PORT}{yol}?kod={urllib.request.quote(kod or '')}"
    try:
        with urllib.request.urlopen(url, timeout=ZAMAN_ASIMI) as yanit:
            return yanit.read(kayit_yedek.EN_BUYUK + 1)
    except urllib.error.HTTPError as hata:
        raise TasimaHatasi("kod" if hata.code == 403 else "yok")
    except (urllib.error.URLError, OSError):
        raise TasimaHatasi("ulasilamadi")


HATALAR = {
    "adres": "Adres, gönderen cihazın ekranındaki 192.168.x.x biçiminde olmalı.",
    "kod": "Kod yanlış ya da süresi dolmuş. Gönderen cihazda yeniden başlatın.",
    "yok": "Bu imparatorluk gönderen cihazda bulunamadı.",
    "ulasilamadi": "Gönderen cihaza ulaşılamadı. İki cihaz da aynı Wi-Fi'da mı, gönderme açık mı?",
}


@app.route("/tasima")
def tasima_sayfasi():
    return render_template("tasima.html", yerel=yerel_mi(), version=version_name)


@app.route("/tasima/gonder", methods=["GET", "POST"])
def tasima_gonder():
    if not yerel_mi():
        return {"hata": "yerel"}, 403
    if request.method == "POST":
        try:
            return gonderimi_baslat()
        except OSError:  # port kullanımda
            return {"hata": "Gönderme açılamadı: 5051 numaralı kapı kullanımda."}, 409
    return gonderim_durumu()


@app.route("/tasima/gonder/durdur", methods=["POST"])
def tasima_gonder_durdur():
    if not yerel_mi():
        return {"hata": "yerel"}, 403
    gonderimi_durdur()
    return gonderim_durumu()


@app.route("/tasima/liste", methods=["POST"])
def tasima_liste():
    if not yerel_mi():
        return {"hata": "yerel"}, 403
    try:
        uzak = json.loads(_getir(request.form.get("adres"), "/liste", request.form.get("kod")))["imparatorluklar"]
    except TasimaHatasi as hata:
        return {"hata": HATALAR[str(hata)]}, 400
    except (ValueError, KeyError, TypeError):
        return {"hata": HATALAR["ulasilamadi"]}, 400
    yerel = {k["userid"]: k for k in _oyuncu_kayitlari()}
    for k in uzak:
        k["burada"] = yerel.get(k.get("userid"))  # aynı imparatorluk bu cihazda varsa üzerine yazılır
    return {"imparatorluklar": uzak}


@app.route("/tasima/al", methods=["POST"])
def tasima_al():
    if not yerel_mi():
        return {"hata": "yerel"}, 403
    uid = request.form.get("uid", "")
    try:
        veri = _getir(request.form.get("adres"), f"/kayit/{urllib.request.quote(uid)}", request.form.get("kod"))
        # Bilerek seçilen imparatorluk alınır: bu cihazdaki aynı kimlikli kaydın üzerine yazılabilir (.bak kalır)
        kimlik, ham = kayit_yedek.zarfi_ac(veri, uid)
    except TasimaHatasi as hata:
        return {"hata": HATALAR[str(hata)]}, 400
    except kayit_yedek.YedekHatasi as hata:
        return {"hata": kayit_yedek.HATALAR.get(hata.kod, kayit_yedek.HATALAR["bicim"])}, 400
    if kimlik != uid:
        return {"hata": kayit_yedek.HATALAR["kimlik"]}, 400
    kayit_yedek.geri_yukle(kimlik, ham)
    session["USERID"] = kimlik
    session.setdefault("GAMEVERSION", "SocialEmpires0926bsec.swf")
    return {"durum": "ok", "imparatorluk": save_info(kimlik)}
