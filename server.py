print (" [+] Loading basics...")
import os
import time
import json
import hashlib
import urllib.request
import urllib.error
import tempfile
import traceback
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
                      save_info, new_village, fb_friends_str, save_lock, gecerli_uid,
                      backup_session, save_session, neighbors, session as kayit_oturumu)
load_saved_villages()

print (" [+] Loading server...")
from flask import Flask, render_template, send_from_directory, request, redirect, session
from flask.debughelpers import attach_enctype_error_multidict
from command import command
from engine import timestamp_now
from version import version_name, version_code
from constants import Constant
from quests import get_quest_map
from bundle import ASSETS_DIR, STUB_DIR, TEMPLATES_DIR, BASE_DIR
from world import Dunya
import turnuva as Turnuva
import ada as Ada
import sezon as Sezon
import basari
import koleksiyon
import etkinlik
import gorev
import magaza
import sosyal

dunya = Dunya()
app_secret = os.environ.get('SE_SECRET_KEY', 'SECRET_KEY')

OYUN_DILI = 'tr'  # istemci yerel ayarı 'en' kalsa da metinler Türkçe gönderilir
host = '127.0.0.1'
port = 5050

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = app_secret
BASLANGIC = time.time()
# Statik varlıklar (SWF/JPG) tarayıcıda/Flash'ta önbelleklensin: her açılışta
# yüzlerce dosya yeniden indirilmesin. Geliştirme sırasında değiştirdiğiniz
# dosyalar için Ctrl+F5 ile önbelleği temizleyin.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400
app.config["JSON_SORT_KEYS"] = False

HATA_LOG = os.path.join(BASE_DIR, "saves", "sunucu_hatalari.log")


def _sayisal_kimlik(uid):
    """Ada haritası sayısal user_id beklediği için UUID'den sabit sayı üretir."""
    return str(int(hashlib.md5(str(uid).encode("utf-8")).hexdigest()[:8], 16))


def _kimlikten_uid(kimlik):
    for uid in all_saves_userid():
        if _sayisal_kimlik(uid) == str(kimlik):
            return uid
    return None
ISTEK_LOG = os.path.join(BASE_DIR, "saves", "http_gunlugu.jsonl")


@app.after_request
def _ada_isteklerini_kaydet(cevap):
    """Ada/turnuva isteklerini ve dönen veriyi dosyaya yazar (teşhis için)."""
    yol = request.path
    if not any(parca in yol for parca in ("get_continent", "get_user_world", "get_public_player_info", "tournament")):
        return cevap
    try:
        os.makedirs(os.path.join(BASE_DIR, "saves"), exist_ok=True)
        govde = cevap.get_data(as_text=True)
        with open(ISTEK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "yol": yol,
                "args": request.values.to_dict(),
                "durum": cevap.status_code,
                "uzunluk": len(govde),
                "govde": govde[:1500],
            }, ensure_ascii=False) + "\n")
    except (OSError, RuntimeError):
        pass
    return cevap


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

@app.route("/saglik")
def saglik():
    return {
        "durum": "ok",
        "surum": version_code,
        "oyuncu": len(all_saves_userid()),
        "calisma_suresi": int(time.time() - BASLANGIC),
        "dunya_tick": getattr(dunya, "tick", None),
        "saat": int(time.time()),
    }


@app.route("/saglik/hazir")
def saglik_hazir():
    return ("hazir", 200)


@app.route("/", methods=['GET', 'POST'])
def login():
    # Log out previous session
    session.pop('USERID', default=None)
    session.pop('GAMEVERSION', default=None)
    # Reload saves. Allows saves modification without server reset
    load_saved_villages()
    # If logging in, set session USERID, and go to play
    if request.method == 'POST':
        if not gecerli_uid(request.form.get('USERID', '')):
            return ("Gecersiz oyuncu kimligi", 400)
        session['USERID'] = request.form.get('USERID', '')
        session['GAMEVERSION'] = request.form.get('GAMEVERSION', 'SocialEmpires0926bsec.swf')
        # Bir bot kaydıyla giriş yapıldıysa onu oyuncuya devret; aksi halde
        # dünya simülasyonu aynı kaydı yazarken çakışma/domma olabiliyor.
        giris_kaydi = kayit_oturumu(session['USERID'])
        if giris_kaydi and giris_kaydi.get("playerInfo", {}).get("bot"):
            giris_kaydi["playerInfo"].pop("bot", None)
            giris_kaydi["playerInfo"].pop("bot_kisi", None)
            save_session(session['USERID'])
            print("[LOGIN] Bot kaydi oyuncuya devredildi:", session['USERID'])
        print("[LOGIN] USERID:", session['USERID'])
        print("[LOGIN] GAMEVERSION:", session['GAMEVERSION'])
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

    def _varlik_gecerli(yol):
        try:
            if os.path.getsize(yol) < 64:
                return False
            with open(yol, "rb") as f:
                ilk = f.read(4)
            return not ilk.startswith(b"<")  # CDN'in HTML hata sayfası olmasın
        except OSError:
            return False

    if os.path.exists(indirilen):
        if _varlik_gecerli(indirilen):
            print(f"====== USING EXTERNAL: download_assets/assets/{path}")
            return send_from_directory(indirilen_klasor, path)
        # Yarım/bozuk indirme: sil, yeniden dene
        try:
            os.remove(indirilen)
        except OSError:
            pass

    # Dosya hiçbir yerde yok: Social Point CDN'inden indirmeyi dene.
    os.makedirs(os.path.dirname(indirilen), exist_ok=True)
    URL = f"https://static.socialpointgames.com/static/socialempires/assets/{path}"
    gecici = None
    try:
        fd, gecici = tempfile.mkstemp(dir=os.path.dirname(indirilen), prefix="indir-", suffix=".tmp")
        os.close(fd)
        urllib.request.urlretrieve(URL, gecici)
        if not _varlik_gecerli(gecici):
            raise OSError("indirilen dosya gecersiz")
        os.replace(gecici, indirilen)  # atomik: yarım dosya servis edilmez
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as hata:
        print(f" ! Asset indirilemedi: {URL} ({hata})")
        if gecici and os.path.exists(gecici):
            try:
                os.remove(gecici)
            except OSError:
                pass
        return ("", 404)

    print(f"====== DOWNLOADED ASSET: {URL}")
    return send_from_directory(indirilen_klasor, path)

## GAME DYNAMIC

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/track_game_status.php", methods=['POST'])
def track_game_status_response():
    status = request.values.get('status', '')
    installId = request.values.get('installId', '')
    user_id = request.values.get('user_id', '')

    print(f"track_game_status: status={status}, installId={installId}, user_id={user_id}. --", request.values)
    return ("", 200)

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_game_config.php", methods=['GET','POST'])
def get_game_config_response():
    spdebug = None

    USERID = request.values.get('USERID', '')
    user_key = request.values.get('user_key', '')
    if 'spdebug' in request.values:
        spdebug = request.values['spdebug']
    language = request.values.get('language', 'en')

    print(f"get_game_config: USERID: {USERID} istemci dili: {language} -> {OYUN_DILI}. --", request.values)
    # İstemci yerel ayarı 'en' kalır (bilinen çalışan yol); metinler OYUN_DILI'ne göre gelir.
    try:
        return get_client_game_config(OYUN_DILI, ascii_mode=True)
    except Exception:
        traceback.print_exc()
        print(" ! Ceviri config'i uretilemedi; Ingilizceye donuluyor")
        return get_client_game_config("en")

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_player_info.php", methods=['POST'])
def get_player_info_response():

    USERID = request.values.get('USERID', '')
    user_key = request.values.get('user_key', '')
    spdebug = request.values.get('spdebug')
    language = request.values.get('language', 'en')
    neighbors = request.values['neighbors'] if 'neighbors' in request.values else None
    client_id = request.values['client_id']
    user = request.values.get('user')
    if user and str(user).isdigit():
        cozulen = _kimlikten_uid(user)
        if cozulen:
            user = cozulen
    map = int(request.values.get('map', 0) or 0)

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

    USERID = request.values.get('USERID', '')
    user_key = request.values.get('user_key', '')
    if 'spdebug' in request.values:
        spdebug = request.values['spdebug']
    language = request.values.get('language', 'en')
    error = request.values.get('error', '')
    current_failed = request.values.get('current_failed', '')
    tries = request.values['tries'] if 'tries' in request.values else None
    survival = request.values.get('survival', '')
    previous_failed = request.values.get('previous_failed', '')
    description = request.values.get('description', '')
    user_id = request.values.get('user_id', '')

    print(f"sync_error_track: USERID: {USERID}. [Error: {error}] tries: {tries}. --", request.values)
    return ("", 200)

@app.route("/null")
def flash_sync_error_response():
    sp_ref_cat = request.values.get('sp_ref_cat', '')
    reason = "reload"

    if sp_ref_cat == "flash_sync_error":
        reason = "reload On Sync Error"
    elif sp_ref_cat == "flash_reload_quest":
        reason = "reload On End Quest"
    elif sp_ref_cat == "flash_reload_attack":
        reason = "reload On End Attack"

    print("flash_sync_error", reason, ". --", request.values)
    return redirect("/play.html")

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_achievements.php", methods=["GET", "POST"])
def get_achievements_response():
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    if not kayit:
        return {"result": "ok", "achievements": []}
    with save_lock:
        basari.kontrol(kayit)
        save_session(uid)
    return {"result": "ok", "achievements": basari.liste(kayit), "data": basari.liste(kayit)}


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_store.php", methods=["GET", "POST"])
def get_store_response():
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    cash = int(kayit.get("playerInfo", {}).get("cash", 0) or 0) if kayit else 0
    return {
        "result": "ok",
        "cash": cash,
        "offers": get_game_config().get("offer_packs", []),
        "warehouse": magaza.stok_durumu(kayit) if kayit else {},
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_collections.php", methods=["GET", "POST"])
def get_collections_response():
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    return {
        "result": "ok",
        "categories": koleksiyon.kategoriler(),
        "status": koleksiyon.durum(kayit) if kayit else {},
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_events.php", methods=["GET", "POST"])
def get_events_response():
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    if kayit:
        with save_lock:
            haftalik = gorev.haftalik_durum(kayit)
            save_session(uid)
    else:
        haftalik = {}
    return {
        "result": "ok",
        "events": etkinlik.durum(kayit) if kayit else {},
        "weekly": haftalik,
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_social.php", methods=["GET", "POST"])
def get_social_response():
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    if kayit:
        with save_lock:
            durum = sosyal.durum(kayit)
            save_session(uid)
    else:
        durum = {}
    return {
        "result": "ok",
        "social": durum,
        "neighbors": max(0, len(all_saves_userid()) - 1) if uid else 0,
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/send_gift.php", methods=["GET", "POST"])
def send_gift_response():
    uid = request.values.get("USERID", "")
    hedef_uid = request.values.get("target") or request.values.get("to") or request.values.get("friend")
    esya_id = request.values.get("item") or request.values.get("item_id")
    if not (uid and hedef_uid and esya_id):
        return {"result": "error", "message": "eksik alan"}, 400
    gonderen = kayit_oturumu(uid)
    hedef = kayit_oturumu(str(hedef_uid))
    if not gonderen or not hedef:
        return {"result": "error", "message": "oyuncu bulunamadi"}, 404
    with save_lock:
        oldu = sosyal.hediye_gonder(gonderen, hedef, str(hedef_uid), int(esya_id))
        if oldu:
            save_session(uid)
            if str(hedef_uid) in all_saves_userid():
                save_session(str(hedef_uid))
    return {"result": "ok" if oldu else "error"}


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/command.php", methods=['POST'])
def command_response():
    spdebug = None

    USERID = request.values.get('USERID', '')
    user_key = request.values.get('user_key', '')
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

@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_continent_ranking.php", methods=["GET", "POST"])
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
            "user_id": _sayisal_kimlik(uid),
            "uid": str(uid),
            "name": kayit["playerInfo"].get("name", ""),
            "pic": kayit["playerInfo"].get("pic") or "/img/profile/1025.png",
            "nivel": harita.get("level", 1),
            "level": harita.get("level", 1),
            "xp": harita.get("xp", 0),
            "trophies": int(kayit.get("privateState", {}).get("trophies", 0)),
        })
    oyuncular.sort(key=lambda o: o["xp"], reverse=True)

    continent = [
        {"posicion": i, "nivel": o["nivel"], "level": o["level"],
         "user_id": o["user_id"], "id": o["user_id"], "uid": o["uid"],
         "name": o["name"], "pic": o["pic"], "trophies": o["trophies"]}
        for i, o in enumerate(oyuncular[:8])
    ]
    for i in range(len(continent), 8):
        continent.append({"posicion": i, "nivel": 0})

    return {"world_id": 0, "continent": continent, "season": Sezon.bilgi()}


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
            slot.update({
                "posicion": i, "pos": i, "position": i,
                "id": slot["user_id"], "userId": slot["user_id"], "saveId": slot["user_id"],
                "level": slot["nivel"], "state": 0, "isConquered": 0,
            })
        else:
            slot = {"posicion": i, "pos": i, "position": i, "nivel": 0, "level": 0}
        slotlar.append(slot)
    return slotlar


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_continent.php", methods=["GET", "POST"])
def get_continent_response():
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    durum = Ada.ada_durumu(kayit) if kayit else {"ada": 99, "fetih": 0, "toplam": 7, "slotlar": []}
    slotlar = durum["slotlar"]
    fetih_pozisyonlari = [s["posicion"] for s in slotlar if s["conquered"]]
    print(f"[ADA] get_continent: {dict(request.values)} -> {len(slotlar)} bolge")
    ada = {
        "id": durum["ada"], "number": durum["ada"], "continentId": durum["ada"], "continentNumber": durum["ada"],
        "saveId": durum["ada"], "continentSaveId": durum["ada"], "world_id": 0,
        "users": slotlar, "territories": slotlar, "players": slotlar,
        "islands": [{"id": durum["ada"], "number": durum["ada"], "users": slotlar}],
        "ada": durum["ada"],
        "conquered": durum["fetih"],
        "progress": {"done": durum["fetih"], "total": durum["toplam"]},
        "island": durum["ada"],
        "arCurrentConquered": fetih_pozisyonlari,
    }
    return {
        "result": "ok",
        "success": True,
        "world_id": 0,
        "continent": slotlar,
        "continentNumber": durum["ada"],
        "continentId": durum["ada"],
        "continentSaveId": durum["ada"],
        "myContinentId": durum["ada"],
        "continentData": ada,
        "users": slotlar,
        "territories": slotlar,
        "players": slotlar,
        "islands": [{"id": durum["ada"], "number": durum["ada"], "users": slotlar}],
        "ada": durum["ada"],
        "island": durum["ada"],
        "conquered": durum["fetih"],
        "arCurrentConquered": fetih_pozisyonlari,
        "progress": {"done": durum["fetih"], "total": durum["toplam"]},
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_public_player_info.php", methods=["GET", "POST"])
def get_public_player_info_response():
    kimlik = (request.values.get("user_id") or request.values.get("user")
              or request.values.get("USERID") or "")
    uid = _kimlikten_uid(kimlik)
    if uid is None and str(kimlik) in all_saves_userid():
        uid = str(kimlik)
    kayit = kayit_oturumu(uid) if uid else None
    if not kayit:
        return ({"result": "error"}, 404)
    harita = kayit["maps"][0]
    pi = kayit.get("playerInfo", {})
    return {
        "result": "ok",
        "user_id": _sayisal_kimlik(uid),
        "id": _sayisal_kimlik(uid),
        "uid": str(uid),
        "playerInfo": {
            "pid": str(uid),
            "user_id": _sayisal_kimlik(uid),
            "name": pi.get("name", ""),
            "pic": pi.get("pic") or "/img/profile/1025.png",
            "level": int(harita.get("level", 1)),
            "nivel": int(harita.get("level", 1)),
            "xp": int(harita.get("xp", 0)),
            "trophies": int(kayit.get("privateState", {}).get("trophies", 0)),
            "world_id": int(pi.get("world_id") or 0),
        },
    }


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_user_world.php", methods=["GET", "POST"])
def get_user_world_response():
    print(f"[ADA] get_user_world: {dict(request.values)}")
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid) if uid else None
    durum = Ada.ada_durumu(kayit) if kayit else {"ada": 99, "fetih": 0, "toplam": 7}
    return {
        "result": "ok", "success": True, "world_id": 0,
        "continentId": durum["ada"], "continentNumber": durum["ada"], "myContinentId": durum["ada"],
        "island": durum["ada"], "islandId": durum["ada"],
        "conquered": durum["fetih"], "progress": {"done": durum["fetih"], "total": durum["toplam"]},
        "islands": [{"id": durum["ada"], "number": durum["ada"]}],
    }


########
# TURNUVALAR
########

def _turnuva_govde():
    ham = request.values.get("data", "")
    if ";" in ham:
        ham = ham.split(";", 1)[1]
    try:
        return json.loads(ham) if ham else {}
    except json.JSONDecodeError:
        return {}


def _turnuva_yanit(turnuva):
    if not turnuva:
        return {"result": "error"}
    return {
        "result": "ok",
        "tournament": turnuva,
        "tournaments": [turnuva],
        "data": turnuva,
        "tournamentId": turnuva.get("id"),
    }


@app.route("/tournaments/create_tournament.php", methods=["GET", "POST"])
def turnuva_create():
    uid = request.values.get("USERID", "")
    veri = _turnuva_govde()
    turnuva = Turnuva.turnuva_olustur(uid, veri.get("type", "general"), veri.get("entryCost", 0))
    Turnuva.gunluge_yaz("create", {"uid": uid, "veri": veri, "id": (turnuva or {}).get("id")})
    return _turnuva_yanit(turnuva)


@app.route("/tournaments/join_tournament.php", methods=["GET", "POST"])
def turnuva_join():
    uid = request.values.get("USERID", "")
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    turnuva = Turnuva.turnuvaya_katil(tid, uid) if tid else None
    Turnuva.gunluge_yaz("join", {"uid": uid, "veri": veri})
    return _turnuva_yanit(turnuva)


@app.route("/tournaments/start_tournament_match.php", methods=["GET", "POST"])
def turnuva_start_match():
    uid = request.values.get("USERID", "")
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    sonuc = Turnuva.mac_baslat(tid, uid) if tid else None
    Turnuva.gunluge_yaz("start_match", {"uid": uid, "veri": veri, "sonuc": bool(sonuc)})
    if not sonuc:
        return {"result": "error"}
    return {"result": "ok", "match": sonuc["match"], "opponent": sonuc["opponent"], "data": sonuc}


@app.route("/tournaments/finish_tournament_match.php", methods=["GET", "POST"])
def turnuva_finish_match():
    uid = request.values.get("USERID", "")
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    ham = veri.get("win", veri.get("kazandi", 0))
    kazandi = str(ham).strip().lower() in ("1", "true", "yes", "evet")
    turnuva = Turnuva.mac_bitir(tid, uid, kazandi) if tid else None
    Turnuva.gunluge_yaz("finish_match", {"uid": uid, "veri": veri, "kazandi": kazandi})
    return _turnuva_yanit(turnuva)


@app.route("/tournaments/get_tournament_info.php", methods=["GET", "POST"])
def turnuva_info():
    uid = request.values.get("USERID", "")
    Turnuva.eski_turnuvalari_temizle()
    turnuva = Turnuva.bul_veya_olustur(uid) if uid else None
    if turnuva:
        return _turnuva_yanit(turnuva)
    return {"result": "ok", "tournament": None, "tournaments": Turnuva.turnuvalar(uid), "data": None}


@app.route("/tournaments/cancel_tournament.php", methods=["GET", "POST"])
def turnuva_cancel():
    uid = request.values.get("USERID", "")
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    turnuva = Turnuva.turnuva_iptal(tid, uid) if tid else None
    Turnuva.gunluge_yaz("cancel", {"uid": uid, "veri": veri})
    return _turnuva_yanit(turnuva)


@app.route("/tournaments/leave_tournament.php", methods=["GET", "POST"])
def turnuva_leave():
    uid = request.values.get("USERID", "")
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    turnuva = Turnuva.turnuvadan_ayril(tid, uid) if tid else None
    Turnuva.gunluge_yaz("leave", {"uid": uid, "veri": veri})
    return _turnuva_yanit(turnuva)


@app.route("/tournaments/clean_tournament.php", methods=["GET", "POST"])
def turnuva_clean():
    Turnuva.eski_turnuvalari_temizle()
    return {"result": "ok"}


@app.route("/tournaments/finish_all_match_tournament.php", methods=["GET", "POST"])
@app.route("/tournaments/reset_player_tournament.php", methods=["GET", "POST"])
@app.route("/tournaments/add_player_tournament.php", methods=["GET", "POST"])
def turnuva_admin_islem():
    Turnuva.gunluge_yaz("admin", dict(request.values))
    return {"result": "ok"}


@app.route("/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/tournaments/<path:ad>", methods=["GET", "POST"])
def turnuva_dinamik(ad):
    """İstemci turnuva uçlarını /srvempires/tournaments/... altından çağırıyor."""
    islevler = {
        "create_tournament.php": turnuva_create,
        "join_tournament.php": turnuva_join,
        "start_tournament_match.php": turnuva_start_match,
        "finish_tournament_match.php": turnuva_finish_match,
        "get_tournament_info.php": turnuva_info,
        "cancel_tournament.php": turnuva_cancel,
        "leave_tournament.php": turnuva_leave,
        "clean_tournament.php": turnuva_clean,
        "finish_all_match_tournament.php": turnuva_admin_islem,
        "reset_player_tournament.php": turnuva_admin_islem,
        "add_player_tournament.php": turnuva_admin_islem,
    }
    islev = islevler.get(ad)
    if not islev:
        Turnuva.gunluge_yaz("bilinmeyen", {"ad": ad, "args": dict(request.values)})
        return {"result": "error", "message": "unknown tournament endpoint"}, 404
    return islev()


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
        Sezon.kontrol()
        dunya.baslat()
        app.secret_key = app_secret
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
