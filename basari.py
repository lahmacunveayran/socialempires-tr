# -*- coding: utf-8 -*-
"""Başarımlar: oyuncu istatistiklerine göre açılır, ödül verir."""

from odul import cash_ekle, para_ekle

BASARIMLAR = [
    {"id": "ilk_gorev", "ad": "İlk Adım", "kosul": lambda s: len(s.get("privateState", {}).get("completedMissions", [])) >= 1, "coins": 100},
    {"id": "gorev_10", "ad": "Görev Ustası", "kosul": lambda s: len(s.get("privateState", {}).get("completedMissions", [])) >= 10, "coins": 1000},
    {"id": "seviye_10", "ad": "Yükseliş", "kosul": lambda s: int(s["maps"][0].get("level", 1)) >= 10, "coins": 500},
    {"id": "insa_50", "ad": "Mimar", "kosul": lambda s: sum(len(h.get("items", [])) for h in s.get("maps", [])) >= 50, "coins": 1000},
    {"id": "pvp_10", "ad": "Savaşçı", "kosul": lambda s: len(s.get("privateState", {}).get("attacksSent", [])) >= 10, "coins": 500},
    {"id": "kupa_100", "ad": "Kupa Avcısı", "kosul": lambda s: int(s.get("privateState", {}).get("trophies", 0) or 0) >= 100, "cash": 1},
    {"id": "ada_1", "ad": "Fatih", "kosul": lambda s: int(s.get("privateState", {}).get("ada_odulu", 0) or 0) >= 1, "cash": 2},
    {"id": "koleksiyon_1", "ad": "Koleksiyoner", "kosul": lambda s: len(s.get("privateState", {}).get("unitCollections", [])) >= 1, "coins": 500},
]


def kontrol(save):
    """Koşulu sağlanan yeni başarımları açar ve ödüllerini verir."""
    ps = save.setdefault("privateState", {})
    acilan = ps.setdefault("basarimlar", [])
    yeni = []
    for b in BASARIMLAR:
        if b["id"] in acilan:
            continue
        try:
            if not b["kosul"](save):
                continue
        except Exception:
            continue
        acilan.append(b["id"])
        if b.get("coins"):
            para_ekle(save, 0, "coins", b["coins"])
        if b.get("cash"):
            cash_ekle(save, b["cash"])
        yeni.append(b["id"])
    return yeni


def liste(save):
    acilan = set(save.get("privateState", {}).get("basarimlar", []))
    return [{"id": b["id"], "name": b["ad"], "unlocked": b["id"] in acilan,
             "coins": b.get("coins", 0), "cash": b.get("cash", 0)} for b in BASARIMLAR]


def yayinla(save, birim_id=None):
    ps = save.setdefault("privateState", {})
    yayin = ps.setdefault("basarim_yayin", [])
    if birim_id is not None:
        yayin.append(int(birim_id))
    return liste(save)
