"""İstemcinin oyun sunucusuna yaptığı istekler (dynamicUrl altındaki uçlar)."""

import hashlib
import hmac
import json
import os
import random
import traceback

from flask import jsonify, redirect, request

from oyun import ada as Ada
from oyun import turnuva as Turnuva
from oyun.config import get_client_game_config, get_game_config, kompu_teklifi
from oyun.ekonomi import timestamp_now
from oyun.kayit import (gecerli_uid, neighbor_session, save_lock, save_session,
                        session as kayit_oturumu)
from oyun.komutlar import command, depo_ekle, listeye_ekle
from oyun.oyuncu import get_neighbor_info, get_player_info, get_quest_map
from oyun.sunucu import OYUN_DILI, app
from oyun.yollar import SAVES_DIR

DINAMIK = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


# İstemcinin "servis" isteklerinde (kompu, hata bildirimi, turnuva) kullandığı
# HMAC-SHA256 anahtarı (istemcideki Config.SERVER_KEY). Yanıt imzasızsa
# istemci kompu yanıtlarını yok sayar.
SUNUCU_ANAHTARI = b"3m0d3pwiupoetn7ysa02"


def imzali(veri):
    govde = json.dumps(veri, separators=(",", ":"), ensure_ascii=False)
    imza = hmac.new(SUNUCU_ANAHTARI, govde.encode("utf-8"), hashlib.sha256).hexdigest()
    return app.response_class(f"{imza};{govde}", mimetype="text/plain")


def servis_govdesi():
    """`data` alanı: "<imza>;<json>" (hata ayıklamada yalnızca json)."""
    ham = request.values.get("data", "")
    if ";" in ham and not ham.lstrip().startswith("{"):
        ham = ham.split(";", 1)[1]
    try:
        return json.loads(ham) if ham else {}
    except json.JSONDecodeError:
        return {}


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
        kayit = kayit_oturumu(uid)
        if kayit is not None:
            with save_lock:
                kompu_donemini_guncelle(kayit)
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


# ---------------------------------------------------------------------------
# Büyücünün İksirleri (kompu): şans oyunu
# ---------------------------------------------------------------------------

KOMPU_SANSLARI = (1 / 30, 1 / 5, 1.0)  # çırak, kalfa, başbüyücü


def kompu_donemini_guncelle(kayit):
    """Yeni 30 günlük dönemde iksir sayacı sıfırlanır."""
    teklif = kompu_teklifi()
    ps = kayit["privateState"]
    if teklif and ps.get("kompuOfferId") != teklif["id"]:
        ps.update(kompuOfferId=teklif["id"], kompuSpells=0, kompuSteps=[], kompuLastTimeStamp=-1)


@app.route(DINAMIK + "/kompu_try.php", methods=["POST"])
def kompu_try_response():
    """{index, town} -> data: true (iksir tuttu) / false."""
    uid = request.values.get("USERID", "")
    kayit, teklif, veri = kayit_oturumu(uid), kompu_teklifi(), servis_govdesi()
    if kayit is None or teklif is None:
        return imzali({"result": "error"})
    indeks = max(0, min(2, int(veri.get("index", 0) or 0)))
    with save_lock:
        kompu_donemini_guncelle(kayit)
        ps = kayit["privateState"]
        bedel = (get_game_config()["globals"].get("KOMPU_WIZZARD_COSTS") or [{}, {}, {}])[indeks]
        harita = kayit["maps"][int(veri.get("town", 0) or 0) % len(kayit["maps"])]
        altin, cash = int(bedel.get("g", 0)), int(bedel.get("c", 0))
        son = int(ps.get("kompuLastTimeStamp", -1) or -1)
        # İstemci bunları zaten denetler; buraya gelmesi değiştirilmiş istemci demektir.
        if (int(harita.get("coins", 0)) < altin or int(kayit["playerInfo"].get("cash", 0)) < cash
                or teklif["id"] in ps.get("kompuCompleted", [])
                or (son > 0 and timestamp_now() - son < int(teklif["timer_between"]))):
            return imzali({"result": "error"})
        harita["coins"] = int(harita.get("coins", 0)) - altin
        kayit["playerInfo"]["cash"] = int(kayit["playerInfo"].get("cash", 0)) - cash
        ps["kompuLastTimeStamp"] = timestamp_now()
        basari = random.random() < KOMPU_SANSLARI[indeks]
        if basari:
            ps["kompuSpells"] = iksir = int(ps.get("kompuSpells", 0) or 0) + 1
            adimlar = ps.setdefault("kompuSteps", [])
            for odul in teklif["rewards"]:
                if int(odul["cost"]) == iksir and iksir not in adimlar:
                    adimlar.append(iksir)
                    depo_ekle(kayit, int(odul["unit"][0]))
            if iksir >= max(int(o["cost"]) for o in teklif["rewards"]):
                listeye_ekle(ps, "kompuCompleted", teklif["id"])
        save_session(uid)
    return imzali({"result": "success", "data": basari})


@app.route(DINAMIK + "/kompu_hurry_up.php", methods=["POST"])
def kompu_hurry_up_response():
    """Bekleme süresini cash ile atla."""
    uid = request.values.get("USERID", "")
    kayit, teklif = kayit_oturumu(uid), kompu_teklifi()
    if kayit is None or teklif is None:
        return imzali({"result": "error"})
    with save_lock:
        ps = kayit["privateState"]
        if int(kayit["playerInfo"].get("cash", 0)) < int(teklif["hurry_up_cost"]):
            return imzali({"result": "error"})
        kayit["playerInfo"]["cash"] = int(kayit["playerInfo"].get("cash", 0)) - int(teklif["hurry_up_cost"])
        ps["kompuLastTimeStamp"] = max(-1, int(ps.get("kompuLastTimeStamp", -1)) - int(teklif["timer_between"]))
        save_session(uid)
    return imzali({"result": "success", "data": True})


# ---------------------------------------------------------------------------
# Diğer servisler
# ---------------------------------------------------------------------------

@app.route(DINAMIK + "/register_found_item.php", methods=["POST"])
def register_found_item_response():
    """Kayıp hayvan/eşya bulundu (bina 91+tür haritadan kalkar). İmzasız istek."""
    uid = request.values.get("sender_id") or request.values.get("USERID", "")
    kayit = kayit_oturumu(uid)
    tur = int(request.values.get("item_id", 1) or 1)
    if kayit is not None:
        with save_lock:
            for harita in kayit["maps"]:
                esya = next((e for e in harita["items"] if e[0] == 91 + tur), None)
                if esya:
                    harita["items"].remove(esya)
                    break
            save_session(uid)
    return jsonify({"id": timestamp_now()})


@app.route(DINAMIK + "/report_error.php", methods=["POST"])
def report_error_response():
    """İstemci hatası: saves/istemci_hatalari.jsonl'a yazılır."""
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        with open(os.path.join(SAVES_DIR, "istemci_hatalari.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(servis_govdesi(), ensure_ascii=False) + "\n")
    except OSError:
        pass
    return imzali({"result": "success", "data": {}})


@app.route(DINAMIK + "/clean_assaults.php", methods=["POST"])
def clean_assaults_response():
    """İstemci aynı işi clean_attacks komutuyla yapar; uç yalnızca sessiz kalsın diye."""
    return imzali({"result": "success", "data": {}})


@app.route(DINAMIK + "/get_continent_ranking.php", methods=["GET", "POST"])
def get_continent_ranking_response():
    """Dünya haritası: [{posicion, user_id, name, level, race, pic}, ...], [0].nivel = kıta no."""
    uid = request.values.get("USERID", "")
    kayit = kayit_oturumu(uid)
    if kayit is None:
        return {"continent": []}
    if request.values.get("worldChange") == "1" or request.values.get("relocate") == "1":
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
    # Sonucu bilinen saldırılar (bot akınlarının kaydında sonuç yok)
    raporlar = [r for r in kayit["privateState"].get("attacksSent") or []
                if isinstance(r, dict) and isinstance(r.get("description"), dict)]
    kazanilan = sum(1 for r in raporlar if r["description"].get("win") in (1, "1"))
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


# ---------------------------------------------------------------------------
# Turnuvalar: istek "data" alanında imzalı JSON, yanıt {"data": {...}}
# ---------------------------------------------------------------------------

@app.route(DINAMIK + "/tournaments/<path:ad>", methods=["GET", "POST"])
def turnuva_ucu(ad):
    veri = servis_govdesi()
    uid = str(veri.get("user_id") or request.values.get("USERID", ""))
    if not gecerli_uid(uid):
        return imzali({"data": {"result": "NOK"}})
    if ad == "get_tournament_info.php":
        sonuc = Turnuva.bilgi(uid)
    elif ad in ("create_tournament.php", "join_tournament.php"):
        sonuc = Turnuva.katil(uid, veri.get("tournament_type_id", 1), veri.get("team"))
    elif ad == "start_tournament_match.php":
        sonuc = Turnuva.mac_baslat(uid, veri.get("victim_id"))
    elif ad == "finish_tournament_match.php":
        sonuc = Turnuva.mac_bitir(uid, veri.get("victim_id"),
                                  str(veri.get("attacker_won")).lower() in ("true", "1"),
                                  veri.get("attacker_points"))
    elif ad in ("cancel_tournament.php", "leave_tournament.php"):
        sonuc = Turnuva.ayril(uid)
    elif ad == "clean_tournament.php":
        sonuc = Turnuva.temizle(uid)
    elif ad.startswith("admin/"):
        sonuc = {"result": "OK"}  # yalnızca geliştirici panelinden
    else:
        _http_gunlugune_yaz("tournaments/" + ad)
        return ("", 404)
    return imzali({"data": sonuc})


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
