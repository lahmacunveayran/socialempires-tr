# -*- coding: utf-8 -*-
"""Görev (mission) zinciri ve haftalık görevler."""

import random
import time

from get_game_config import get_game_config
from odul import cash_ekle, cash_harca, harita, para_ekle


def gorevler():
    return {int(g["id"]): g for g in get_game_config().get("missions", []) if str(g.get("id", "")).isdigit()}


def gorev(gorev_id):
    return gorevler().get(int(gorev_id))


def tamamla(save, gorev_id, atla=False):
    g = gorev(gorev_id)
    if not g:
        return False
    ps = save.setdefault("privateState", {})
    if atla:
        # Atlama ücreti: config'te yoksa 1 cash (bedava atlama yok).
        ucret = int(get_game_config().get("globals", {}).get("SKIP_MISSION_CASH", 1) or 1)
        if not cash_harca(save, ucret):
            return False
    tamamlanan = ps.setdefault("completedMissions", [])
    if int(gorev_id) not in [int(x) for x in tamamlanan]:
        tamamlanan.append(int(gorev_id))
    ps["unlockedQuestIndex"] = max(int(ps.get("unlockedQuestIndex", 0) or 0), int(gorev_id))
    haftalik_ilerle(save, gorev_id)
    return True


def odul(save, town_id, gorev_id):
    g = gorev(gorev_id)
    if not g:
        return False
    ps = save.setdefault("privateState", {})
    if int(gorev_id) not in [int(x) for x in ps.get("completedMissions", [])]:
        return False
    odul_verilen = ps.setdefault("rewardedMissions", [])
    if int(gorev_id) in [int(x) for x in odul_verilen]:
        return False
    para_ekle(save, town_id, "coins", int(g.get("reward", 0) or 0))
    odul_verilen.append(int(gorev_id))
    return True


def sifirla(save):
    ps = save.setdefault("privateState", {})
    ps["completedMissions"] = []
    ps["unlockedQuestIndex"] = 0
    # rewardedMissions korunur; sıfırlama ödül hakkını geri vermez.
    return True


def _hafta():
    yil, hafta, _ = time.strftime("%Y-%W-%w", time.localtime()).split("-")
    return f"{yil}-W{hafta}"


def haftalik_secim(save):
    ps = save.setdefault("privateState", {})
    hafta = _hafta()
    mevcut = ps.get("weeklyMissions")
    if isinstance(mevcut, dict) and mevcut.get("week") == hafta:
        return mevcut
    adaylar = [gid for gid in gorevler() if gid >= 10]
    rnd = random.Random(hafta)
    secilen = rnd.sample(adaylar, min(3, len(adaylar))) if adaylar else []
    mevcut = {"week": hafta, "ids": secilen, "done": [], "odul": 0}
    ps["weeklyMissions"] = mevcut
    return mevcut


def haftalik_ilerle(save, gorev_id):
    hm = haftalik_secim(save)
    if int(gorev_id) not in [int(x) for x in hm["ids"]]:
        return
    if int(gorev_id) in [int(x) for x in hm["done"]]:
        return
    hm["done"].append(int(gorev_id))
    if not hm.get("odul") and len(hm["done"]) >= len(hm["ids"]):
        para_ekle(save, 0, "coins", 1000)
        cash_ekle(save, 1)
        hm["odul"] = 1


def haftalik_durum(save):
    hm = haftalik_secim(save)
    return {
        "week": hm["week"],
        "missions": hm["ids"],
        "done": hm["done"],
        "rewarded": bool(hm.get("odul")),
    }
