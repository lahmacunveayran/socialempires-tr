"""Yerel hile paneli (/cheat): kaynak, seviye, kalkan ve yedek işlemleri.

Yalnızca bu bilgisayardan (127.0.0.1) ve aynı kökenden çağrılabilir.
"""

from flask import redirect, render_template, request, session

from oyun.config import get_game_config
from oyun.ekonomi import timestamp_now
from oyun.kayit import (all_saves_userid, backup_session, save_info, save_lock, save_session,
                        session as kayit_oturumu)
from oyun.sunucu import app
from oyun.surum import version_name


def _hile_izinli():
    """Panelin yalnızca yerel makineden ve aynı kökenden çağrılmasını sağlar."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return False
    koken = request.headers.get("Origin")
    if koken and koken.rstrip("/") != request.host_url.rstrip("/"):
        return False
    return True


def _kayit_ozeti(kayit):
    harita = kayit["maps"][0]
    return {
        "seviye": harita["level"],
        "xp": harita["xp"],
        "altin": harita["coins"],
        "odun": harita["wood"],
        "tas": harita["stone"],
        "yemek": harita["food"],
        "cash": kayit["playerInfo"]["cash"],
    }


@app.route("/cheat")
def cheat_sayfasi():
    if not _hile_izinli():
        return ("", 403)
    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return redirect("/")
    from oyun.dunya import rutbe
    from oyun.sunucu import STATIK_YOL
    bilgi = save_info(uid)
    return render_template("cheat.html", save_info=bilgi, version=version_name, varlik=STATIK_YOL,
                           rutbe=rutbe(bilgi["level"]), ozet=_kayit_ozeti(kayit_oturumu(uid)))


@app.route("/cheat/uygula", methods=["POST"])
def cheat_uygula():
    if not _hile_izinli():
        return ({"hata": "yasak"}, 403)
    if not request.is_json:
        return ({"hata": "JSON gerekli"}, 400)

    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return ({"hata": "oturum yok"}, 401)

    veri = request.get_json(silent=True) or {}
    islem = veri.get("islem")
    kayit = kayit_oturumu(uid)
    harita = kayit["maps"][0]

    try:
        with save_lock:
            if islem == "kaynak":
                tur = veri.get("tur")
                miktar = int(veri.get("miktar", 1000))
                if miktar <= 0 or miktar > 10 ** 9:
                    return ({"hata": "gecersiz miktar"}, 400)
                if tur == "cash":
                    kayit["playerInfo"]["cash"] = int(kayit["playerInfo"].get("cash", 0)) + miktar
                elif tur in ("wood", "stone", "food", "coins"):
                    harita[tur] = int(harita.get(tur, 0)) + miktar
                else:
                    return ({"hata": "gecersiz kaynak"}, 400)

            elif islem == "seviye":
                seviyeler = get_game_config()["levels"]
                yeni = int(veri.get("delta", 1)) + int(harita["level"])
                yeni = max(0, min(yeni, len(seviyeler) - 1))
                harita["level"] = yeni
                harita["xp"] = int(seviyeler[yeni]["exp_required"])

            elif islem == "max_seviye":
                seviyeler = get_game_config()["levels"]
                yeni = len(seviyeler) - 1
                harita["level"] = yeni
                harita["xp"] = int(seviyeler[yeni]["exp_required"])

            elif islem == "egitim":
                kayit["playerInfo"]["completed_tutorial"] = 1
                kayit["privateState"]["dragonNestActive"] = 1

            elif islem == "kalkan":
                saat = max(1, min(72, int(veri.get("saat", 12))))
                kayit.setdefault("privateState", {})["shield_until"] = timestamp_now() + saat * 3600

            elif islem == "yedek":
                backup_session(uid)

            else:
                return ({"hata": "bilinmeyen islem"}, 400)

            save_session(uid)
    except (KeyError, ValueError, TypeError) as hata:
        print("[HILE HATA]", hata)
        return ({"hata": "islem gecersiz"}, 400)

    print(f"[HILE] {islem} {veri} -> ok")
    return ({"ok": True, "ozet": _kayit_ozeti(kayit)}, 200)
