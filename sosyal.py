# -*- coding: utf-8 -*-
"""Sosyal döngü: komşu yardımı ve hediye gönderimi (günlük limitli)."""

import time

from odul import depo, depo_adet, depo_cikar, harita

GUNLUK_YARDIM = 20
GUNLUK_HEDIYE = 20


def _gun():
    return time.strftime("%Y-%m-%d", time.localtime())


def _sayac(save, anahtar):
    ps = save.setdefault("privateState", {})
    kayit = ps.setdefault(anahtar, {})
    gun = _gun()
    if kayit.get("gun") != gun:
        kayit["gun"] = gun
        kayit["sayi"] = 0
    return kayit


def yardim_et(save, hedef, hedef_uid, tur="assist"):
    """Komşuya yardım eder; günlük limit ve tekrar kontrolü uygular."""
    if not hedef or str(save.get("playerInfo", {}).get("pid")) == str(hedef_uid):
        return False
    sayac = _sayac(save, "gunluk_yardim")
    if int(sayac.get("sayi", 0)) >= GUNLUK_YARDIM:
        return False
    # Aynı komşuya günde bir kez yardım
    ps = save.setdefault("privateState", {})
    bugun = ps.setdefault("yardim_edilenler", {})
    if bugun.get("gun") != _gun():
        bugun["gun"] = _gun()
        bugun["liste"] = []
    if str(hedef_uid) in [str(x) for x in bugun.get("liste", [])]:
        return False
    bugun.setdefault("liste", []).append(str(hedef_uid))
    sayac["sayi"] = int(sayac.get("sayi", 0)) + 1

    # Yardım edene küçük ödül
    h = harita(save, 0)
    h["coins"] = int(h.get("coins", 0)) + 100
    h["xp"] = int(h.get("xp", 0)) + 5

    # Komşunun alınan yardım listesine yaz
    hps = hedef.setdefault("privateState", {})
    alinan = hps.setdefault("receivedAssists", [])
    alinan.append({"from": str(save.get("playerInfo", {}).get("pid")), "time": int(time.time()), "type": tur})
    if len(alinan) > 100:
        del alinan[:-100]
    return True


def hediye_gonder(save, hedef, hedef_uid, esya_id, adet=1):
    if not hedef or str(save.get("playerInfo", {}).get("pid")) == str(hedef_uid):
        return False
    sayac = _sayac(save, "gunluk_hediye")
    if int(sayac.get("sayi", 0)) >= GUNLUK_HEDIYE:
        return False
    if not depo_cikar(save, esya_id, adet):
        return False
    depo(hedef, esya_id, adet)
    sayac["sayi"] = int(sayac.get("sayi", 0)) + 1
    gelen = hedef.setdefault("privateState", {}).setdefault("hediye_gelen", [])
    gelen.append({"from": str(save.get("playerInfo", {}).get("pid")), "item": int(esya_id), "time": int(time.time())})
    if len(gelen) > 100:
        del gelen[:-100]
    return True


def durum(save):
    return {
        "yardim": dict(_sayac(save, "gunluk_yardim")),
        "hediye": dict(_sayac(save, "gunluk_hediye")),
        "received": len(save.get("privateState", {}).get("receivedAssists", [])),
        "sent": len(save.get("privateState", {}).get("attacksSent", [])),
    }
