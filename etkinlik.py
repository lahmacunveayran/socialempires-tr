# -*- coding: utf-8 -*-
"""Etkinlikler: günlük bonus, pazartesi bonusu, geri dönüş ve hazine."""

import time

from get_game_config import get_game_config
from odul import birim_ekle, cash_ekle, harita, odul_uygula, para_ekle


def _gun():
    return time.strftime("%Y-%m-%d", time.localtime())


def _hafta():
    yil, hafta, _ = time.strftime("%Y-%W-%w", time.localtime()).split("-")
    return f"{yil}-W{hafta}"


def _etkinlikler(save):
    return save.setdefault("privateState", {}).setdefault("etkinlikler", {})


def gunluk_bonus(save, town_id=0):
    e = _etkinlikler(save)
    gun = _gun()
    if e.get("daily") == gun:
        return False
    g = get_game_config().get("globals", {})
    oduller = []
    for o in g.get("DAILY_BONUS_CONFIG", []):
        tur = o.get("type", "g")
        adet = int(o.get("qty", o.get("value", 0)) or 0)
        if tur == "hero":
            devam = True
            continue
        oduller.append({"type": tur, "value": adet})
    odul_uygula(save, town_id, oduller)
    # Günlük kahraman ödülü
    kahramanlar = g.get("DAILY_BONUS_CONFIG_HEROES", [])
    if kahramanlar:
        birim_ekle(save, town_id, kahramanlar[int(gun.replace("-", "")) % len(kahramanlar)], 1)
    e["daily"] = gun
    return True


def pazartesi_bonus(save, town_id=0):
    e = _etkinlikler(save)
    hafta = _hafta()
    if e.get("monday") == hafta:
        return False
    g = get_game_config().get("globals", {})
    odul_uygula(save, town_id, g.get("MONDAY_BONUS_REWARDS", []))
    birimler = g.get("MONDAY_BONUS_UNITS", [])
    if birimler:
        birim_ekle(save, town_id, birimler[int(hafta.split("-W")[1]) % len(birimler)], 1)
    e["monday"] = hafta
    return True


def geri_donus(save, town_id=0):
    e = _etkinlikler(save)
    simdi = int(time.time())
    if simdi - int(e.get("comeback", 0) or 0) < 20 * 3600:
        return False
    g = get_game_config().get("globals", {})
    odul_uygula(save, town_id, g.get("COMEBACK_BONUS_REWARDS", []))
    birimler = g.get("COMEBACK_BONUS_UNITS", [])
    if birimler:
        birim_ekle(save, town_id, birimler[simdi % len(birimler)], 1)
    e["comeback"] = simdi
    return True


def hazine(save, town_id=0):
    e = _etkinlikler(save)
    gun = _gun()
    if e.get("treasure") == gun:
        return False
    para_ekle(save, town_id, "coins", 1500)
    cash_ekle(save, 1)
    e["treasure"] = gun
    return True


def durum(save):
    e = save.get("privateState", {}).get("etkinlikler", {})
    return {
        "daily": e.get("daily"),
        "monday": e.get("monday"),
        "comeback": e.get("comeback", 0),
        "treasure": e.get("treasure"),
    }
