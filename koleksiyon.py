# -*- coding: utf-8 -*-
"""Birim koleksiyonları: kategori tamamlama ve ödüller."""

from get_game_config import get_game_config
from odul import depo, depo_adet, depo_cikar, para_ekle


def kategoriler():
    return get_game_config().get("units_collections_categories", {}) or {}


def kategori(kategori_id):
    return kategoriler().get(str(kategori_id))


def _birim_var_mi(birim_id):
    for e in get_game_config().get("items", []):
        if str(e.get("id")) == str(birim_id):
            return True
    return False


def _envanterde_var(save, birim_id):
    if depo_adet(save, birim_id) > 0:
        return True
    return any(int(esya[0]) == int(birim_id) for h in save.get("maps", []) for esya in h.get("items", []))


def _tuket(save, birim_id, adet):
    """Önce depodan, sonra ordudan birim düşer; yetersizse False."""
    kalan = int(adet)
    while kalan > 0 and depo_adet(save, birim_id) > 0:
        depo_cikar(save, birim_id, 1)
        kalan -= 1
    for h in save.get("maps", []):
        if kalan <= 0:
            break
        for esya in list(h.get("items", [])):
            if kalan <= 0:
                break
            if int(esya[0]) == int(birim_id):
                h["items"].remove(esya)
                kalan -= 1
    return kalan == 0


def _envanter_sayi(save, birim_id):
    adet = depo_adet(save, birim_id)
    for h in save.get("maps", []):
        for esya in h.get("items", []):
            if int(esya[0]) == int(birim_id):
                adet += 1
    return adet


def _gerekli(kat):
    birimler = [int(x) for x in kat.get("units", [])]
    costs = kat.get("costs")
    if isinstance(costs, list) and len(costs) == len(birimler):
        return {b: max(1, int(c or 1)) for b, c in zip(birimler, costs)}
    toplam = max(1, int(kat.get("cost", 1) or 1))
    return {b: toplam for b in birimler}


def tamamla(save, kategori_id, town_id=0):
    kat = kategori(kategori_id)
    if not kat:
        return False
    ps = save.setdefault("privateState", {})
    tamamlanan = ps.setdefault("unitCollections", [])
    if str(kategori_id) in [str(x) for x in tamamlanan]:
        return False
    gerekli = _gerekli(kat)
    costs = kat.get("costs")
    if isinstance(costs, list) and len(costs) == len(kat.get("units", [])):
        # Önce tüm gereksinimleri doğrula (yarıda tüketim olmasın)
        for birim, adet in gerekli.items():
            if _envanter_sayi(save, birim) < adet:
                return False
        for birim, adet in gerekli.items():
            if not _tuket(save, birim, adet):
                return False
    else:
        # Toplam adet, koleksiyondaki birimlerden herhangi biriyle karşılanabilir
        kalan = max(1, int(kat.get("cost", 1) or 1))
        toplam = sum(_envanter_sayi(save, b) for b in gerekli)
        if toplam < kalan:
            return False
        for birim in gerekli:
            while kalan > 0 and _envanter_sayi(save, birim) > 0:
                if not _tuket(save, birim, 1):
                    break
                kalan -= 1
        if kalan > 0:
            return False
    odul = int(kat.get("rewards", 0) or 0)
    if odul:
        depo(save, odul, 1)
    para_ekle(save, town_id, "coins", 500)
    tamamlanan.append(str(kategori_id))
    return True


def birim_tamamlandi(save, birim_id, town_id=0):
    try:
        birim_id = int(birim_id)
    except (TypeError, ValueError):
        return False
    if birim_id <= 0 or not _birim_var_mi(birim_id):
        return False
    # Yalnızca bir koleksiyonda geçen ve oyuncunun sahip olduğu birimler.
    ilgili = {int(x) for kat in kategoriler().values() for x in kat.get("units", [])}
    if birim_id not in ilgili or not _envanterde_var(save, birim_id):
        return False
    ps = save.setdefault("privateState", {})
    tamamlanan = ps.setdefault("unitCollectionsCompleted", [])
    if str(birim_id) in [str(x) for x in tamamlanan]:
        return False
    tamamlanan.append(str(birim_id))
    para_ekle(save, town_id, "coins", 250)
    return True


def durum(save):
    ps = save.get("privateState", {})
    return {
        "completed": ps.get("unitCollections", []),
        "units_completed": ps.get("unitCollectionsCompleted", []),
    }
