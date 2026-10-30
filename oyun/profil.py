"""Profil resmi (/profil): oyuncu kendi fotoğrafını koyar.

Fotoğraf tarayıcıda kare kırpılıp 256×256 JPEG'e küçültülür, sunucu yalnızca JPEG
olduğunu ve boyutunu denetler (Python'da resim kütüphanesi gerekmez, Android'de de çalışır).
Resim kaydın içinde, oyuna gönderilmeyen `profil_resmi` alanında saklanır: yedek ve
Wi-Fi ile taşıma onu da götürür. playerInfo.pic resmin adresini gösterir; oyun içi
komşu şeridi, Şeref Kürsüsü ve günlük bu adresi kullanır.
"""

import base64
import binascii
import time

from flask import Response, abort, redirect, render_template, request, session

from oyun.diyar import kursuyu_tazele, portre
from oyun.kayit import all_saves_userid, gecerli_uid, save_info, save_lock, save_session
from oyun.kayit import session as kayit_oturumu
from oyun.sunucu import app
from oyun.surum import version_name

EN_BUYUK = 300_000  # bayt; 256×256 JPEG genelde 20-40 KB
ADRES = "/profil/resim/{}.jpg"


def _oyuncu():
    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return None, None
    return uid, kayit_oturumu(uid)


def jpeg_mi(veri):
    return len(veri) > 4 and veri[:3] == b"\xff\xd8\xff" and veri.rstrip(b"\x00")[-2:] == b"\xff\xd9"


@app.route("/profil")
def profil_sayfasi():
    uid, kayit = _oyuncu()
    if not uid:
        return redirect("/")
    return render_template("profil.html", bilgi=save_info(uid), portre=portre(kayit),
                           kendi=bool(kayit.get("profil_resmi")), version=version_name)


@app.route("/profil/resim", methods=["POST"])
def profil_resmi_yukle():
    uid, kayit = _oyuncu()
    if not uid:
        return {"hata": "Önce bir imparatorluğa giriş yapın."}, 403
    dosya = request.files.get("resim")
    veri = dosya.read(EN_BUYUK + 1) if dosya else b""
    if len(veri) > EN_BUYUK:
        return {"hata": "Resim çok büyük."}, 400
    if not jpeg_mi(veri):
        return {"hata": "Resim okunamadı; başka bir fotoğraf deneyin."}, 400
    with save_lock:
        kayit["profil_resmi"] = base64.b64encode(veri).decode("ascii")
        kayit["playerInfo"]["pic"] = ADRES.format(uid) + f"?v={int(time.time())}"
        save_session(uid)
    kursuyu_tazele()
    return {"pic": kayit["playerInfo"]["pic"]}


@app.route("/profil/resim/sil", methods=["POST"])
def profil_resmi_sil():
    uid, kayit = _oyuncu()
    if not uid:
        return {"hata": "Önce bir imparatorluğa giriş yapın."}, 403
    with save_lock:
        kayit.pop("profil_resmi", None)
        kayit["playerInfo"]["pic"] = ""
        save_session(uid)
    kursuyu_tazele()
    return {"pic": portre(kayit)}


@app.route("/profil/resim/<uid>.jpg")
def profil_resmi(uid):
    kayit = kayit_oturumu(uid) if gecerli_uid(uid) else None
    try:
        veri = base64.b64decode((kayit or {}).get("profil_resmi") or "", validate=True)
    except (binascii.Error, ValueError):
        veri = b""
    if not jpeg_mi(veri):
        abort(404)
    return Response(veri, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})
