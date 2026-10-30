"""Flask uygulaması: giriş/oyun sayfaları, hata günlüğü ve açılış.

İstemcinin çağırdığı uçlar ayrı modüllerdedir:
- oyun.varliklar: SWF/görsel/müzik dosyaları
- oyun.istemci:   oyun sunucusu uçları (config, oyuncu bilgisi, komutlar,
                  ada, turnuva)
- oyun.hile:      yerel hile paneli
"""

import json
import os
import socket
import time
import traceback

print(" [+] Oyun ayarlari yukleniyor...")
from flask import Flask, redirect, render_template, request, send_from_directory, session

from oyun import aktarim, ayarlar, ruffle as Ruffle
from oyun.dunya import rutbe
from oyun.ekonomi import timestamp_now
from oyun.kayit import (all_saves_info, all_saves_userid, fb_friends_str, load_saved_villages,
                        new_village, save_info, save_lock, save_session, gecerli_uid,
                        session as kayit_oturumu)
from oyun.surum import version_code, version_name
from oyun.yollar import SAVES_DIR, STUB_DIR, TEMPLATES_DIR

print(" [+] Kayitlar yukleniyor...")
load_saved_villages()

HOST = "127.0.0.1"
PORT = 5050
# Ruffle aynı anda çok sayıda küçük dosya istediği için iş parçacığı sayısı önemli.
IS_PARCACIGI = 8
OYUN_DILI = "tr"
HATA_LOG = os.path.join(SAVES_DIR, "sunucu_hatalari.log")
BASLANGIC = time.time()

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("SE_SECRET_KEY", "SECRET_KEY")
# Statik varlıklar tarayıcıda/Flash'ta önbelleklensin (her açılışta yüzlerce
# dosya yeniden indirilmesin). Değiştirdiğiniz dosyalar için Ctrl+F5.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400
app.json.sort_keys = False
aktarim.kaydet(app)


def bot_mu(uid):
    return bool((kayit_oturumu(uid) or {}).get("playerInfo", {}).get("bot"))


def _botlari_hazirla():
    """Hiç bot köyü yoksa (ilk çalıştırma) PvP/ada/turnuva için üretir."""
    if any(bot_mu(uid) for uid in all_saves_userid()):
        _bot_adlarini_yenile()
        return
    print(" [+] Bot koyleri bulunamadi; ilk calistirma icin uretiliyor...")
    try:
        # Paket olarak alınır: Android'de araclar/ salt okunur oyun dosyalarının yanındadır, yazılabilir klasörde değil
        from araclar.bot_koy_uret import bot_uret
        bot_uret()
    except Exception:
        traceback.print_exc()
        print(" ! Bot koyleri uretilemedi; elle: python araclar/bot_koy_uret.py")
        return
    load_saved_villages()


def _bot_adlarini_yenile():
    """Eski tarihî adlı botları ve portrelerini oyunun birimlerine geçirir (oyun/bot_kimlik.py)."""
    from oyun.bot_kimlik import adlari_yenile
    with save_lock:
        degisen = adlari_yenile({uid: kayit_oturumu(uid) for uid in all_saves_userid()})
        for uid in degisen:
            save_session(uid)
    if degisen:
        print(f" [+] Bot adlari/portreleri guncellendi: {len(degisen)} kayit")


_botlari_hazirla()


@app.errorhandler(Exception)
def _hatayi_kaydet(hata):
    """Beklenmeyen hataları dosyaya yazar; sunucu ayakta kalır."""
    from werkzeug.exceptions import HTTPException
    if isinstance(hata, HTTPException):
        return hata
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        with open(HATA_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {timestamp_now()} {request.path} ===\n")
            traceback.print_exc(file=f)
    except OSError:
        pass
    print(" ! Sunucu hatasi (ayrinti saves/sunucu_hatalari.log):", hata)
    return ({"result": "error"}, 500)


# ---------------------------------------------------------------------------
# Sayfalar
# ---------------------------------------------------------------------------

@app.route("/saglik")
def saglik():
    return {
        "durum": "ok",
        "surum": version_code,
        "oyuncu": len(all_saves_userid()),
        "calisma_suresi": int(time.time() - BASLANGIC),
        "saat": int(time.time()),
    }


@app.route("/saglik/hazir")
def saglik_hazir():
    return ("hazir", 200)


@app.route("/", methods=["GET", "POST"])
def login():
    session.pop("USERID", None)
    session.pop("GAMEVERSION", None)
    load_saved_villages()  # kayıtlar sunucu kapanmadan düzenlenebilsin
    if request.method == "POST":
        uid = request.form.get("USERID", "")
        if not gecerli_uid(uid):
            return ("Gecersiz oyuncu kimligi", 400)
        session["USERID"] = uid
        session["GAMEVERSION"] = request.form.get("GAMEVERSION", "SocialEmpires0926bsec.swf")
        # Bot kaydıyla giriş yapıldıysa oyuncuya devret; yoksa dünya
        # simülasyonu aynı kayda yazarken çakışabilir.
        kayit = kayit_oturumu(uid)
        if kayit and kayit["playerInfo"].get("bot"):
            with save_lock:
                kayit["playerInfo"].pop("bot", None)
                kayit["playerInfo"].pop("bot_kisi", None)
                save_session(uid)
        return redirect("/play.html")
    from oyun.diyar import portre
    kayitlar = [k for k in all_saves_info() if not bot_mu(k["userid"])]
    for k in kayitlar:
        k["rutbe"] = rutbe(k["level"])
        k["resim"] = portre(kayit_oturumu(k["userid"]) or {})
    kayitlar.sort(key=lambda k: (-int(k["level"]), -int(k["xp"])))
    return render_template("login.html", saves_info=kayitlar, version=version_name, varlik=STATIK_YOL)


STATIK_YOL = "/default01.static.socialpointgames.com/static/socialempires/"
DINAMIK_YOL = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/"


def _xp_araligi(bilgi):
    """Başlıktaki XP çubuğu için (şimdiki, seviye başı, sonraki seviye)."""
    from oyun.config import get_game_config
    seviyeler = get_game_config()["levels"]
    sv = max(0, min(int(bilgi.get("level", 0)), len(seviyeler) - 1))
    bas = int(seviyeler[sv]["exp_required"])
    son = int(seviyeler[sv + 1]["exp_required"]) if sv + 1 < len(seviyeler) else bas
    return {"simdi": int(bilgi.get("xp", 0)), "bas": bas, "son": son}


def _oyun_sayfasi(sablon, ruffle_js=None):
    uid, surum = session.get("USERID"), session.get("GAMEVERSION")
    if not uid or not surum or uid not in all_saves_userid():
        return redirect("/")
    if ruffle_js is None:
        ruffle_js = f"/ruffle/{Ruffle.SURUM}/ruffle.js"
    # Oyun adresleri isteğin geldiği adrese göre kurulur: evdeki telefon
    # 192.168.x.x üzerinden açınca da varlıklar aynı sunucudan iner.
    kok = request.host_url.rstrip("/")
    bilgi = save_info(uid)
    return render_template(sablon, save_info=bilgi, serverTime=timestamp_now(),
                           friendsInfo=fb_friends_str(uid), version=version_name,
                           GAMEVERSION=surum, SERVERIP=HOST, ruffle_js=ruffle_js,
                           statik=kok + STATIK_YOL, dinamik=kok + DINAMIK_YOL,
                           rutbe=rutbe(bilgi.get("level", 0)), varlik=STATIK_YOL,
                           xp=_xp_araligi(bilgi))


@app.route("/play.html")
@app.route("/ruffle.html")
def play():
    return _oyun_sayfasi("oyun.html")


@app.route("/flash.html")
def flash():
    """Flash Player eklentili tarayıcılar için eski gömme sayfası."""
    return _oyun_sayfasi("play.html")


@app.route("/ruffle-deneme.html")
def ruffle_deneme():
    """Ruffle'ın gece sürümünü sabitlenmiş sürüme dokunmadan dener."""
    return _oyun_sayfasi("oyun.html", ruffle_js=Ruffle.DENEME_URL)


@app.route("/manifest.webmanifest")
def manifest():
    """Bilgisayarda 'uygulama olarak yükle' (Chrome/Edge service worker istemiyor)."""
    yanit = app.response_class(json.dumps({
        "name": "Social Empires Türkçe", "short_name": "Social Empires", "lang": "tr",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#2f7fd6", "theme_color": "#6e4a2b",
        "icons": [{"src": "/img/simge-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/img/simge-512.png", "sizes": "512x512", "type": "image/png"}],
    }, ensure_ascii=False), mimetype="application/manifest+json")
    return yanit


@app.route("/hazine")
def hazine():
    return render_template("hazine.html", version=version_name)


@app.route("/new.html")
def new():
    session["USERID"] = new_village()
    session["GAMEVERSION"] = "SocialEmpires0926bsec.swf"
    return redirect("play.html")


@app.route("/crossdomain.xml")
def crossdomain():
    return send_from_directory(STUB_DIR, "crossdomain.xml")


@app.route("/img/<path:path>")
def images(path):
    return send_from_directory(os.path.join(TEMPLATES_DIR, "img"), path)


@app.route("/css/<path:path>")
def css(path):
    return send_from_directory(os.path.join(TEMPLATES_DIR, "css"), path)


@app.route("/fonts/<path:path>")
def fonts(path):
    return send_from_directory(os.path.join(TEMPLATES_DIR, "fonts"), path)


@app.route("/js/<path:path>")
def js(path):
    return send_from_directory(os.path.join(TEMPLATES_DIR, "js"), path)


# Diğer uçlar (içe aktarılınca rotalarını kaydeder)
from oyun import diyar, gunluk, hile, istemci, kayit_yedek, onindirme, tasima, varliklar  # noqa: E402,F401


def yerel_ag_adresi():
    """Bu bilgisayarın ev ağındaki adresi (192.168.x.x); bulunamazsa 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # paket gönderilmez, yalnızca yol seçilir
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def calistir():
    from oyun.dunya import Dunya
    from oyun.yedek import baslat as yedekleri_baslat
    try:
        yedekleri_baslat()
        Dunya().baslat()
        Ruffle.brotli_baslat()
        dinlenen = HOST
        print(f" [+] Sunucu hazir: http://{HOST}:{PORT}/")
        if ayarlar.oku().get("ev_agi"):
            dinlenen = "0.0.0.0"
            print(f" [+] Ev agindaki telefon ve tabletler icin: http://{yerel_ag_adresi()}:{PORT}/")
        try:
            from waitress import serve
        except ImportError:
            print(" ! waitress kurulu degil; Flask gelistirme sunucusu kullaniliyor"
                  " (pip install -r requirements.txt)")
            app.run(host=dinlenen, port=PORT, debug=False, threaded=True, use_reloader=False)
            return
        serve(app, host=dinlenen, port=PORT, threads=IS_PARCACIGI, ident="SocialEmpiresTR")
    except Exception:
        try:
            os.makedirs(SAVES_DIR, exist_ok=True)
            with open(HATA_LOG, "a", encoding="utf-8") as f:
                f.write(f"\n=== ACILIS HATASI {timestamp_now()} ===\n")
                traceback.print_exc(file=f)
        except OSError:
            pass
        traceback.print_exc()
        input("Sunucu baslatilamadi. Kapatmak icin Enter'a basin...")
