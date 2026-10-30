import random

from oyun.ekonomi import timestamp_now

version_name = "alpha 0.06"
version_code = "0.06a"

def migrate_loaded_save(save: dict) -> bool:

    # discard current version saves
    if save.get("version") == version_code:
        return False
    
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

    return True