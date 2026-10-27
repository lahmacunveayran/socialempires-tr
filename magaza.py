# -*- coding: utf-8 -*-
"""Mağaza: teklif paketleri, cash ile eşya, cash borsası, depo ve PvP alımları."""

from get_game_config import get_game_config
from odul import cash_ekle, cash_harca, depo, harita


def esya(esya_id):
    for e in get_game_config().get("items", []):
        if str(e.get("id")) == str(esya_id):
            return e
    return None


def teklif(teklif_id):
    for p in get_game_config().get("offer_packs", []):
        if str(p.get("id")) == str(teklif_id):
            return p
    return None


def teklif_al(save, town_id, teklif_id):
    p = teklif(teklif_id)
    if not p:
        return False
    fiyat = int(p.get("cost_cash", 0) or 0)
    if fiyat and not cash_harca(save, fiyat):
        return False
    # Paket eşyaları düz id listesi veya iç içe id grupları olabilir; hepsini
    # tek tek (adet 1) ver.
    esyalar = []
    for ham in p.get("items", []) or []:
        parcalar = ham if isinstance(ham, (list, tuple)) else [ham]
        for x in parcalar:
            try:
                esya_id = int(x)
            except (TypeError, ValueError):
                continue
            if esya_id > 0:
                esyalar.append((esya_id, 1))
    try:
        h = harita(save, town_id)
        for alan in ("gold", "wood", "stone", "food"):
            miktar = int(p.get(alan, 0) or 0)
            if miktar:
                hedef = "coins" if alan == "gold" else alan
                h[hedef] = int(h.get(hedef, 0)) + miktar
        h["xp"] = int(h.get("xp", 0)) + int(p.get("xp", 0) or 0)
        if p.get("mana"):
            ps = save.setdefault("privateState", {})
            ps["mana"] = int(ps.get("mana", 0) or 0) + int(p["mana"])
        for esya_id, adet in esyalar:
            depo(save, esya_id, adet)
    except (TypeError, ValueError, KeyError):
        if fiyat:
            cash_ekle(save, fiyat)  # yarıda kalan alımı geri al
        return False
    return True


def satin_al(save, town_id, esya_id, x=0, y=0, kaynaktan_dus=True, carpan=1):
    e = esya(esya_id)
    if not e:
        return False
    try:
        carpan = float(carpan if carpan is not None else 1)
    except (TypeError, ValueError):
        carpan = 1
    if carpan <= 0:
        return False
    carpan = min(carpan, 1)  # istemciden gelen çarpan fiyatı düşüremez
    fiyat = int(int(e.get("cost", 0) or 0) * carpan)
    if fiyat < 0:
        return False
    tur = e.get("cost_type", "g")
    h = harita(save, town_id)
    if kaynaktan_dus and fiyat > 0:
        if tur == "c":
            if not cash_harca(save, fiyat):
                return False
        else:
            alan = {"w": "wood", "g": "coins", "s": "stone", "f": "food"}.get(tur, "coins")
            if int(h.get(alan, 0)) < fiyat:
                return False
            h[alan] = int(h.get(alan, 0)) - fiyat
    from engine import timestamp_now
    h.setdefault("items", []).append([int(esya_id), int(x), int(y), 0, timestamp_now(), 0])
    if kaynaktan_dus:
        h["xp"] = int(h.get("xp", 0)) + int(e.get("xp", 0) or 0)
    return True


def depo_esya_cash(save, esya_id):
    e = esya(esya_id)
    if not e or e.get("cost_type") != "c":
        return False
    fiyat = int(e.get("cost", 0) or 0)
    if not cash_harca(save, fiyat):
        return False
    depo(save, esya_id, 1)
    return True


def cash_borsasi(save, town_id):
    g = get_game_config().get("globals", {})
    cash = int(g.get("EXCHANGE_CASH", 5) or 5)
    altin = int(g.get("EXCHANGE_GOLD", 2500) or 2500)
    if not cash_harca(save, cash):
        return False
    h = harita(save, town_id)
    h["coins"] = int(h.get("coins", 0)) + altin
    return True


def pvp_bolge_al(save):
    fiyat = int(get_game_config().get("globals", {}).get("PVP_BUY_TERRITORY_CASH", 5) or 5)
    if not cash_harca(save, fiyat):
        return False
    ps = save.setdefault("privateState", {})
    ps["pvp_territory_bought"] = int(ps.get("pvp_territory_bought", 0) or 0) + 1
    return True


def pvp_ada_al(save):
    fiyat = int(get_game_config().get("globals", {}).get("PVP_BUY_ISLAND_CASH", 30) or 30)
    if not cash_harca(save, fiyat):
        return False
    ps = save.setdefault("privateState", {})
    ps["pvp_island_bought"] = int(ps.get("pvp_island_bought", 0) or 0) + 1
    return True


def depo_kapasite(save, tek=False):
    g = get_game_config().get("globals", {})
    ps = save.setdefault("privateState", {})
    kapasiteler = g.get("WAREHOUSE_CAPACITIES", [])
    if kapasiteler:
        mevcut_kap = int(ps.get("warehouse_capacity", 0) or 0)
        if mevcut_kap not in kapasiteler:
            adim = min(max(0, int(ps.get("warehouse_capacity_step", 0) or 0)), len(kapasiteler) - 1)
            mevcut_kap = int(kapasiteler[adim])
        indeks = kapasiteler.index(mevcut_kap)
        if indeks + 1 >= len(kapasiteler):
            return False  # azami depo kapasitesi
        yeni_indeks = indeks + 1
    else:
        yeni_indeks = int(ps.get("warehouse_capacity_step", 0) or 0) + 1
    fiyatlar = g.get("WAREHOUSE_CAPACITY_INCREASE_PRICE_SINGLE" if tek else "WAREHOUSE_CAPACITY_INCREASE_PRICE", 50)
    if isinstance(fiyatlar, list):
        fiyat = int(fiyatlar[min(yeni_indeks, len(fiyatlar) - 1)] or 0)
    else:
        fiyat = int(fiyatlar or 0)
    if not cash_harca(save, fiyat):
        return False
    ps["warehouse_capacity_step"] = yeni_indeks
    if kapasiteler:
        ps["warehouse_capacity"] = int(kapasiteler[yeni_indeks])
    return True


def kilidi_ac(save, anahtar, deger):
    ps = save.setdefault("privateState", {})
    liste = ps.setdefault(anahtar, [])
    if deger not in liste:
        liste.append(deger)
    return True


def stok_durumu(save):
    ps = save.get("privateState", {})
    return {
        "cash": int(save.get("playerInfo", {}).get("cash", 0) or 0),
        "warehouse_step": int(ps.get("warehouse_capacity_step", 0) or 0),
        "warehouse_capacity": int(ps.get("warehouse_capacity", 0) or 0),
        "territory_bought": int(ps.get("pvp_territory_bought", 0) or 0),
        "island_bought": int(ps.get("pvp_island_bought", 0) or 0),
    }
