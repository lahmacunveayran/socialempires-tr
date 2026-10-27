# -*- coding: utf-8 -*-
"""PvP için yapay komşu köyleri üretir.

Her bot `saves/<uuid>.save.json` olarak kaydedilir ve `playerInfo.bot`
ile işaretlenir. `world.py` bu köyleri yaşayan dünya simülasyonuna dahil
eder: ekonomi, birlik üretimi, akınlar ve savunma.

Kullanım:
    python tools\\bot_koy_uret.py [adet]      (varsayılan 50)
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

# 50 farklı isim
ISIMLER = [
    "Kara Han", "Bozkurt Bey", "Demir Yay", "Gökbörü", "Alp Er Tunga",
    "Kül Tigin", "Bilge Kağan", "Tomris Hatun", "Modu Han", "Attila",
    "Balamir", "İlteriş", "Kapgan", "Suyab", "Tardu",
    "Bayan Kağan", "İstemi Yabgu", "Bilge Hatun", "Kür Şad", "Tonyukuk",
    "Vezir Nizam", "Şahin Bey", "Korkut Ata", "Dede Korkut", "Manas",
    "Cengiz Han", "Kubilay", "Timur", "Babür", "Alparslan",
    "Tuğrul Bey", "Melikşah", "Sultan Sencer", "Harzemşah", "Celaleddin",
    "Ertuğrul", "Osman Bey", "Orhan Bey", "Murat Bey", "Yıldırım",
    "Fatih", "Yavuz", "Kanuni", "Sokullu", "Kılıç Arslan",
    "Nurettin", "Selahaddin", "Baybars", "Kutuz", "Berke Han",
]

KISILIKLER = ["agresif", "savunmaci", "tuccar", "dengeli"]

# Birim havuzları (kişiliğe göre)
BIRIMLER = {
    "agresif": [512, 512, 512, 517, 518],
    "savunmaci": [516, 516, 517, 518, 512],
    "tuccar": [516, 517, 512, 516, 517],
    "dengeli": [512, 516, 517, 518],
}


def _sec(tablo, seviye):
    anahtar = 1 if seviye < 12 else 2 if seviye < 30 else 3
    return tablo[anahtar]


def _yerlesim(seviye, simdi, kisi, rastgele):
    """Bot köyünün eşya listesini üretir; kişiliğe göre savunma dağılımı."""
    esyalar = []
    dolu = set()

    def koy(esya_id, x, y):
        if (x, y) in dolu:
            return False
        dolu.add((x, y))
        esyalar.append([esya_id, x, y, 0, simdi, 0, [], {}])
        return True

    def bos_yer(alt=38, ust=62):
        for _ in range(60):
            x, y = rastgele.randint(alt, ust), rastgele.randint(alt, ust)
            if (x, y) not in dolu:
                return x, y
        return None

    # Belediye binası
    belediye = 26 if seviye < 18 else 139 if seviye < 32 else 140 if seviye < 46 else 141
    koy(belediye, 50, 50)

    # Evler (seviyeye göre 3-7)
    ev_ids = [1, 2, 3, 4, 194]
    ev = ev_ids[min(len(ev_ids) - 1, seviye // 14)]
    for _ in range(rastgele.randint(3, 7)):
        yer = bos_yer()
        if yer:
            koy(ev, *yer)

    # Kaynak binaları
    mill = _sec({1: 5, 2: 6, 3: 7}, seviye)
    for _ in range(rastgele.randint(2, 4)):
        yer = bos_yer()
        if yer:
            koy(mill, *yer)
    for _ in range(rastgele.randint(2, 4)):
        yer = bos_yer()
        if yer:
            koy(10, *yer)  # Farm Land

    # Kışla
    kisla = _sec({1: 38, 2: 39, 3: 40}, seviye)
    for _ in range(2 if kisi == "agresif" else 1):
        yer = bos_yer()
        if yer:
            koy(kisla, *yer)

    # Kuleler (savunmacı daha çok)
    kule = _sec({1: 29, 2: 30, 3: 31}, seviye)
    kule_sayisi = rastgele.randint(2, 4) + (2 if kisi == "savunmaci" else 0)
    for _ in range(kule_sayisi):
        yer = bos_yer(36, 64)
        if yer:
            koy(kule, *yer)

    # Surlar (seviye 8+)
    if seviye >= 8:
        sur = 34 if seviye < 20 else 35 if seviye < 36 else 36
        for x in range(34, 67):
            koy(sur, x, 33)
            koy(sur, x, 67)
        for y in range(35, 66):
            koy(sur, 33, y)
            koy(sur, 67, y)
        koy(37, 50, 67)  # kapı

    # Dekor (birkaç heykel)
    for _ in range(rastgele.randint(0, 2)):
        yer = bos_yer()
        if yer:
            koy(122, *yer)

    # Savunma birlikleri
    havuz = BIRIMLER.get(kisi, BIRIMLER["dengeli"])
    adet = min(6 + seviye + rastgele.randint(0, 8), 70)
    for _ in range(adet):
        yer = bos_yer(38, 62)
        if yer:
            koy(rastgele.choice(havuz), *yer)

    return esyalar


def mevcut_botlari_sil():
    """Daha önce üretilmiş bot kayıtlarını siler (oyuncu kaydına dokunmaz)."""
    silinen = 0
    if not os.path.exists(SAVES_DIR):
        return 0
    for dosya in os.listdir(SAVES_DIR):
        if not dosya.endswith(".save.json"):
            continue
        yol = os.path.join(SAVES_DIR, dosya)
        try:
            with open(yol, encoding="utf-8") as f:
                kayit = json.load(f)
        except (ValueError, OSError):
            continue
        if kayit.get("playerInfo", {}).get("bot"):
            try:
                os.remove(yol)
                if os.path.exists(yol + ".bak"):
                    os.remove(yol + ".bak")
                silinen += 1
            except OSError:
                pass
    return silinen


def bot_uret(adet=50):
    with open(os.path.join(VILLAGES_DIR, "initial.json"), encoding="utf-8") as f:
        sablon = json.load(f)
    with open(os.path.join(KOK, "config", "game_config_20120826.json"), encoding="utf-8") as f:
        seviyeler = json.load(f)["levels"]

    os.makedirs(SAVES_DIR, exist_ok=True)
    eski = mevcut_botlari_sil()
    if eski:
        print(f" * {eski} eski bot kaydi silindi")

    rastgele = random.Random(20261027)
    simdi = int(time.time())

    adet = max(1, min(adet, len(ISIMLER)))
    for i in range(adet):
        isim = ISIMLER[i]
        kisi = KISILIKLER[i % len(KISILIKLER)]
        seviye = min(60, 3 + int(i * 1.15))
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
            "bot_kisi": kisi,
        })
        pi["map_names"] = [f"{isim} Kalesi"]
        pi["map_sizes"] = [0]

        harita = kayit["maps"][0]
        harita["level"] = seviye
        onceki = max(0, seviye - 1)
        harita["xp"] = int(seviyeler[onceki]["exp_required"]) + 1 if seviye > 0 else 0
        harita["coins"] = 300 * seviye
        harita["wood"] = 450 * seviye
        harita["stone"] = 350 * seviye
        harita["food"] = 400 * seviye
        harita["timestamp"] = simdi
        harita["expansions"] = [13]
        harita["resourcesTraded"] = {}
        harita["items"] = _yerlesim(seviye, simdi, kisi, rastgele)

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

    print(f"[+] {adet} bot koy uretildi: {SAVES_DIR}")


if __name__ == "__main__":
    adet = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    bot_uret(adet)
