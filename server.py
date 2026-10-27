print (" [+] Loading basics...")
import os
import json
import urllib
if os.name == 'nt':
    os.system("color")
    os.system("title Social Empires Server")
else:
    import sys
    sys.stdout.write("\x1b]2;Social Empires Server\x07")

print (" [+] Loading game config...")
from get_game_config import get_game_config, get_client_game_config, patch_game_config

print (" [+] Loading players...")
from get_player_info import get_player_info, get_neighbor_info
from sessions import (load_saved_villages, all_saves_userid, all_saves_info,
                      save_info, new_village, fb_friends_str, save_lock,
                      backup_session, save_session, session as kayit_oturumu)
load_saved_villages()

print (" [+] Loading server...")
from flask import Flask, render_template, send_from_directory, request, redirect, session
from flask.debughelpers import attach_enctype_error_multidict
from command import command
from engine import timestamp_now
from version import version_name
from constants import Constant
from quests import get_quest_map
from bundle import ASSETS_DIR, STUB_DIR, TEMPLATES_DIR, BASE_DIR
from world import Dunya

dunya = Dunya()

host = '127.0.0.1'
port = 5050

app = Flask(__name__, template_folder=TEMPLATES_DIR)
# Statik varlıklar (SWF/JPG) tarayıcıda/Flash'ta önbelleklensin: her açılışta
# yüzlerce dosya yeniden indirilmesin. Geliştirme sırasında değiştirdiğiniz
# dosyalar için Ctrl+F5 ile önbelleği temizleyin.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400
app.config["JSON_SORT_KEYS"] = False

HATA_LOG = os.path.join(BASE_DIR, "saves", "sunucu_hatalari.log")


@app.errorhandler(Exception)
def _hatayi_kaydet(hata):
    """Beklenmeyen hataları dosyaya yazar; sunucu ayakta kalır."""
    from werkzeug.exceptions import HTTPException
    if isinstance(hata, HTTPException):
        return hata
    import traceback
    try:
        os.makedirs(os.path.join(BASE_DIR, "saves"), exist_ok=True)
        with open(HATA_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {timestamp_now()} ===\n")
            traceback.print_exc(file=f)
    except OSError:
        pass
    print(" ! Sunucu hatasi (ayrinti saves/sunucu_hatalari.log):", hata)
    return ({"result": "error"}, 500)

print (" [+] Configuring server routes...")

##########
# ROUTES #
##########

## PAGES AND RESOURCES

@app.route("/", methods=['GET', 'POST'])
def login():
    # Log out previous session
    session.pop('USERID', default=None)
    session.pop('GAMEVERSION', default=None)
    # Reload saves. Allows saves modification without server reset
    load_saved_villages()
    # If logging in, set session USERID, and go to play
    if request.method == 'POST':
        session['USERID'] = request.form['USERID']
        session['GAMEVERSION'] = request.form['GAMEVERSION']
        # Bir bot kaydıyla giriş yapıldıysa onu oyuncuya devret; aksi halde
        # dünya simülasyonu aynı kaydı yazarken çakışma/domma olabiliyor.
        giris_kaydi = kayit_oturumu(session['USERID'])
        if giris_kaydi and giris_kaydi.get("playerInfo", {}).get("bot"):
            giris_kaydi["playerInfo"].pop("bot", None)
            giris_kaydi["playerInfo"].pop("bot_kisi", None)
            save_session(session['USERID'])
            print("[LOGIN] Bot kaydi oyuncuya devredildi:", session['USERID'])
        print("[LOGIN] USERID:", request.form['USERID'])
        print("[LOGIN] GAMEVERSION:", request.form['GAMEVERSION'])
        return redirect("/play.html")
    # Login page
    if request.method == 'GET':
        saves_info = all_saves_info()
        return render_template("login.html", saves_info=saves_info, version=version_name)

@app.route("/play.html")
def play():
    print(session)

    if 'USERID' not in session:
        return redirect("/")
    if 'GAMEVERSION' not in session:
        return redirect("/")

    if session['USERID'] not in all_saves_userid():
        return redirect("/")
    
    USERID = session['USERID']
    GAMEVERSION = session['GAMEVERSION']
    print("[PLAY] USERID:", USERID)
    print("[PLAY] GAMEVERSION:", GAMEVERSION)
    return render_template("play.html", save_info=save_info(USERID), serverTime=timestamp_now(), friendsInfo=fb_friends_str(USERID), version=version_name, GAMEVERSION=GAMEVERSION, SERVERIP=host)

@app.route("/ruffle.html")
def ruffle():
    print(session)

    if 'USERID' not in session:
        return redirect("/")
    if 'GAMEVERSION' not in session:
        return redirect("/")

    if session['USERID'] not in all_saves_userid():
        return redirect("/")
    
    USERID = session['USERID']
    GAMEVERSION = session['GAMEVERSION']
    print("[RUFFLE] USERID:", USERID)
    print("[RUFFLE] GAMEVERSION:", GAMEVERSION)
    return render_template("ruffle.html", save_info=save_info(USERID), serverTime=timestamp_now(), version=version_name, GAMEVERSION=GAMEVERSION, SERVERIP=host)


@app.route("/new.html")
def new():
    session['USERID'] = new_village()
    session['GAMEVERSION'] = "SocialEmpires0926bsec.swf"
    return redirect("play.html")

@app.route("/crossdomain.xml")
def crossdomain():
    return send_from_directory(STUB_DIR, "crossdomain.xml")

@app.route("/img/<path:path>")
def images(path):
    return send_from_directory(TEMPLATES_DIR + "/img", path)

@app.route("/css/<path:path>")
def css(path):
    return send_from_directory(TEMPLATES_DIR + "/css", path)

## GAME STATIC


@app.route("/default01.static.socialpointgames.com/static/socialempires/swf/05122012_projectiles.swf")
def similar_05122012_projectiles():
    return send_from_directory(ASSETS_DIR + "/swf", "20130417_projectiles.swf")

@app.route("/default01.static.socialpointgames.com/static/socialempires/swf/05122012_magicParticles.swf")
def similar_05122012_magicParticles():
    return send_from_directory(ASSETS_DIR + "/swf", "20131010_magicParticles.swf")

@app.route("/default01.static.socialpointgames.com/static/socialempires/swf/05122012_dynamic.swf")
def similar_05122012_dynamic():
    return send_from_directory(ASSETS_DIR + "/swf", "120608_dynamic.swf")

@app.route("/default01.static.socialpointgames.com/static/socialempires/<path:path>")
def static_assets_loader(path):
    # İstenen yolun varlık klasörünün dışına çıkmadığından emin ol.
    def _kok_icinde(kok, istenen):
        kok = os.path.abspath(kok)
        hedef = os.path.abspath(os.path.join(kok, istenen))
        return hedef == kok or hedef.startswith(kok + os.sep)

    if not _kok_icinde(ASSETS_DIR, path):
        return ("", 404)

    # Önce paketle gelen varlıklara bak, yoksa CDN'den indirileni kullan.
    yerel = os.path.join(ASSETS_DIR, path)
    indirilen_klasor = os.path.join(BASE_DIR, "download_assets", "assets")
    indirilen = os.path.join(indirilen_klasor, path)

    if os.path.exists(yerel):
        return send_from_directory(ASSETS_DIR, path)

    if os.path.exists(indirilen):
        print(f"====== USING EXTERNAL: download_assets/assets/{path}")
        return send_from_directory(indirilen_klasor, path)

    # Dosya hiçbir yerde yok: Social Point CDN'inden indirmeyi dene.
    os.makedirs(os.path.dirname(indirilen), exist_ok=True)
    URL = f"https://static.socialpointgames.com/static/socialempires/assets/{path}"
    try:
        urllib.request.urlretrieve(URL, indirilen)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as hata:
        print(f" ! Asset indirilemedi: {URL} ({hata})")
        return ("", 404)

    print(f"====== DOWNLOADED ASSET: {URL}")
    return send_from_directory(indirilen_klasor, path)

## GAME DYNAMIC

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/track_game_status.php", methods=['POST'])
def track_game_status_response():
    status = request.values['status']
    installId = request.values['installId']
    user_id = request.values['user_id']

    print(f"track_game_status: status={status}, installId={installId}, user_id={user_id}. --", request.values)
    return ("", 200)

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_game_config.php", methods=['GET','POST'])
def get_game_config_response():
    spdebug = None

    USERID = request.values['USERID']
    user_key = request.values['user_key']
    if 'spdebug' in request.values:
        spdebug = request.values['spdebug']
    language = request.values.get('language', 'en')

    print(f"get_game_config: USERID: {USERID}. --", request.values)
    # Zaman ölçeği uygulanmış config istemciye gider (sunucu aslını kullanır).
    return get_client_game_config()

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_player_info.php", methods=['POST'])
def get_player_info_response():

    USERID = request.values['USERID']
    user_key = request.values['user_key']
    spdebug = request.values['spdebug'] if 'spdebug' in request.values else None
    language = request.values.get('language', 'en')
    neighbors = request.values['neighbors'] if 'neighbors' in request.values else None
    client_id = request.values['client_id']
    user = request.values['user'] if 'user' in request.values else None
    map = int(request.values['map']) if 'map' in request.values else None

    print(f"get_player_info: USERID: {USERID}. user: {user} --", request.values)

    # Current Player
    if user is None:
        return (get_player_info(USERID), 200)
    # Arthur
    elif user == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_1 \
    or user == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_2 \
    or user == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_3:
        return (get_neighbor_info(user, map), 200)
    # Quest
    elif user.startswith("100000"): # Dirty but quick
        return get_quest_map(user)
    # Neighbor
    else:
        return (get_neighbor_info(user, map), 200)

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/sync_error_track.php", methods=['POST'])
def sync_error_track_response():
    spdebug = None

    USERID = request.values['USERID']
    user_key = request.values['user_key']
    if 'spdebug' in request.values:
        spdebug = request.values['spdebug']
    language = request.values.get('language', 'en')
    error = request.values['error']
    current_failed = request.values['current_failed']
    tries = request.values['tries'] if 'tries' in request.values else None
    survival = request.values['survival']
    previous_failed = request.values['previous_failed']
    description = request.values['description']
    user_id = request.values['user_id']

    print(f"sync_error_track: USERID: {USERID}. [Error: {error}] tries: {tries}. --", request.values)
    return ("", 200)

@app.route("/null")
def flash_sync_error_response():
    sp_ref_cat = request.values['sp_ref_cat']

    if sp_ref_cat == "flash_sync_error":
        reason = "reload On Sync Error"
    elif sp_ref_cat == "flash_reload_quest":
        reason = "reload On End Quest"
    elif sp_ref_cat == "flash_reload_attack":
        reason = "reload On End Attack"

    print("flash_sync_error", reason, ". --", request.values)
    return redirect("/play.html")

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/command.php", methods=['POST'])
def command_response():
    spdebug = None

    USERID = request.values['USERID']
    user_key = request.values['user_key']
    if 'spdebug' in request.values:
        spdebug = request.values['spdebug']
    language = request.values.get('language', 'en')
    client_id = request.values['client_id']

    print(f"command: USERID: {USERID}. --", request.values)

    data_str = request.values.get('data', '')
    if len(data_str) < 65 or data_str[64] != ';':
        print(" ! Gecersiz komut paketi (hash;veri formati bozuk)")
        return ({"result": "error"}, 400)

    data_payload = data_str[65:]
    try:
        data = json.loads(data_payload)
    except json.JSONDecodeError as hata:
        print(f" ! Komut JSON'u cozulemedi: {hata}")
        return ({"result": "error"}, 400)

    try:
        with save_lock:  # aynı anda gelen komutlar kaydı ezmesin
            command(USERID, data)
    except Exception:
        # Tek bir komut hatasi tum oturumu dusurmesin; kayit yine yazilsin.
        import traceback
        traceback.print_exc()

    return ({"result": "success"}, 200)

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_continent_ranking.php")
def get_continent_ranking_response():

    USERID = request.values.get('USERID', '')
    worldChange = request.values.get('worldChange', '0')
    if 'spdebug' in request.values:
        spdebug = request.values['spdebug']
    town_id = request.values.get('map', '0')
    user_key = request.values.get('user_key', '')

    # Kayıtlı oyuncuları XP'ye göre sırala; istemci ilk 8 sırayı gösteriyor.
    oyuncular = []
    for uid in all_saves_userid():
        kayit = kayit_oturumu(uid)
        if not kayit:
            continue
        harita = kayit["maps"][0]
        oyuncular.append({
            "user_id": str(uid),
            "name": kayit["playerInfo"].get("name", ""),
            "nivel": harita.get("level", 1),
            "xp": harita.get("xp", 0),
        })
    oyuncular.sort(key=lambda o: o["xp"], reverse=True)

    continent = [
        {"posicion": i, "nivel": o["nivel"], "user_id": o["user_id"]}
        for i, o in enumerate(oyuncular[:8])
    ]
    for i in range(len(continent), 8):
        continent.append({"posicion": i, "nivel": 0})

    return {"world_id": 0, "continent": continent}


########
# DÜNYA GEZGİNİ (ada / kıta)
########

def _ada_slotlari():
    """Adadaki 7 bölgeyi oyunculardan doldurur."""
    oyuncular = []
    for uid in all_saves_userid():
        kayit = kayit_oturumu(uid)
        if not kayit:
            continue
        harita = kayit["maps"][0]
        pi = kayit.get("playerInfo", {})
        oyuncular.append({
            "user_id": str(uid),
            "name": pi.get("name", "Oyuncu"),
            "pic": pi.get("pic", ""),
            "nivel": int(harita.get("level", 1)),
            "conquered": 0,
        })
    slotlar = []
    for i in range(7):
        if i < len(oyuncular):
            slot = dict(oyuncular[i])
            slot["posicion"] = i
        else:
            slot = {"posicion": i, "nivel": 0}
        slotlar.append(slot)
    return slotlar


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_continent.php")
def get_continent_response():
    slotlar = _ada_slotlari()
    print(f"[ADA] get_continent: {dict(request.values)} -> {len(slotlar)} bolge")
    ada = {"id": 99, "number": 99, "users": slotlar, "territories": slotlar}
    return {
        "result": "ok",
        "world_id": 0,
        "continent": slotlar,
        "continentNumber": 99,
        "continentId": 99,
        "myContinentId": 99,
        "continentData": ada,
        "users": slotlar,
        "territories": slotlar,
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_user_world.php")
def get_user_world_response():
    print(f"[ADA] get_user_world: {dict(request.values)}")
    return {"result": "ok", "world_id": 0, "continentNumber": 99, "island": 99}


########
# DÜNYA HARİTASI
########


@app.route("/dunya")
def dunya_sayfasi():
    return render_template("dunya.html")


@app.route("/dunya/veri")
def dunya_verisi():
    return (dunya.veri(), 200)


@app.route("/dunya/tick", methods=["POST"])
def dunya_tick():
    """Simülasyonu elle bir tur ilerletir (yalnızca bu bilgisayar)."""
    if not _hile_izinli():
        return ({"hata": "yasak"}, 403)
    dunya.tek_tick()
    return ({"ok": True, "tick": dunya.tick}, 200)


########
# KEŞİF: henüz uygulanmayan uçları günlüğe yaz
########

def _http_gunlugune_yaz(yol):
    """İstemcinin çağırdığı ama sunucuda karşılığı olmayan istekleri kaydeder."""
    try:
        os.makedirs(os.path.join(BASE_DIR, "saves"), exist_ok=True)
        with open(os.path.join(BASE_DIR, "saves", "http_gunlugu.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"yol": yol, "method": request.method, "args": request.values.to_dict()},
                ensure_ascii=False,
            ) + "\n")
    except OSError:
        pass
    print(f"[EKSIK UC] {request.method} /{yol} -> {dict(request.values)}")


@app.route("/tournaments/<path:yol>", methods=["GET", "POST"])
def tournament_kesif(yol):
    _http_gunlugune_yaz("tournaments/" + yol)
    return ("", 404)


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/<path:yol>", methods=["GET", "POST"])
def bilinmeyen_dinamik_uc(yol):
    _http_gunlugune_yaz(yol)
    return ("", 404)


########
# HİLE PANELİ (yalnızca bu bilgisayar)
########

def _hile_izinli():
    """Panelin yalnızca yerel makineden ve aynı kökenden çağrılmasını sağlar."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return False
    koken = request.headers.get("Origin")
    if koken and koken.rstrip("/") != request.host_url.rstrip("/"):
        return False
    return True


def _kayit_ozeti(kayit):
    harita = kayit["maps"][0]
    return {
        "seviye": harita["level"],
        "xp": harita["xp"],
        "altin": harita["coins"],
        "odun": harita["wood"],
        "tas": harita["stone"],
        "yemek": harita["food"],
        "cash": kayit["playerInfo"]["cash"],
    }


@app.route("/cheat")
def cheat_sayfasi():
    if not _hile_izinli():
        return ("", 403)
    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return redirect("/")
    return render_template("cheat.html", save_info=save_info(uid), version=version_name)


@app.route("/cheat/uygula", methods=["POST"])
def cheat_uygula():
    if not _hile_izinli():
        return ({"hata": "yasak"}, 403)
    if not request.is_json:
        return ({"hata": "JSON gerekli"}, 400)

    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return ({"hata": "oturum yok"}, 401)

    veri = request.get_json(silent=True) or {}
    islem = veri.get("islem")
    kayit = kayit_oturumu(uid)
    harita = kayit["maps"][0]

    try:
        with save_lock:
            if islem == "kaynak":
                tur = veri.get("tur")
                miktar = int(veri.get("miktar", 1000))
                if miktar <= 0 or miktar > 10 ** 9:
                    return ({"hata": "gecersiz miktar"}, 400)
                if tur == "cash":
                    kayit["playerInfo"]["cash"] = int(kayit["playerInfo"].get("cash", 0)) + miktar
                elif tur in ("wood", "stone", "food", "coins"):
                    harita[tur] = int(harita.get(tur, 0)) + miktar
                else:
                    return ({"hata": "gecersiz kaynak"}, 400)

            elif islem == "seviye":
                seviyeler = get_game_config()["levels"]
                yeni = int(veri.get("delta", 1)) + int(harita["level"])
                yeni = max(0, min(yeni, len(seviyeler) - 1))
                harita["level"] = yeni
                harita["xp"] = int(seviyeler[yeni]["exp_required"])

            elif islem == "max_seviye":
                seviyeler = get_game_config()["levels"]
                yeni = len(seviyeler) - 1
                harita["level"] = yeni
                harita["xp"] = int(seviyeler[yeni]["exp_required"])

            elif islem == "egitim":
                kayit["playerInfo"]["completed_tutorial"] = 1
                kayit["privateState"]["dragonNestActive"] = 1

            elif islem == "kalkan":
                saat = max(1, min(72, int(veri.get("saat", 12))))
                kayit.setdefault("privateState", {})["shield_until"] = timestamp_now() + saat * 3600

            elif islem == "yedek":
                backup_session(uid)

            else:
                return ({"hata": "bilinmeyen islem"}, 400)

            save_session(uid)
    except (KeyError, ValueError, TypeError) as hata:
        return ({"hata": str(hata)}, 400)

    print(f"[HILE] {islem} {veri} -> ok")
    return ({"ok": True, "ozet": _kayit_ozeti(kayit)}, 200)


########
# MAIN #
########

print (" [+] Running server...")

if __name__ == '__main__':
    try:
        from backups_daily import baslat as yedekleri_baslat
        yedekleri_baslat()
        dunya.baslat()
        app.secret_key = 'SECRET_KEY'
        # threaded=True: Flash aynı anda onlarca varlık istiyor; tek iş
        # parçacığı bunları sırayla sunup yükleme süresini uzatıyordu.
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
    except Exception:
        import traceback
        try:
            with open(HATA_LOG, "a", encoding="utf-8") as f:
                f.write(f"\n=== ACILIS HATASI {timestamp_now()} ===\n")
                traceback.print_exc(file=f)
        except OSError:
            pass
        traceback.print_exc()
        input("Sunucu baslatilamadi. Kapatmak icin Enter'a basin...")
