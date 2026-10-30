"""Oyuncu kayıtları (saves/) ve statik komşu köyleri (villages/)."""

import copy
import json
import os
import random
import re
import shutil
import threading
import uuid

from werkzeug.utils import safe_join, secure_filename

from oyun import denge
from oyun.ekonomi import timestamp_now
from oyun.surum import migrate_loaded_save, version_code
from oyun.yollar import SAVES_DIR, VILLAGES_DIR, json_oku

# Sunucu çok iş parçacıklı çalıştığı için kayıt değiştiren işlemler bu
# kilit altında yapılır (aynı anda gelen komutlar birbirini ezmesin).
save_lock = threading.RLock()

# Eğitimdeki Arthur/Guinevere köyleri (komşu listesinde gösterilmez)
ARTHUR_KIMLIKLERI = ("100000030", "100000031", "100000032")

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

__initial_village = json_oku(os.path.join(VILLAGES_DIR, "initial.json"))

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
        village = json_oku(os.path.join(VILLAGES_DIR, file))
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
        yol = os.path.join(SAVES_DIR, file)
        # Tek bir bozuk kayıt (eski/elle düzenlenmiş yedek, yarım yazım) sunucunun açılmasını engellemesin:
        # okunamayan kayıt kenara alınır, varsa .bak'ı yerine konur (Android'de dosyayı silmenin yolu yok).
        try:
            save = _kaydi_ac(yol)
        except Exception as hata:
            print(f"Okunamadi ({type(hata).__name__}: {hata}).")
            save = _bozugu_kenara_al(yol)
            if save is None:
                continue
        USERID = save["playerInfo"]["pid"]
        try:
            map_name = save["playerInfo"]["map_names"][ save["playerInfo"]["default_map"] ]
        except:
            map_name = '?'
        print(f"({map_name}) Ok.")
        __saves[str(USERID)] = save
        if save.pop("_bak_kullanildi", False) or _yukleme_duzeltmeleri(save):
            save_session(USERID)


def _kaydi_ac(yol):
    return kaydi_dogrula(json_oku(yol))


def kaydi_dogrula(save):
    """Kaydın yüklenip oynanabileceğini dener (şema, sürüm göçü, ad, seviye); olmazsa ValueError.

    Göç bir kopyada denenir: yarıda patlarsa asıl kayıt yarım değişmiş olmaz. Yedekten yüklemede de kullanılır."""
    if not isinstance(save, dict) or not is_valid_village(save):
        raise ValueError("gecersiz kayit")
    try:
        deneme = copy.deepcopy(save)
        migrate_loaded_save(deneme)
        deneme["playerInfo"]["map_names"][deneme["playerInfo"].get("default_map", 0)]
        int(deneme["maps"][0]["level"])
    except Exception as hata:
        raise ValueError(f"kayit acilamiyor: {type(hata).__name__}: {hata}") from hata
    return save


def _bozugu_kenara_al(yol):
    """Okunamayan kaydı .bozuk olarak saklar; .bak okunabiliyorsa onu döndürür (kaydedilmek üzere)."""
    try:
        os.replace(yol, yol + ".bozuk")
    except OSError:
        pass
    try:
        save = _kaydi_ac(yol + ".bak")
    except Exception:
        print("   ! .bak da yok ya da okunamadi; kayit .bozuk olarak saklandi.")
        return None
    print("   > .bak'tan geri alindi.")
    save["_bak_kullanildi"] = True
    return save


def _yukleme_duzeltmeleri(save: dict) -> bool:
    modified = migrate_loaded_save(save)  # check save version for migration
    if _seviyeyi_duzelt(save):
        modified = True
    return modified


def _seviyeyi_duzelt(save: dict) -> bool:
    """Kayıttaki seviye, XP eşiğiyle uyuşmuyorsa düzeltir.

    Bozuk bir XP (ör. aşırı büyük değer) yüzünden seviye 0'da kalmış
    kayıtların oyunu kilitlemesini önler.
    """
    try:
        from oyun.config import get_level_from_xp
    except Exception:
        return False
    duzeltildi = False
    ps = save.setdefault("privateState", {})
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
    village["privateState"]["shield_until"] = timestamp_now() + denge.YENI_OYUNCU_KALKANI
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
    if empire_name == "My Empire":  # eski kayıtların İngilizce varsayılan adı (oyun içinde zaten Türkçe görünür)
        empire_name = "İmparatorluğum"
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
    friends = []
    # static villages
    for key in __villages:
        vill = __villages[key]
        # Avoid Arthur being loaded as friend.
        if vill["playerInfo"]["pid"] in ARTHUR_KIMLIKLERI:
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
        if vill["playerInfo"]["pid"] in ARTHUR_KIMLIKLERI:
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
    if not gecerli_uid(USERID) or secure_filename(str(USERID)) != str(USERID):
        print(f" ! Gecersiz USERID, kayit yazilmadi: {USERID!r}")
        return
    file = f"{USERID}.save.json"
    yol = safe_join(SAVES_DIR, file)
    if not yol:
        print(" ! Gecersiz kayit yolu")
        return
    gecici = yol + ".tmp"
    print(f" * Saving village at {file}... ", end='')

    with save_lock:
        village = session(USERID)
        try:
            with open(gecici, "w", encoding="utf-8") as f:
                # Girintisiz: dosya ~5 kat küçük; bot dünyası her dakika yazdığından tablette pil/depolama için önemli
                json.dump(village, f, ensure_ascii=False, separators=(",", ":"))
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(yol):
                try:
                    # Kopya (taşıma değil): iki adım arasında süreç ölürse canlı kayıt yine yerinde kalır
                    shutil.copyfile(yol, yol + ".bak")
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