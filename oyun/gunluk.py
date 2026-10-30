"""İmparatorluk günlüğü (/gunluk): savaş geçmişi, ganimet ve seviye ilerlemesi tek sayfada.

Yalnızca kayıttaki verilerden okur, hiçbir şey yazmaz:
- savaş geçmişi: privateState.attacksSent (oyuncunun saldırıları) ve attacksReceived (oyuncuya ve bot akınları),
- seviye ilerlemesi: günlük yedekler (saves/gunluk_yedek/<gün>/, oyun.yedek; en çok 14 gün) ve bugünkü kayıt.
"""

import json
import os
from datetime import datetime

from flask import redirect, render_template, session

from oyun import yedek
from oyun.diyar import portre
from oyun.dunya import rutbe
from oyun.kayit import all_saves_userid, save_info, session as kayit_oturumu
from oyun.sunucu import STATIK_YOL, app
from oyun.surum import version_name
from oyun.takvim import TURKIYE

ALANLAR = ("coins", "wood", "stone", "food")


def _tam(deger):
    try:
        return int(deger)
    except (TypeError, ValueError):
        return 0


def _rakip(aciklama, kimlik):
    """Raporda rakip yoksa (bot akınlarının gönderilen kaydı) kayıttan bulunur."""
    rakip = (aciklama or {}).get("oponent") or {}
    if not rakip.get("name"):
        kayit = kayit_oturumu(str(kimlik)) if kimlik else None
        if kayit:
            rakip = {"name": kayit["playerInfo"].get("name", ""), "level": kayit["maps"][0].get("level", 1),
                     "pic": kayit["playerInfo"].get("pic", "")}
    return {"ad": rakip.get("name") or "Bilinmeyen köy", "seviye": _tam(rakip.get("level")) or None,
            "resim": portre({"playerInfo": {"pic": rakip.get("pic", "")}})}


def savaslar(kayit):
    """Saldırı ve savunmalar, yeniden eskiye."""
    ps = kayit.get("privateState", {})
    liste = []
    for giris in ps.get("attacksSent") or []:
        if not isinstance(giris, dict):
            continue
        aciklama = giris.get("description") or {}
        kaynak = aciklama.get("resources") or {}
        liste.append({"yon": "saldiri", "zaman": _tam(giris.get("time")),
                      "zafer": _tam(aciklama.get("win")) == 1 if aciklama else None,
                      "altin": _tam(kaynak.get("g")), "xp": _tam(kaynak.get("x")),
                      "rakip": _rakip(aciklama, giris.get("victim_id"))})
    for giris in ps.get("attacksReceived") or []:
        if not isinstance(giris, dict):
            continue
        aciklama = giris.get("description") or {}
        saldiran_kazandi = _tam(aciklama.get("win")) == 1
        liste.append({"yon": "savunma", "zaman": _tam(giris.get("time")),
                      "zafer": not saldiran_kazandi,  # savunma için zafer: saldırı püskürtüldü
                      # saldıranın aldığı altın (kayıp) ya da püskürtünce kazanılan savunma ödülü
                      "altin": _tam((aciklama.get("resources") or {}).get("g")) if saldiran_kazandi
                      else _tam((aciklama.get("resources_victim") or {}).get("g")),
                      "xp": 0, "rakip": _rakip(aciklama, giris.get("attacker_id"))})
    liste.sort(key=lambda s: s["zaman"], reverse=True)
    for s in liste:
        s["tarih"] = datetime.fromtimestamp(s["zaman"], TURKIYE).strftime("%d.%m.%Y %H:%M") if s["zaman"] else ""
    return liste


def ozet(kayit, savas_listesi):
    saldirilar = [s for s in savas_listesi if s["yon"] == "saldiri"]
    savunmalar = [s for s in savas_listesi if s["yon"] == "savunma"]
    return {
        "saldiri": len(saldirilar),
        "saldiri_zafer": sum(1 for s in saldirilar if s["zafer"]),
        "ganimet": sum(s["altin"] for s in saldirilar),
        "xp": sum(s["xp"] for s in saldirilar),
        "savunma": len(savunmalar),
        "savunma_zafer": sum(1 for s in savunmalar if s["zafer"]),
        "kayip": sum(s["altin"] for s in savunmalar if not s["zafer"]),
        "onur": _tam(kayit.get("privateState", {}).get("honor")),
    }


def _anlik(kayit):
    harita = kayit["maps"][0]
    return {"seviye": _tam(harita.get("level")), "xp": _tam(harita.get("xp")),
            "onur": _tam(kayit.get("privateState", {}).get("honor")),
            "kaynak": sum(_tam(harita.get(a)) for a in ALANLAR)}


def ilerleme(uid, kayit, yedek_koku=None):
    """Gün gün seviye, XP, onur ve kaynak: günlük yedeklerden ve bugünkü kayıttan (eskiden yeniye)."""
    yedek_koku = yedek_koku or yedek.YEDEK_KOK
    gunler = {}
    try:
        klasorler = sorted(os.listdir(yedek_koku))
    except OSError:
        klasorler = []
    for gun in klasorler:
        yol = os.path.join(yedek_koku, gun, f"{uid}.save.json")
        try:
            with open(yol, encoding="utf-8") as f:
                gunler[gun] = _anlik(json.load(f))
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            continue
    gunler[datetime.now(TURKIYE).date().isoformat()] = _anlik(kayit)  # günün yedeği sabahki hâldir; bugün şimdiki hâl
    satirlar = []
    onceki = None
    for gun in sorted(gunler):
        satir = dict(gunler[gun], gun=gun)
        satir["xp_artis"] = satir["xp"] - onceki["xp"] if onceki else None
        satirlar.append(satir)
        onceki = satir
    return satirlar


@app.route("/gunluk")
def gunluk_sayfasi():
    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return redirect("/")
    kayit = kayit_oturumu(uid)
    liste = savaslar(kayit)
    bilgi = save_info(uid)
    return render_template("gunluk.html", bilgi=bilgi, rutbe=rutbe(bilgi["level"]), portre=portre(kayit),
                           ozet=ozet(kayit, liste), savaslar=liste[:60], ilerleme=ilerleme(uid, kayit),
                           version=version_name, varlik=STATIK_YOL)
