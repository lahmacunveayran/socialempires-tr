# -*- coding: utf-8 -*-
"""PvP için yapay komşu köyleri üretir.

Her bot, `saves/<uuid>.save.json` olarak kaydedilir; sunucu açılışında
bunları normal oyuncu kaydı gibi yükler. Böylece PvP listesinde ve kıta
sıralamasında görünürler, saldırılabilirler.

Kullanım:
    python tools\\bot_koy_uret.py [adet]
"""

import copy
import json
import os
import random
import sys
import time
import uuid

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from bundle import SAVES_DIR, VILLAGES_DIR  # noqa: E402
from version import version_code  # noqa: E402

ISIMLER = [
    "Kara Han", "Bozkurt Bey", "Demir Yay", "Gökbörü", "Alp Er Tunga",
    "Kül Tigin", "Bilge Kağan", "Tomris Hatun", "Modu Han", "Attila",
    "Balamir", "İlteriş", "Kapgan", "Suyab", "Tardu",
]

# Seviyeye göre bina seçimleri
EV = {  # evler
    1: 1, 2: 2, 3: 3,
}
MILL = {1: 5, 2: 6, 3: 7}
TOWER = {1: 29, 2: 30, 3: 31, 4: 32}
BARRACKS = {1: 38, 2: 39, 3: 40}


def _sec(tablo, seviye):
    anahtar = 1 if seviye < 10 else 2 if seviye < 25 else 3
    return tablo[anahtar]


def _yerlesim(seviye, simdi):
    """Bot köyünün eşya listesini üretir."""
    esyalar = []
    dolu = set()

    def koy(esya_id, x, y, birim=False):
        if (x, y) in dolu:
            return False
        dolu.add((x, y))
        esyalar.append([esya_id, x, y, 0, simdi, 0, [], {}])
        return True

    # Kale / belediye binası
    belediye = 26 if seviye < 20 else 139 if seviye < 35 else 140
    koy(belediye, 50, 50)

    # Evler
    ev = _sec(EV, seviye)
    for x, y in ((40, 40), (40, 44), (44, 40), (44, 44), (56, 56), (60, 60)):
        koy(ev, x, y)

    # Değirmenler ve tarlalar
    mill = _sec(MILL, seviye)
    for x, y in ((56, 40), (60, 44)):
        koy(mill, x, y)
    for x, y in ((40, 56), (44, 60)):
        koy(10, x, y)

    # Kışla
    kisla = _sec(BARRACKS, seviye)
    koy(kisla, 56, 48)

    # Kuleler
    kule = _sec(TOWER, seviye)
    for x, y in ((36, 36), (64, 36), (36, 64), (64, 64)):
        koy(kule, x, y)

    # Surlar (çevre)
    sur = 35 if seviye < 25 else 36
    for x in range(36, 65):
        koy(sur, x, 34)
        koy(sur, x, 66)
    for y in range(36, 65):
        koy(sur, 34, y)
        koy(sur, 66, y)
    koy(37, 50, 66)  # kapı

    # Savunma birimleri (seviyeye göre artar)
    birimler = [512, 516, 517, 518]
    adet = min(4 + seviye, 60)
    for i in range(adet):
        for _deneme in range(40):
            x = random.randint(38, 62)
            y = random.randint(38, 62)
            if (x, y) not in dolu:
                koy(random.choice(birimler), x, y, birim=True)
                break

    return esyalar


def bot_uret(adet=10):
    with open(os.path.join(VILLAGES_DIR, "initial.json"), encoding="utf-8") as f:
        sablon = json.load(f)
    with open(os.path.join(KOK, "config", "game_config_20120826.json"), encoding="utf-8") as f:
        seviyeler = json.load(f)["levels"]

    os.makedirs(SAVES_DIR, exist_ok=True)
    rastgele = random.Random(1234)
    simdi = int(time.time())

    uretilen = 0
    for i in range(min(adet, len(ISIMLER))):
        isim = ISIMLER[i]
        seviye = [5, 8, 12, 16, 20, 25, 30, 35, 40, 45][i % 10]
        pid = str(uuid.uuid4())

        kayit = copy.deepcopy(sablon)
        kayit["version"] = version_code

        pi = kayit["playerInfo"]
        pi.update({
            "pid": pid,
            "name": isim,
            "pic": "/img/profile/1025.png",
            "cash": 0,
            "completed_tutorial": 1,
            "default_map": 0,
            "world_id": 0,
            "last_logged_in": 0,
            "sp_ref_uid": pid,
            "bot": True,
        })
        pi["map_names"] = [f"{isim} Kalesi"]
        pi["map_sizes"] = [0]

        harita = kayit["maps"][0]
        harita["level"] = seviye
        # get_level_from_xp eşik değerinde bir üst seviyeyi döndürdüğü için
        # bir önceki eşiğin 1 fazlasını yazıyoruz; seviye tam kalıyor.
        onceki = max(0, seviye - 1)
        harita["xp"] = int(seviyeler[onceki]["exp_required"]) + 1 if seviye > 0 else 0
        harita["coins"] = 250 * seviye
        harita["wood"] = 400 * seviye
        harita["stone"] = 300 * seviye
        harita["food"] = 400 * seviye
        harita["timestamp"] = simdi
        harita["expansions"] = [13]
        harita["resourcesTraded"] = {}
        harita["items"] = _yerlesim(seviye, simdi)

        ps = kayit["privateState"]
        ps["attacksSent"] = []
        ps["attacksReceived"] = []
        ps["teams"] = {"tournament": None}
        ps["completedMissions"] = []
        ps["rewardedMissions"] = []
        ps["gifts"] = []
        ps["unlockedQuestIndex"] = 0

        yol = os.path.join(SAVES_DIR, f"{pid}.save.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(kayit, f, indent=4, ensure_ascii=False)
        uretilen += 1
        print(f" * {isim:<15} seviye {seviye:>2} -> {pid}.save.json")

    print(f"[+] {uretilen} bot koy uretildi: {SAVES_DIR}")


if __name__ == "__main__":
    adet = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    bot_uret(adet)
