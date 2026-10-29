"""İstemcinin oyun sunucusuna yaptığı istekler (dynamicUrl altındaki uçlar)."""

import json
import os
import traceback

from flask import jsonify, redirect, request

from oyun import ada as Ada
from oyun import turnuva as Turnuva
from oyun.config import get_client_game_config
from oyun.kayit import (gecerli_uid, neighbor_session, save_lock, save_session,
                        session as kayit_oturumu)
from oyun.komutlar import command
from oyun.oyuncu import get_neighbor_info, get_player_info, get_quest_map
from oyun.sunucu import OYUN_DILI, app
from oyun.yollar import SAVES_DIR

DINAMIK = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


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
    """Dünya haritası: [{posicion, user_id, name, level, race, pic}, ...], [0].nivel = kıta no."""
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid)
    if kayit is None:
        return {"continent": []}
    with save_lock:
        if request.values.get("worldChange") == "1":
            Ada.sonraki_kita(kayit)
        if request.values.get("relocate") == "1":
            Ada.yer_degistir(kayit)
        save_session(uid)
    kita = int(request.values.get("level_id") or 0) or None
    return {"world_id": Ada.dunya_kimligi(kayit), "continent": Ada.kita_listesi(kayit, kita)}


@app.route(DINAMIK + "/get_public_player_info.php", methods=["GET", "POST"])
def get_public_player_info_response():
    """Oyuncu profili penceresi; USERID burada bakılan oyuncudur."""
    kayit = neighbor_session(request.values.get("USERID", ""))
    if kayit is None:
        return {}
    pi = kayit["playerInfo"]
    raporlar = [r for r in kayit["privateState"].get("attacksSent") or [] if isinstance(r, dict)]
    kazanilan = sum(1 for r in raporlar if (r.get("description") or {}).get("win") in (1, "1"))
    return {
        "pid": str(pi.get("pid", "")),
        "name": pi.get("name", ""),
        "level": int(kayit["maps"][0].get("level", 1)),
        "map_names": pi.get("map_names") or [pi.get("name", "")],
        "honor_points": int(pi.get("honor_points", 0) or 0),
        "country": pi.get("country", "TR"),
        "last_logged_in": int(pi.get("last_logged_in", 0) or 0),
        "attacks_won": kazanilan,
        "attacks_lost": len(raporlar) - kazanilan,
    }


@app.route(DINAMIK + "/get_user_world.php", methods=["GET", "POST"])
def get_user_world_response():
    kayit = kayit_oturumu(request.values.get("USERID", ""))
    return {"result": {"world_id": Ada.dunya_kimligi(kayit) if kayit else 0}}


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
