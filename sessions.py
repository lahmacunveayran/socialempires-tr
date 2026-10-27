import json
import os
import re
import copy
import threading
import uuid
import random
from flask import session
# from flask_session import SqlAlchemySessionInterface, current_app

from version import version_code
from engine import timestamp_now
from version import migrate_loaded_save
from constants import Constant

from bundle import VILLAGES_DIR, SAVES_DIR

# Sunucu çok iş parçacıklı çalıştığı için kayıt değiştiren işlemler bu
# kilit altında yapılır (aynı anda gelen komutlar birbirini ezmesin).
save_lock = threading.RLock()

__villages = {}  # ALL static neighbors
'''__villages = {
    "USERID_1": {
        "playerInfo": {...},
        "maps": [{...},{...}]
        "privateState": {...}
    },
    "USERID_2": {...}
}'''

__saves = {}  # ALL saved villages
'''__saves = {
    "USERID_1": {
        "playerInfo": {...},
        "maps": [{...},{...}]
        "privateState": {...}
    },
    "USERID_2": {...}
}'''

__initial_village = json.load(open(os.path.join(VILLAGES_DIR, "initial.json"), encoding="utf-8"))

# Load saved villages

def load_saved_villages():
    """Kayıtları diskten yeniden yükler (kilit altında)."""
    with save_lock:
        _load_saved_villages()


def _load_saved_villages():
    global __villages
    global __saves
    # Empty in memory
    __villages = {}
    __saves = {}
    # Saves dir check
    if not os.path.exists(SAVES_DIR):
        try:
            print(f"Creating '{SAVES_DIR}' folder...")
            os.mkdir(SAVES_DIR)
        except:
            print(f"Could not create '{SAVES_DIR}' folder.")
            exit(1)
    if not os.path.isdir(SAVES_DIR):
        print(f"'{SAVES_DIR}' is not a folder... Move the file somewhere else.")
        exit(1)
    # Static neighbors in /villages
    for file in os.listdir(VILLAGES_DIR):
        if file == "initial.json" or not file.endswith(".json"):
            continue
        print(f" * Loading static neighbour {file}... ", end='')
        village = json.load(open(os.path.join(VILLAGES_DIR, file), encoding="utf-8"))
        if not is_valid_village(village):
            print("Invalid neighbour")
            continue
        USERID = village["playerInfo"]["pid"]
        if str(USERID) in __villages:
            print(f"Ignored: duplicated PID '{USERID}'.")
        else:
            __villages[str(USERID)] = village
            print("Ok.")
    # Saves in /saves
    for file in os.listdir(SAVES_DIR):
        if not file.endswith(".save.json"):
            continue
        print(f" * Loading save at {file}... ", end='')
        try:
            save = json.load(open(os.path.join(SAVES_DIR, file), encoding="utf-8"))
        except json.decoder.JSONDecodeError as e:
            print("Corrupted JSON.")
            continue
        if not is_valid_village(save):
            print("Invalid Save.")
            continue
        USERID = save["playerInfo"]["pid"]
        try:
            map_name = save["playerInfo"]["map_names"][ save["playerInfo"]["default_map"] ]
        except:
            map_name = '?'
        print(f"({map_name}) Ok.")
        __saves[str(USERID)] = save
        modified = migrate_loaded_save(save) # check save version for migration
        if _seviyeyi_duzelt(save):
            modified = True
        if modified:
            save_session(USERID)


def _seviyeyi_duzelt(save: dict) -> bool:
    """Kayıttaki seviye, XP eşiğiyle uyuşmuyorsa düzeltir.

    Bozuk bir XP (ör. aşırı büyük değer) yüzünden seviye 0'da kalmış
    kayıtların oyunu kilitlemesini önler.
    """
    try:
        from get_game_config import get_level_from_xp
    except Exception:
        return False
    duzeltildi = False
    ps = save.setdefault("privateState", {})
    if "trophies" not in ps:
        ps["trophies"] = 0
        duzeltildi = True
    for harita in save.get("maps", []):
        try:
            beklenen = get_level_from_xp(int(harita.get("xp", 0)))
        except (TypeError, ValueError):
            continue
        if harita.get("level") != beklenen:
            print(f"   > seviye duzeltildi: {harita.get('level')} -> {beklenen}")
            harita["level"] = beklenen
            duzeltildi = True
    return duzeltildi
    

# New village

def new_village() -> str:
    # Generate USERID
    USERID: str = str(uuid.uuid4())
    assert USERID not in all_userid()
    # Copy init
    village = copy.deepcopy(__initial_village)
    # Custom values
    village["version"] = version_code
    village["playerInfo"]["pid"] = USERID
    village["maps"][0]["timestamp"] = timestamp_now()
    village["privateState"]["dartsRandomSeed"] = abs(int((2**16 - 1) * random.random()))
    # Memory saves
    __saves[USERID] = village
    # Generate save file
    save_session(USERID)
    print("Done.")
    return USERID

# Access functions

def all_saves_userid() -> list:
    "Returns a list of the USERID of every saved village."
    return list(__saves.keys())

def all_userid() -> list:
    "Returns a list of the USERID of every village."
    return list(__villages.keys()) + list(__saves.keys())

def save_info(USERID: str) -> dict:
    save = __saves[USERID]
    default_map = save["playerInfo"]["default_map"]
    empire_name = str(save["playerInfo"]["map_names"][default_map])
    xp = save["maps"][default_map]["xp"]
    level = save["maps"][default_map]["level"]
    return{"userid": USERID, "name": empire_name, "xp": xp, "level": level}

def all_saves_info() -> list:
    saves_info = []
    for userid in __saves:
        saves_info.append(save_info(userid))
    return list(saves_info)

def session(USERID: str) -> dict:
    assert(isinstance(USERID, str))
    return __saves[USERID] if USERID in __saves else None

def neighbor_session(USERID: str) -> dict:
    assert(isinstance(USERID, str))
    if USERID in __saves:
        return __saves[USERID]
    if USERID in __villages:
        return __villages[USERID]

def fb_friends_str(USERID: str) -> list:
    DELETE_ME = [{"uid": "1111", "pic_square":"http://127.0.0.1:5050/img/profile/Paladin_Justiciero.jpg"},
        {"uid": "aa_002", "pic_square":"/1025.png"}]
    friends = []
    # static villages
    for key in __villages:
        vill = __villages[key]
        # Avoid Arthur being loaded as friend.
        if vill["playerInfo"]["pid"] == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_1 \
        or vill["playerInfo"]["pid"] == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_2 \
        or vill["playerInfo"]["pid"] == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_3:
            continue
        frie = {}
        frie["uid"] = vill["playerInfo"]["pid"]
        frie["pic_square"] = vill["playerInfo"]["pic"]
        if not frie["pic_square"]: frie["pic_square"] = "/img/profile/1025.png"
        friends += [frie]
    # other players
    for key in __saves:
        vill = __saves[key]
        if vill["playerInfo"]["pid"] == USERID:
            continue
        frie = {}
        frie["uid"] = vill["playerInfo"]["pid"]
        frie["pic_square"] = vill["playerInfo"]["pic"]
        if not frie["pic_square"]: frie["pic_square"] = "/img/profile/1025.png"
        friends += [frie]
    return friends

def neighbors(USERID: str) -> list:
    neighbors = []
    # static villages
    for key in __villages:
        vill = __villages[key]
        # Avoid Arthur being loaded as multiple neigtbors.
        if vill["playerInfo"]["pid"] == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_1 \
        or vill["playerInfo"]["pid"] == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_2 \
        or vill["playerInfo"]["pid"] == Constant.NEIGHBOUR_ARTHUR_GUINEVERE_3:
            continue
        neigh = vill["playerInfo"]
        neigh["coins"] = vill["maps"][0]["coins"]
        neigh["xp"] = vill["maps"][0]["xp"]
        neigh["level"] = vill["maps"][0]["level"]
        neigh["stone"] = vill["maps"][0]["stone"]
        neigh["wood"] = vill["maps"][0]["wood"]
        neigh["food"] = vill["maps"][0]["food"]
        neigh["stone"] = vill["maps"][0]["stone"]
        neighbors += [neigh]
    # other players
    for key in __saves:
        vill = __saves[key]
        if vill["playerInfo"]["pid"] == USERID:
            continue
        neigh = vill["playerInfo"]
        neigh["coins"] = vill["maps"][0]["coins"]
        neigh["xp"] = vill["maps"][0]["xp"]
        neigh["level"] = vill["maps"][0]["level"]
        neigh["stone"] = vill["maps"][0]["stone"]
        neigh["wood"] = vill["maps"][0]["wood"]
        neigh["food"] = vill["maps"][0]["food"]
        neigh["stone"] = vill["maps"][0]["stone"]
        neighbors += [neigh]
    return neighbors

# Check for valid village
# The reason why this was implemented is to warn the user if a save game from Social Wars was used by accident

def is_valid_village(save: dict):
    if "playerInfo" not in save or "maps" not in save or "privateState" not in save:
        # These are obvious
        return False
    for map in save["maps"]:
        if "oil" in map or "steel" in map:
            return False
        if "stone" not in map or "food" not in map:
            return False
        if "items" not in map:
            return False
        if type(map["items"]) != list:
            return False

    return True

# Persistency

BACKUP_DIR = os.path.join(SAVES_DIR, "backups")
MAX_BACKUPS = 10


def backup_session(USERID: str):
    """Kayıt dosyasının zaman damgalı bir kopyasını backups/ altına alır."""
    kaynak = os.path.join(SAVES_DIR, f"{USERID}.save.json")
    if not os.path.exists(kaynak):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    hedef = os.path.join(BACKUP_DIR, f"{USERID}-{timestamp_now()}.save.json")
    try:
        with open(kaynak, "rb") as f:
            veri = f.read()
        with open(hedef, "wb") as f:
            f.write(veri)
        _eski_yedekleri_temizle(USERID)
    except OSError as hata:
        print(f" ! Yedek alinamadi ({hedef}): {hata}")
        return None
    return hedef


def _eski_yedekleri_temizle(USERID: str):
    """Aynı oyuncuya ait en fazla MAX_BACKUPS yedeği tutar."""
    try:
        dosyalar = [
            os.path.join(BACKUP_DIR, d)
            for d in os.listdir(BACKUP_DIR)
            if d.startswith(f"{USERID}-") and d.endswith(".save.json")
        ]
    except OSError:
        return
    dosyalar.sort(key=os.path.getmtime, reverse=True)
    for eski in dosyalar[MAX_BACKUPS:]:
        try:
            os.remove(eski)
        except OSError:
            pass


def gecerli_uid(USERID: str) -> bool:
    """Dosya yoluna yazılabilecek güvenli kimlik mi? (path traversal engeli)"""
    uid = str(USERID or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", uid):
        return False
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", uid):
        return False
    return True


def save_session(USERID: str):
    """Kaydı atomik olarak yazar: önce .tmp, sonra yerine taşır.

    Yazma sırasında oyun çökerse eski kayıt bozulmadan kalır; başarılı her
    yazımdan önce bir önceki sürüm .bak olarak saklanır.
    """
    if not gecerli_uid(USERID):
        print(f" ! Gecersiz USERID, kayit yazilmadi: {USERID!r}")
        return
    file = f"{USERID}.save.json"
    yol = os.path.join(SAVES_DIR, file)
    gecici = yol + ".tmp"
    print(f" * Saving village at {file}... ", end='')

    with save_lock:
        village = session(USERID)
        try:
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(village, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(yol):
                try:
                    os.replace(yol, yol + ".bak")
                except OSError:
                    pass  # yedek alınamasa da asıl kayıt yazılsın

            os.replace(gecici, yol)
        except OSError as hata:
            print(f"HATA: {hata}")
            try:
                if os.path.exists(gecici):
                    os.remove(gecici)
            except OSError:
                pass
            raise
    print("Done.")