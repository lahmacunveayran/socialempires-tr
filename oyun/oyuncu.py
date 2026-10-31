"""İstemcinin oyuncu/komşu/görev haritası isteklerine verilen yanıtlar."""

import json
import os
import time

from oyun.ekonomi import timestamp_now
from oyun.kayit import session, neighbor_session, neighbors
from oyun.yollar import QUESTS_DIR


def _harita(kayit, map_number):
    haritalar = kayit["maps"]
    if not 0 <= map_number < len(haritalar):
        map_number = 0
    return haritalar[map_number]


# Oyuncunun en son açtığı kasaba (kasaba değiştirince istemci get_player_info'yu o kasabayla ister). Kasaba numarası
# taşımayan komutlar (buy_first_purchase) kaynağı buraya yazar. Kayda yazılmaz: açılışta istemci yeniden ister.
_acik_kasabalar = {}


def acik_kasaba(USERID) -> int:
    return _acik_kasabalar.get(str(USERID), 0)


def giris_gunu_say(kayit, ts_now):
    """numDayLogged: yeni bir takvim gününde ilk girişte bir artar (1.4.07'nin günlük sayacı, KYT-02)."""
    ps = kayit["privateState"]
    onceki = int(kayit["playerInfo"].get("last_logged_in", 0) or 0)
    if not isinstance(ps.get("numDayLogged"), int):
        ps["numDayLogged"] = 1
    elif 0 < onceki < ts_now and _gun(onceki) != _gun(ts_now):
        ps["numDayLogged"] += 1


def _gun(ts):
    """Yerel takvim günü; bozuk damgada (Windows'ta erimin dışı) None."""
    try:
        return time.localtime(ts)[:3]
    except (OSError, OverflowError, ValueError):
        return None


def get_player_info(USERID, map_number=0):
    kayit = session(USERID)
    ts_now = timestamp_now()
    giris_gunu_say(kayit, ts_now)
    kayit["playerInfo"]["last_logged_in"] = ts_now
    _acik_kasabalar[str(USERID)] = map_number if 0 <= map_number < len(kayit["maps"]) else 0
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
