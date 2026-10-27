# -*- coding: utf-8 -*-
"""Ödül ve envanter yardımcıları (görev, mağaza, koleksiyon, etkinlik)."""

from get_game_config import get_game_config


def harita(save, town_id=0):
    try:
        town_id = int(town_id)
    except (TypeError, ValueError):
        town_id = 0
    if not (0 <= town_id < len(save.get("maps", []))):
        town_id = 0
    return save["maps"][town_id]


def para_ekle(save, town_id, alan, miktar):
    harita(save, town_id)[alan] = int(harita(save, town_id).get(alan, 0)) + int(miktar)


def cash_ekle(save, miktar):
    save.setdefault("playerInfo", {})["cash"] = int(save.get("playerInfo", {}).get("cash", 0) or 0) + int(miktar)


def cash_var(save, miktar):
    return int(save.get("playerInfo", {}).get("cash", 0) or 0) >= int(miktar)


def cash_harca(save, miktar):
    miktar = int(miktar)
    if not cash_var(save, miktar):
        return False
    save["playerInfo"]["cash"] = int(save["playerInfo"].get("cash", 0)) - miktar
    return True


def depo(save, esya_id, adet=1):
    esya_id = int(esya_id)
    gifts = save.setdefault("privateState", {}).setdefault("gifts", [])
    while len(gifts) <= esya_id:
        gifts.append(0)
    gifts[esya_id] = int(gifts[esya_id] or 0) + int(adet)


def depo_cikar(save, esya_id, adet=1):
    esya_id = int(esya_id)
    gifts = save.setdefault("privateState", {}).setdefault("gifts", [])
    if esya_id >= len(gifts) or int(gifts[esya_id] or 0) < int(adet):
        return False
    gifts[esya_id] = int(gifts[esya_id]) - int(adet)
    while gifts and gifts[-1] == 0:
        gifts.pop()
    return True


def depo_adet(save, esya_id):
    gifts = save.get("privateState", {}).get("gifts", [])
    if 0 <= int(esya_id) < len(gifts):
        return int(gifts[int(esya_id)] or 0)
    return 0


def birim_ekle(save, town_id, birim_id, adet=1):
    from engine import timestamp_now
    h = harita(save, town_id)
    for _ in range(int(adet)):
        h.setdefault("items", []).append([int(birim_id), 0, 0, 0, timestamp_now(), 0])


def odul_uygula(save, town_id, oduller):
    """[{'type':'g'|'c'|'u','value':N}] biçimindeki ödülleri uygular."""
    for odul in oduller or []:
        if not isinstance(odul, dict):
            continue
        tur = str(odul.get("type", "g"))
        deger = int(odul.get("value", odul.get("qty", 0)) or 0)
        if deger <= 0:
            continue
        if tur == "g":
            para_ekle(save, town_id, "coins", deger)
        elif tur == "c":
            cash_ekle(save, deger)
        elif tur == "u":
            birim_ekle(save, town_id, deger)
        elif tur == "hero":
            birim_ekle(save, town_id, deger)


def esya_adi(esya_id):
    for esya in get_game_config().get("items", []):
        if str(esya.get("id")) == str(esya_id):
            return esya.get("name", str(esya_id))
    return str(esya_id)
