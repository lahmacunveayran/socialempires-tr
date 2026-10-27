# -*- coding: utf-8 -*-
"""Turnuva sistemi (4 oyunculu, botlarla doldurulur).

Orijinal oyunda turnuvalar 4 kişilik odalarda oynanır; herkes herkesle
bir maç yapar. Tek kişilik sunucuda boş koltuklar botlarla doldurulur ve
bot-bot maçları otomatik oynanır.

Durum bellek içinde tutulur; sunucu yeniden başlarsa turnuvalar sıfırlanır.
"""

import json
import os
import random
import threading
import time
import uuid

from bundle import SAVES_DIR
from sessions import all_saves_userid, save_session, session

KILIT = threading.RLock()
TURNUVALAR = {}
SON_TEMIZLIK = 0


def _oyuncu_bilgi(uid):
    kayit = session(uid)
    if not kayit:
        return None
    pi = kayit.get("playerInfo", {})
    return {
        "user_id": str(uid),
        "id": str(uid),
        "name": pi.get("name", "Oyuncu"),
        "pic": pi.get("pic") or "/img/profile/1025.png",
        "level": int(kayit["maps"][0].get("level", 1)),
        "bot": bool(pi.get("bot")),
    }


def _bot_oyuncu(no):
    return {
        "user_id": f"bot-{uuid.uuid4().hex[:8]}",
        "id": f"bot-{uuid.uuid4().hex[:8]}",
        "name": f"Bot {no}",
        "pic": "/img/profile/1025.png",
        "level": 1,
        "bot": True,
    }


def _botlar(haric=()):
    haric = {str(x) for x in haric}
    botlar = []
    for uid in all_saves_userid():
        if str(uid) in haric:
            continue
        bilgi = _oyuncu_bilgi(uid)
        if bilgi and bilgi["bot"]:
            botlar.append(bilgi)
    random.shuffle(botlar)
    return botlar


def _maclari_uret(oyuncular):
    maclar = []
    for i in range(len(oyuncular)):
        for j in range(i + 1, len(oyuncular)):
            maclar.append({
                "id": f"m{len(maclar) + 1}",
                "player1": oyuncular[i]["user_id"],
                "player2": oyuncular[j]["user_id"],
                "winner": None,
                "state": "pending",
            })
    return maclar


def _oyuncu(turnuva, uid):
    for o in turnuva["players"]:
        if o["user_id"] == str(uid):
            return o
    return None


def _bot_maclarini_oyna(turnuva):
    """İki tarafı da bot olan bekleyen maçları otomatik sonuçlandırır."""
    for mac in turnuva["matches"]:
        if mac["state"] != "pending":
            continue
        p1, p2 = _oyuncu(turnuva, mac["player1"]), _oyuncu(turnuva, mac["player2"])
        if not p1 or not p2:
            continue
        if not (p1.get("bot") and p2.get("bot")):
            continue
        s1, s2 = max(1, p1.get("level", 1)), max(1, p2.get("level", 1))
        mac["winner"] = p1["user_id"] if random.random() < s1 / (s1 + s2) else p2["user_id"]
        mac["state"] = "finished"


def _turnuvayi_bitir(turnuva):
    if turnuva["state"] != "running":
        return
    if not all(m["state"] == "finished" for m in turnuva["matches"]):
        return
    turnuva["state"] = "finished"
    puanlar = {}
    for mac in turnuva["matches"]:
        puanlar[mac["winner"]] = puanlar.get(mac["winner"], 0) + 1
    kazanan = max(puanlar, key=puanlar.get) if puanlar else None
    turnuva["winner"] = kazanan
    if kazanan:
        kayit = session(kazanan)
        if kayit:
            ps = kayit.setdefault("privateState", {})
            ps["trophies"] = int(ps.get("trophies", 0) or 0) + 30
            ps["turnuva_zaferi"] = int(ps.get("turnuva_zaferi", 0) or 0) + 1
            kayit.setdefault("playerInfo", {})["cash"] = int(kayit.get("playerInfo", {}).get("cash", 0) or 0) + 2
            try:
                save_session(kazanan)
            except Exception as hata:
                print(" ! Turnuva odulu kaydedilemedi:", hata)


def turnuva_olustur(owner_uid, tip="general", ucret=0):
    with KILIT:
        sahip = _oyuncu_bilgi(owner_uid)
        if not sahip:
            return None
        oyuncular = [sahip] + _botlar([owner_uid])[:3]
        while len(oyuncular) < 4:
            oyuncular.append(_bot_oyuncu(len(oyuncular) + 1))
        turnuva = {
            "id": "t-" + uuid.uuid4().hex[:10],
            "tournamentId": None,
            "type": tip,
            "state": "waiting",
            "entryCost": int(ucret or 0),
            "prize": 2500,
            "created": int(time.time()),
            "owner": str(owner_uid),
            "players": oyuncular,
            "users": oyuncular,
            "matches": _maclari_uret(oyuncular),
            "rounds": 3,
            "maxPlayers": 4,
        }
        turnuva["tournamentId"] = turnuva["id"]
        TURNUVALAR[turnuva["id"]] = turnuva
        return turnuva


def turnuva_bul(uid):
    with KILIT:
        for turnuva in TURNUVALAR.values():
            if turnuva["state"] not in ("waiting", "running"):
                continue
            if any(o["user_id"] == str(uid) for o in turnuva["players"]):
                return turnuva
    return None


def bul_veya_olustur(uid):
    """Aktif turnuvayı döndürür; yoksa kilit altında tek bir tane açar."""
    with KILIT:
        mevcut = turnuva_bul(uid)
        if mevcut:
            return mevcut
        return turnuva_olustur(uid)


def turnuvalar(uid=None):
    with KILIT:
        hepsi = [t for t in TURNUVALAR.values() if t["state"] != "cancelled"]
        if uid is not None:
            hepsi = [t for t in hepsi if any(o["user_id"] == str(uid) for o in t["players"])]
        return sorted(hepsi, key=lambda t: t["created"], reverse=True)


def turnuvaya_katil(turnuva_id, uid):
    with KILIT:
        turnuva = TURNUVALAR.get(turnuva_id)
        if not turnuva or turnuva["state"] != "waiting":
            return None
        if any(o["user_id"] == str(uid) for o in turnuva["players"]):
            return turnuva
        bilgi = _oyuncu_bilgi(uid)
        if not bilgi:
            return None
        for i, oyuncu in enumerate(turnuva["players"]):
            if oyuncu.get("bot"):
                turnuva["players"][i] = bilgi
                turnuva["users"] = turnuva["players"]
                turnuva["matches"] = _maclari_uret(turnuva["players"])
                return turnuva
    return None


def mac_baslat(turnuva_id, uid):
    with KILIT:
        turnuva = TURNUVALAR.get(turnuva_id)
        if not turnuva or turnuva["state"] in ("finished", "cancelled"):
            return None
        if turnuva["state"] == "waiting":
            turnuva["state"] = "running"
        _bot_maclarini_oyna(turnuva)
        _turnuvayi_bitir(turnuva)
        for mac in turnuva["matches"]:
            if mac["state"] != "pending":
                continue
            if mac["player1"] == str(uid):
                return {"match": mac, "opponent": _oyuncu_bilgi(mac["player2"])}
            if mac["player2"] == str(uid):
                return {"match": mac, "opponent": _oyuncu_bilgi(mac["player1"])}
    return None


def mac_bitir(turnuva_id, uid, kazandi):
    with KILIT:
        turnuva = TURNUVALAR.get(turnuva_id)
        if not turnuva or turnuva["state"] in ("finished", "cancelled"):
            return turnuva
        if turnuva["state"] == "waiting":
            turnuva["state"] = "running"
        for mac in turnuva["matches"]:
            if mac["state"] != "pending":
                continue
            if mac["player1"] == str(uid):
                mac["winner"] = mac["player1"] if kazandi else mac["player2"]
            elif mac["player2"] == str(uid):
                mac["winner"] = mac["player2"] if kazandi else mac["player1"]
            else:
                continue
            mac["state"] = "finished"
            break
        _bot_maclarini_oyna(turnuva)
        _turnuvayi_bitir(turnuva)
        return turnuva


def turnuvadan_ayril(turnuva_id, uid):
    with KILIT:
        turnuva = TURNUVALAR.get(turnuva_id)
        if not turnuva or turnuva["state"] != "waiting":
            return None
        if turnuva["owner"] == str(uid):
            turnuva["state"] = "cancelled"
            return turnuva
        for i, o in enumerate(turnuva["players"]):
            if o["user_id"] == str(uid) and not o.get("bot"):
                turnuva["players"][i] = _bot_oyuncu(i + 1)
                turnuva["users"] = turnuva["players"]
                turnuva["matches"] = _maclari_uret(turnuva["players"])
                break
        return turnuva


def turnuva_iptal(turnuva_id, uid):
    with KILIT:
        turnuva = TURNUVALAR.get(turnuva_id)
        if turnuva and turnuva.get("owner") == str(uid):
            turnuva["state"] = "cancelled"
        return turnuva


def eski_turnuvalari_temizle():
    global SON_TEMIZLIK
    simdi = int(time.time())
    if simdi - SON_TEMIZLIK < 600:
        return
    SON_TEMIZLIK = simdi
    with KILIT:
        for tid, turnuva in list(TURNUVALAR.items()):
            if turnuva["state"] in ("finished", "cancelled", "waiting") and simdi - turnuva["created"] > (3600 if turnuva["state"] != "waiting" else 7200):
                del TURNUVALAR[tid]


def gunluge_yaz(olay, veri):
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        with open(os.path.join(SAVES_DIR, "turnuva_gunlugu.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": int(time.time()), "olay": olay, "veri": veri}, ensure_ascii=False) + "\n")
    except OSError:
        pass
