# -*- coding: utf-8 -*-
"""Ada fetih sistemi: her adada 7 bölge, her bölgede bir bot köyü.

Oyuncu bir bölgedeki botu yendiğinde bölge fethedilir. 7/7 olunca ada
tamamlanır; ödül verilir ve bir sonraki adaya geçilir.

Fetihler `ada:posicion` anahtarıyla saklanır; böylece bot listesi değişse
bile aynı adadaki aynı bölge kastedilir.
"""

import hashlib

from sessions import all_saves_userid, session


def _botlar():
    botlar = []
    for uid in all_saves_userid():
        kayit = session(uid)
        if not kayit:
            continue
        pi = kayit.get("playerInfo", {})
        if pi.get("bot"):
            botlar.append((str(uid), pi.get("name", "Bot"),
                           int(kayit["maps"][0].get("level", 1)),
                           pi.get("pic") or "/img/profile/1025.png"))
    botlar.sort(key=lambda x: x[0])
    return botlar


def _sayisal(uid):
    return int(hashlib.sha256(str(uid).encode("utf-8")).hexdigest()[:8], 16)


def _ada_no(kayit):
    return int(kayit.get("privateState", {}).get("ada", 99) or 99)


def ada_slotlari(kayit):
    """Oyuncunun bulunduğu adadaki 7 bölgeyi döndürür."""
    botlar = _botlar()
    if len(botlar) < 7:
        return []
    ada = _ada_no(kayit)
    ps = kayit.get("privateState", {})
    fetih = set(str(x) for x in ps.get("ada_fetih", []))
    baslangic = ((ada - 99) * 7) % len(botlar)
    slotlar = []
    for i in range(7):
        uid, ad, seviye, pic = botlar[(baslangic + i) % len(botlar)]
        anahtar = f"{ada}:{uid}"
        conquered = anahtar in fetih or uid in fetih or f"{ada}:{i}" in fetih
        slotlar.append({
            "posicion": i, "pos": i, "position": i,
            "key": anahtar,
            "user_id": _sayisal(uid), "id": _sayisal(uid), "uid": uid, "saveId": _sayisal(uid),
            "name": ad,
            "nivel": seviye, "level": seviye,
            "pic": pic,
            "conquered": 1 if conquered else 0,
            "isConquered": 1 if conquered else 0,
            "state": 1 if conquered else 0,
        })
    return slotlar


def ada_durumu(kayit):
    slotlar = ada_slotlari(kayit)
    fetih = sum(1 for s in slotlar if s["conquered"])
    return {
        "ada": _ada_no(kayit),
        "fetih": fetih,
        "toplam": len(slotlar),
        "slotlar": slotlar,
    }


def fetih_kaydet(kayit, kurban_id):
    """Kurban adadaki bölgelerden birindeyse fethedildi olarak işaretler."""
    slotlar = ada_slotlari(kayit)
    hedef = next((s for s in slotlar if str(s.get("uid")) == str(kurban_id) or str(s.get("user_id")) == str(kurban_id)), None)
    if not hedef:
        return None
    ps = kayit.setdefault("privateState", {})
    fetih = ps.setdefault("ada_fetih", [])
    anahtar = hedef["key"]
    if anahtar not in fetih:
        fetih.append(anahtar)
    durum = ada_durumu(kayit)
    if durum["toplam"] and durum["fetih"] >= durum["toplam"]:
        ps["ada"] = durum["ada"] + 1
        ps["ada_fetih"] = []
        ps["ada_odulu"] = int(ps.get("ada_odulu", 0) or 0) + 1
        ps["trophies"] = int(ps.get("trophies", 0) or 0) + 50
        kayit.setdefault("playerInfo", {})["cash"] = int(kayit.get("playerInfo", {}).get("cash", 0) or 0) + 1
    return durum
