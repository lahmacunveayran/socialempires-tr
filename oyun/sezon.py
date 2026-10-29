# -*- coding: utf-8 -*-
"""Haftalık PvP sezonu.

Her hafta başında kupa sıralamasındaki ilk üç oyuncuya cash ödülü verilir
ve kupalar bir miktar yumuşatılır (lig yeniden dengelensin).
"""

import json
import os
import tempfile
import time

from oyun.yollar import SAVES_DIR
from oyun.kayit import all_saves_userid, save_session, session

DURUM_DOSYASI = os.path.join(SAVES_DIR, "sezon.json")


def _hafta(ts=None):
    yil, hafta, _ = time.strftime("%Y-%W-%w", time.localtime(ts)).split("-")
    return f"{yil}-W{hafta}"


def _oku():
    try:
        with open(DURUM_DOSYASI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _yaz(veri):
    """Atomik yazar; başarılıysa True döner."""
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        fd, gecici = tempfile.mkstemp(dir=SAVES_DIR, prefix="sezon-", suffix=".tmp")
        os.close(fd)
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        os.replace(gecici, DURUM_DOSYASI)
        return True
    except OSError as hata:
        print(" ! Sezon durumu yazilamadi:", hata)
        return False


def kontrol():
    hafta = _hafta()
    durum = _oku()
    if durum.get("hafta") == hafta:
        return durum

    oyuncular = []
    for uid in all_saves_userid():
        kayit = session(uid)
        if not kayit:
            continue
        ps = kayit.setdefault("privateState", {})
        try:
            kupa = int(ps.get("trophies", 0) or 0)
        except (TypeError, ValueError):
            kupa = 0
            ps["trophies"] = 0
        oyuncular.append((uid, kupa, kayit))
    oyuncular.sort(key=lambda x: x[1], reverse=True)

    oduller = [5, 3, 1]
    kazananlar = []
    for i, (uid, kupa, kayit) in enumerate(oyuncular[:3]):
        if kupa <= 0:
            continue
        kazananlar.append({"user_id": str(uid), "name": kayit["playerInfo"].get("name", ""),
                           "trophies": kupa, "cash": oduller[i]})

    yeni = {"hafta": hafta, "kazananlar": kazananlar, "guncelleme": int(time.time())}
    if not _yaz(yeni):
        return durum or yeni

    # Ödülleri ancak sezon durumu diske yazıldıktan sonra uygula.
    odul_map = {k["user_id"]: k["cash"] for k in kazananlar}
    for uid, kupa, kayit in oyuncular:
        degisti = False
        if str(uid) in odul_map:
            kayit.setdefault("playerInfo", {})["cash"] = int(kayit.get("playerInfo", {}).get("cash", 0) or 0) + odul_map[str(uid)]
            degisti = True
        if kupa:
            kayit.setdefault("privateState", {})["trophies"] = int(kupa * 0.6)
            degisti = True
        if degisti:
            try:
                session(uid)
                save_session(uid)
            except Exception as hata:
                print(" ! Sezon kaydi yazilamadi:", uid, hata)

    if kazananlar:
        print(" [+] Sezon odulleri:", kazananlar)
    return yeni


def bilgi():
    durum = _oku()
    return {
        "hafta": durum.get("hafta", _hafta()),
        "kazananlar": durum.get("kazananlar", []),
    }
