"""İstemcinin oyuncu/komşu/görev haritası isteklerine verilen yanıtlar."""

import json
import os

from oyun.ekonomi import timestamp_now
from oyun.kayit import session, neighbor_session, neighbors
from oyun.yollar import QUESTS_DIR


def _harita(kayit, map_number):
    haritalar = kayit["maps"]
    if not 0 <= map_number < len(haritalar):
        map_number = 0
    return haritalar[map_number]


def get_player_info(USERID, map_number=0):
    kayit = session(USERID)
    ts_now = timestamp_now()
    kayit["playerInfo"]["last_logged_in"] = ts_now
    return {
        "result": "ok",
        "processed_errors": 0,
        "timestamp": ts_now,
        "playerInfo": kayit["playerInfo"],
        "map": _harita(kayit, map_number),
        "privateState": kayit["privateState"],
        "neighbors": neighbors(USERID),
    }


def get_neighbor_info(userid, map_number):
    komsu = neighbor_session(userid)
    if komsu is None:
        # Silinmiş/bilinmeyen komşu: sunucu 500 vermesin.
        return {"result": "error", "processed_errors": 0, "timestamp": timestamp_now()}
    return {
        "result": "ok",
        "processed_errors": 0,
        "timestamp": timestamp_now(),
        "playerInfo": komsu["playerInfo"],
        "map": _harita(komsu, map_number),
        "privateState": komsu["privateState"],
        "neighbors": neighbors(userid),
    }


def get_quest_map(questid):
    try:
        questid = int(questid)
    except (TypeError, ValueError):
        return ("", 404)
    dosya = os.path.join(QUESTS_DIR, f"{questid}.json")
    if not os.path.exists(dosya):
        return ("", 404)
    with open(dosya, encoding="utf-8") as f:
        return (json.load(f), 200)
