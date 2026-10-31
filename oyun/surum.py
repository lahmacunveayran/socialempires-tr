import json
import os
import random

from oyun.ekonomi import timestamp_now
from oyun.kayit_semasi import eksikleri_tamamla
from oyun.yollar import CONFIG_DIR

version_name = "alpha 0.08"
version_code = "0.08a"

# 1.4.07'den önceki sürümler: bu kayıtlardaki görev numaraları 0926 istemcisinin numaralarıdır.
ESKI_ISTEMCI_SURUMLERI = ("0.01a", "0.02a", "0.03a", "0.04a", "0.05a")
_GOREV_TABLOSU = None


def gorev_tablosu() -> dict:
    """Eski görev numarası → 1.4.07 hedef numarası (config/gorev_gocu.json, araclar/gorev_gocu.py üretir)."""
    global _GOREV_TABLOSU
    if _GOREV_TABLOSU is None:
        with open(os.path.join(CONFIG_DIR, "gorev_gocu.json"), encoding="utf-8") as f:
            _GOREV_TABLOSU = {int(k): int(v) for k, v in json.load(f)["tablo"].items()}
    return _GOREV_TABLOSU


def gorev_numaralarini_cevir(ps: dict, eski_numaralar=None) -> bool:
    """completedMissions ve rewardedMissions'taki eski numaraları 1.4.07 numaralarına çevirir (GOR-01).

    `eski_numaralar` verilirse yalnızca onlar eski sayılır; ötekiler 1.4.07'de kazanılmıştır, dokunulmaz.
    None ise hepsi eskidir. Karşılığı olmayan eski numara düşer: aynı numaralı yeni hedef başka bir iştir,
    oyuncu onu kendisi yapar.
    """
    tablo = gorev_tablosu()
    degisti = False
    for alan in ("completedMissions", "rewardedMissions"):
        liste = ps.get(alan)
        if not isinstance(liste, list):
            continue
        yeni = []
        for numara in liste:
            eski = isinstance(numara, int) and (eski_numaralar is None or numara in eski_numaralar)
            hedef = tablo.get(numara) if eski else numara
            if hedef is not None and hedef not in yeni:
                yeni.append(hedef)
        if yeni != liste:
            ps[alan] = yeni
            degisti = True
    return degisti


def migrate_loaded_save(save: dict, eski_gorevler=None) -> bool:
    """Kaydı bu sürüme getirir.

    `eski_gorevler`: 0.06a'daki bir kayıtta hâlâ eski numaralı olan görevler (göç öncesi yedekten okunur,
    bkz. kayit.eski_gorev_numaralari). 0.06a'dan eski kayıtta bütün numaralar eskidir, bu değer kullanılmaz.
    """

    # discard current version saves
    if save.get("version") == version_code:
        return False

    eski_istemci = save.get("version") in ESKI_ISTEMCI_SURUMLERI or save.get("version") is None
    
    # fix 0.01a saves
    if "version" not in save or save["version"] is None:
        save["version"] = "0.01a"
    
    # 0.01a -> 0.02a
    if save["version"] == "0.01a":
        save["maps"][0]["timestamp"] = timestamp_now()
        save["privateState"]["dartsRandomSeed"] = abs(int((2**16 - 1) * random.random()))
        save["version"] = "0.02a"
        print("   > migrated to 0.02a")
    
    # 0.02a -> 0.03a
    if save["version"] == "0.02a":
        if "arrayAnimals" not in save["privateState"]:
            save["privateState"]["arrayAnimals"] = {} # fix no animal spawning
        if "strategy" not in save["privateState"]:
            save["privateState"]["strategy"] = 8 # fix crash when attacking a player
        if "universAttackWin" not in save["maps"][0]:
            save["maps"][0]["universAttackWin"] = [] # pvp current island progress
        if "questTimes" not in save["maps"][0]:
            save["maps"][0]["questTimes"] = [] # quests
        if "lastQuestTimes" not in save["maps"][0]:
            save["maps"][0]["lastQuestTimes"] = [] # 1.1.5 quests
        save["version"] = "0.03a"
        print("   > migrated to 0.03a")
    
    # 0.03a -> 0.04a
    if save["version"] == "0.03a":
        if "pic" not in save["playerInfo"].keys():
            save["playerInfo"]["pic"] = ""
        if("survivalVidaTimeStamp" not in save["privateState"]):
            save["privateState"]["survivalVidaTimeStamp"] = []
        if("survivalVidasExtra" not in save["privateState"]):
            save["privateState"]["survivalVidasExtra"] = 0
        if("survivalMaps" not in save["privateState"]):
            save["privateState"]["survivalMaps"] = {
                "100000035": {
                    "ts": 0,
                    "tp": 0
                },
                "100000036": {
                    "ts": 0,
                    "tp": 0
                },
                "100000037": {
                    "ts": 0,
                    "tp": 0
                }
            }
        save["version"] = "0.04a"
        print("   > migrated to 0.04a")

    # 0.04a -> 0.05a
    if save["version"] == "0.04a":
        if "lastUpgrades" not in save["privateState"]:
            save["privateState"]["lastUpgrades"] = []
        if "marketTimestamp" not in save["privateState"]:
            save["privateState"]["marketTimestamp"] = 0
        for m in save["maps"]:
            if "resourcesTraded" not in m or m["resourcesTraded"] is None:
                m["resourcesTraded"] = {}
        save["version"] = "0.05a"
        print("   > migrated to 0.05a")

    # 0.05a -> 0.06a: oyun 1.4.07 istemcisine geçti (GEC-02). Kayıt alanları burada değişmez; 1.4.07'nin yeni
    # privateState alanlarının göçü GEC-04'te bu adımın ardına eklenir. Göçten önceki kayıt backups/ altında durur.
    if save["version"] == "0.05a":
        save["version"] = "0.06a"
        print("   > migrated to 0.06a")

    # 0.06a -> 0.07a: görev numaraları 1.4.07'nin hedeflerine çevrilir (GOR-01). 0.06a'da göç edip oynanmış kayıtta
    # numaraların bir kısmı 1.4.07'de kazanılmıştır; eskiler yalnızca göç öncesi yedekte olanlardır.
    if save["version"] == "0.06a":
        eski = None if eski_istemci else set(eski_gorevler or ())
        if gorev_numaralarini_cevir(save.setdefault("privateState", {}), eski):
            print("   > gorev numaralari 1.4.07'ye cevrildi")
        save["version"] = "0.07a"
        print("   > migrated to 0.07a")

    # 0.07a -> 0.08a: 1.4.07'nin yokluğunda bozulduğu privateState alanları eklenir (oyun/kayit_semasi.py)
    if save["version"] == "0.07a":
        eklenen = eksikleri_tamamla(save.setdefault("privateState", {}))
        if eklenen:
            print(f"   > 1.4.07 alanlari: {', '.join(eklenen)}")
        save["version"] = "0.08a"
        print("   > migrated to 0.08a")

    return True