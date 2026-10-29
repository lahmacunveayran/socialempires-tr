"""İstemcinin oyun sunucusuna yaptığı istekler (dynamicUrl altındaki uçlar)."""

import hashlib
import json
import os
import traceback

from flask import jsonify, redirect, request

from oyun import ada as Ada
from oyun import sezon as Sezon
from oyun import turnuva as Turnuva
from oyun.config import get_client_game_config
from oyun.kayit import (all_saves_userid, gecerli_uid, neighbor_session, save_lock,
                        session as kayit_oturumu)
from oyun.komutlar import command
from oyun.oyuncu import get_neighbor_info, get_player_info, get_quest_map
from oyun.sunucu import OYUN_DILI, app
from oyun.yollar import SAVES_DIR

DINAMIK = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


def _sayisal_kimlik(uid):
    """Ada haritası sayısal user_id beklediği için UUID'den sabit sayı üretir."""
    return str(int(hashlib.sha256(str(uid).encode("utf-8")).hexdigest()[:8], 16))


def _kimlikten_uid(kimlik):
    for uid in all_saves_userid():
        if _sayisal_kimlik(uid) == str(kimlik):
            return uid
    return None


@app.route(DINAMIK + "/track_game_status.php", methods=["POST"])
def track_game_status_response():
    print("track_game_status:", request.values.get("status", ""))
    return ("", 200)


@app.route(DINAMIK + "/get_game_config.php", methods=["GET", "POST"])
def get_game_config_response():
    # İstemcinin dil ayarından bağımsız olarak metinler OYUN_DILI'nde gönderilir.
    try:
        return get_client_game_config(OYUN_DILI)
    except Exception:
        traceback.print_exc()
        print(" ! Ceviri config'i uretilemedi; Ingilizceye donuluyor")
        return get_client_game_config("en")


@app.route(DINAMIK + "/get_player_info.php", methods=["POST"])
def get_player_info_response():
    uid = request.values.get("USERID", "")
    kullanici = request.values.get("user")
    harita_no = int(request.values.get("map", 0) or 0)
    if kullanici is None:
        return (get_player_info(uid, harita_no), 200)
    if kullanici.isdigit():  # ada haritası sayısal kimlik gönderir
        kullanici = _kimlikten_uid(kullanici) or kullanici
    if neighbor_session(kullanici) is None and kullanici.startswith("100000"):
        return get_quest_map(kullanici)  # görev (quest) haritası
    return (get_neighbor_info(kullanici, harita_no), 200)


@app.route(DINAMIK + "/sync_error_track.php", methods=["POST"])
def sync_error_track_response():
    print("sync_error_track:", request.values.get("error", ""), dict(request.values))
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

@app.route(DINAMIK + "/command.php", methods=["POST"])
def command_response():
    uid = request.values.get("USERID", "")
    # Biçim: <64 karakter imza>;<JSON>
    paket = request.values.get("data", "")
    if len(paket) < 65 or paket[64] != ";":
        print(" ! Gecersiz komut paketi (imza;veri bicimi bozuk)")
        return ({"result": "error"}, 400)
    try:
        veri = json.loads(paket[65:])
    except json.JSONDecodeError as hata:
        print(f" ! Komut JSON'u cozulemedi: {hata}")
        return ({"result": "error"}, 400)
    if kayit_oturumu(uid) is None:
        return ({"result": "error"}, 404)
    with save_lock:  # aynı anda gelen komutlar kaydı ezmesin
        command(uid, veri)
    return ({"result": "success"}, 200)


@app.route(DINAMIK + "/get_continent_ranking.php", methods=["GET", "POST"])
def get_continent_ranking_response():
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


@app.route(DINAMIK + "/get_continent.php", methods=["GET", "POST"])
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


@app.route(DINAMIK + "/get_public_player_info.php", methods=["GET", "POST"])
def get_public_player_info_response():
    kimlik = (request.values.get("user_id") or request.values.get("user")
              or request.values.get("USERID") or "")
    uid = _kimlikten_uid(kimlik)
    if uid is None and str(kimlik) in all_saves_userid():
        uid = str(kimlik)
    if not uid or not gecerli_uid(str(uid)):
        return ({"result": "error"}, 404)
    kayit = kayit_oturumu(uid) if uid else None
    if not kayit:
        return ({"result": "error"}, 404)
    harita = kayit["maps"][0]
    pi = kayit.get("playerInfo", {})
    return jsonify({
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
    })


@app.route(DINAMIK + "/get_user_world.php", methods=["GET", "POST"])
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

def _istek_uid():
    uid = request.values.get("USERID", "")
    return uid if gecerli_uid(uid) else ""


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
        return jsonify({"result": "error"})
    return jsonify({
        "result": "ok",
        "tournament": turnuva,
        "tournaments": [turnuva],
        "data": turnuva,
        "tournamentId": turnuva.get("id"),
    })


def turnuva_create():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    veri = _turnuva_govde()
    turnuva = Turnuva.turnuva_olustur(uid, veri.get("type", "general"), veri.get("entryCost", 0))
    Turnuva.gunluge_yaz("create", {"uid": uid, "veri": veri, "id": (turnuva or {}).get("id")})
    return _turnuva_yanit(turnuva)


def turnuva_join():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    turnuva = Turnuva.turnuvaya_katil(tid, uid) if tid else None
    Turnuva.gunluge_yaz("join", {"uid": uid, "veri": veri})
    return _turnuva_yanit(turnuva)


def turnuva_start_match():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    sonuc = Turnuva.mac_baslat(tid, uid) if tid else None
    Turnuva.gunluge_yaz("start_match", {"uid": uid, "veri": veri, "sonuc": bool(sonuc)})
    if not sonuc:
        return {"result": "error"}
    return {"result": "ok", "match": sonuc["match"], "opponent": sonuc["opponent"], "data": sonuc}


def turnuva_finish_match():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    ham = veri.get("win", veri.get("kazandi", 0))
    kazandi = str(ham).strip().lower() in ("1", "true", "yes", "evet")
    turnuva = Turnuva.mac_bitir(tid, uid, kazandi) if tid else None
    Turnuva.gunluge_yaz("finish_match", {"uid": uid, "veri": veri, "kazandi": kazandi})
    return _turnuva_yanit(turnuva)


def turnuva_info():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    Turnuva.eski_turnuvalari_temizle()
    turnuva = Turnuva.bul_veya_olustur(uid) if uid else None
    if turnuva:
        return _turnuva_yanit(turnuva)
    return {"result": "ok", "tournament": None, "tournaments": Turnuva.turnuvalar(uid), "data": None}


def turnuva_cancel():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    turnuva = Turnuva.turnuva_iptal(tid, uid) if tid else None
    Turnuva.gunluge_yaz("cancel", {"uid": uid, "veri": veri})
    return _turnuva_yanit(turnuva)


def turnuva_leave():
    uid = _istek_uid()
    if not uid:
        return {"result": "error", "message": "gecersiz kullanici"}
    veri = _turnuva_govde()
    tid = veri.get("tournament_id") or veri.get("tournamentId") or veri.get("id")
    turnuva = Turnuva.turnuvadan_ayril(tid, uid) if tid else None
    Turnuva.gunluge_yaz("leave", {"uid": uid, "veri": veri})
    return _turnuva_yanit(turnuva)


def turnuva_clean():
    Turnuva.eski_turnuvalari_temizle()
    return {"result": "ok"}


def turnuva_admin_islem():
    Turnuva.gunluge_yaz("admin", dict(request.values))
    return {"result": "ok"}


@app.route(DINAMIK + "/tournaments/<path:ad>", methods=["GET", "POST"])
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
        "admin/finish_all_match_tournament.php": turnuva_admin_islem,
        "admin/reset_player_tournament.php": turnuva_admin_islem,
        "admin/add_player_tournament.php": turnuva_admin_islem,
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
        os.makedirs(SAVES_DIR, exist_ok=True)
        with open(os.path.join(SAVES_DIR, "http_gunlugu.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"yol": yol, "method": request.method, "args": request.values.to_dict()},
                ensure_ascii=False,
            ) + "\n")
    except OSError:
        pass
    print(f"[EKSIK UC] {request.method} /{yol} -> {dict(request.values)}")


@app.route(DINAMIK + "/<path:yol>", methods=["GET", "POST"])
def bilinmeyen_dinamik_uc(yol):
    _http_gunlugune_yaz(yol)
    return ("", 404)
