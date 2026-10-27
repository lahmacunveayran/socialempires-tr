# -*- coding: utf-8 -*-
"""Günlük oyun döngüsü: giriş takvimi, günlük görevler ve haftalık meydan okuma.

Tüm ödüller sunucu tarafında otomatik verilir; istemciye ek ekran gerekmez.
"""

import random
import time
from datetime import date, timedelta

from odul import cash_ekle, depo, harita, odul_uygula, para_ekle

GOREV_TASLAKLARI = [
    {"id": "collect", "ad": "Kaynak topla", "hedef": 10, "odul": {"coins": 400}},
    {"id": "upgrade", "ad": "Bina yükselt", "hedef": 3, "odul": {"coins": 600}},
    {"id": "build", "ad": "Bina inşa et", "hedef": 3, "odul": {"coins": 500}},
    {"id": "attack", "ad": "Savaş kazan", "hedef": 2, "odul": {"cash": 1}},
    {"id": "mission", "ad": "Görev tamamla", "hedef": 2, "odul": {"coins": 700}},
]

HAFTALIK = [
    {"id": "attack", "ad": "Haftanın Savaşçısı", "hedef": 10, "odul": {"cash": 3}},
    {"id": "build", "ad": "Haftanın Mimarı", "hedef": 15, "odul": {"cash": 2, "coins": 2500}},
    {"id": "collect", "ad": "Haftanın Toplayıcısı", "hedef": 40, "odul": {"cash": 2}},
]

GIRIS_ODULLERI = [
    {"coins": 500},
    {"food": 1500},
    {"wood": 1500},
    {"stone": 1500},
    {"cash": 1},
    {"coins": 2500},
    {"cash": 2, "unit": 541},
]


def _gun():
    return time.strftime("%Y-%m-%d", time.localtime())


def _hafta():
    yil, hafta, _ = date.today().isocalendar()
    return f"{yil}-W{hafta}"


def _dun():
    return (date.today() - timedelta(days=1)).isoformat()


def _gunluk(save):
    return save.setdefault("privateState", {}).setdefault("gunluk", {})


def _gunluk_gorevleri(save):
    g = _gunluk(save)
    if g.get("tarih") == _gun():
        return g
    rnd = random.Random(_gun())
    secilen = rnd.sample(GOREV_TASLAKLARI, 3)
    g["tarih"] = _gun()
    g["gorevler"] = [
        {"id": t["id"], "ad": t["ad"], "hedef": t["hedef"], "ilerleme": 0,
         "odul": t["odul"], "alindi": 0}
        for t in secilen
    ]
    return g


def _haftalik(save):
    g = _gunluk(save)
    if g.get("hafta") == _hafta() and isinstance(g.get("haftalik"), dict):
        return g["haftalik"]
    rnd = random.Random(_hafta())
    sec = rnd.choice(HAFTALIK)
    g["hafta"] = _hafta()
    g["haftalik"] = {"id": sec["id"], "ad": sec["ad"], "hedef": sec["hedef"],
                     "ilerleme": 0, "odul": sec["odul"], "alindi": 0}
    return g["haftalik"]


def _odul_ver(save, odul):
    for anahtar, deger in (odul or {}).items():
        if anahtar in ("coins", "food", "wood", "stone"):
            para_ekle(save, 0, "coins" if anahtar == "coins" else anahtar, deger)
        elif anahtar == "cash":
            cash_ekle(save, deger)
        elif anahtar == "unit":
            depo(save, deger, 1)


def ilerle(save, olay, miktar=1):
    """Oyun içi bir eylemde günlük ve haftalık ilerlemeyi artırır."""
    g = _gunluk_gorevleri(save)
    for gorev in g["gorevler"]:
        if gorev["id"] != olay or gorev["alindi"]:
            continue
        gorev["ilerleme"] = min(gorev["hedef"], int(gorev["ilerleme"]) + int(miktar))
        if gorev["ilerleme"] >= gorev["hedef"]:
            gorev["alindi"] = 1
            _odul_ver(save, gorev["odul"])
            print(f" [+] Gunluk gorev tamamlandi: {gorev['ad']}")
    h = _haftalik(save)
    if h["id"] == olay and not h["alindi"]:
        h["ilerleme"] = min(h["hedef"], int(h["ilerleme"]) + int(miktar))
        if h["ilerleme"] >= h["hedef"]:
            h["alindi"] = 1
            _odul_ver(save, h["odul"])
            print(f" [+] Haftalik meydan okuma tamamlandi: {h['ad']}")


def giris(save):
    """Günlük giriş takvimini işler; günde bir kez ödül verir."""
    g = _gunluk_gorevleri(save)
    bugun = _gun()
    if g.get("son_giris") == bugun:
        return False
    onceki = g.get("son_giris")
    seri = int(g.get("seri", 0) or 0)
    seri = seri + 1 if onceki == _dun() else 1
    gun = ((seri - 1) % 7) + 1
    odul = dict(GIRIS_ODULLERI[gun - 1])
    _odul_ver(save, odul)
    # 2+ gün ara veren için geri dönüş paketi
    if onceki and onceki < _dun():
        try:
            from etkinlik import geri_donus
            geri_donus(save, 0)
        except Exception:
            pass
    g["son_giris"] = bugun
    g["seri"] = seri
    g["son_odul_gun"] = gun
    print(f" [+] Gunluk giris odulu ({gun}/7), seri {seri}")
    return True


def durum(save):
    g = _gunluk_gorevleri(save)
    h = _haftalik(save)
    return {
        "tarih": g.get("tarih"),
        "seri": int(g.get("seri", 0) or 0),
        "son_odul_gun": int(g.get("son_odul_gun", 0) or 0),
        "gorevler": g.get("gorevler", []),
        "haftalik": h,
    }
