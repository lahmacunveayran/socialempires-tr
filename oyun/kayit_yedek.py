"""Oyun sayfasından tek tıkla imparatorluğu indirme ve başka bilgisayarda yükleme.

Yedek bir JSON dosyasıdır: kayıt dosyasının kendisi metin olarak durur,
yanında SHA-256 özeti bulunur. Böylece geri yüklenen kayıt orijinaliyle bayt
bayt aynı olur. Yükleme sırasında özet, şema ve kimlik çakışması denetlenir;
eski kayıt otomatik olarak .bak dosyasına alınır.
"""

import hashlib
import json
import os
import shutil
from datetime import datetime

from flask import request, session
from werkzeug.utils import safe_join

from oyun.kayit import (all_saves_userid, gecerli_uid, is_valid_village, load_saved_villages,
                        save_lock)
from oyun.sunucu import app
from oyun.yollar import SAVES_DIR

BICIM = "SocialEmpiresTR-yedek"
EN_BUYUK = 32 * 1024 * 1024


def _yol(uid):
    return safe_join(SAVES_DIR, f"{uid}.save.json")


def zarf(uid):
    """Kaydın yedek zarfı (dict)."""
    with save_lock, open(_yol(uid), "rb") as f:
        ham = f.read()
    kayit = json.loads(ham)
    ad = kayit["playerInfo"]["map_names"][kayit["playerInfo"].get("default_map", 0)]
    return {"bicim": BICIM, "surum": 1, "kimlik": uid, "ad": ad,
            "tarih": datetime.now().isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(ham).hexdigest(), "kayit": ham.decode("utf-8")}


def zarfi_ac(veri, oturum_uid):
    """Zarfı denetler; (kimlik, ham bayt) döndürür ya da ValueError (Türkçe ileti)."""
    try:
        zarf_ = json.loads(veri)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Dosya bir imparatorluk yedeği değil.")
    if not isinstance(zarf_, dict) or zarf_.get("bicim") != BICIM or not isinstance(zarf_.get("kayit"), str):
        raise ValueError("Dosya bir imparatorluk yedeği değil.")
    ham = zarf_["kayit"].encode("utf-8")
    if hashlib.sha256(ham).hexdigest() != zarf_.get("sha256"):
        raise ValueError("Yedek bozulmuş: SHA-256 özeti tutmuyor.")
    try:
        kayit = json.loads(ham)
    except ValueError:
        raise ValueError("Yedekteki kayıt okunamadı.")
    if not isinstance(kayit, dict) or not is_valid_village(kayit):
        raise ValueError("Yedekteki kayıt geçerli bir imparatorluk değil.")
    kimlik = str(kayit["playerInfo"].get("pid", ""))
    if kimlik != zarf_.get("kimlik") or not gecerli_uid(kimlik):
        raise ValueError("Yedeğin kimliği tutarsız.")
    if kimlik != oturum_uid and kimlik in all_saves_userid():
        raise ValueError("Bu bilgisayarda aynı kimlikle başka bir imparatorluk var; "
                         "üzerine yazmak için o imparatorlukla giriş yapın.")
    return kimlik, ham


def geri_yukle(kimlik, ham):
    yol = _yol(kimlik)
    with save_lock:
        if os.path.exists(yol):
            shutil.copy2(yol, yol + ".bak")
        gecici = yol + ".tmp"
        with open(gecici, "wb") as f:
            f.write(ham)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    load_saved_villages()


@app.route("/kayit/indir")
def kayit_indir():
    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return ({"hata": "Önce giriş yapın."}, 401)
    veri = zarf(uid)
    ad = "".join(c for c in veri["ad"] if c.isalnum()) or "imparatorluk"
    yanit = app.response_class(json.dumps(veri, ensure_ascii=False), mimetype="application/json")
    yanit.headers["Content-Disposition"] = (
        f"attachment; filename=\"{ad.encode('ascii', 'ignore').decode() or 'imparatorluk'}"
        f"-{veri['tarih'][:10]}.seyedek.json\"")
    return yanit


@app.route("/kayit/yukle", methods=["POST"])
def kayit_yukle():
    dosya = request.files.get("dosya")
    if dosya is None:
        return ({"hata": "Dosya seçilmedi."}, 400)
    veri = dosya.read(EN_BUYUK + 1)
    if len(veri) > EN_BUYUK:
        return ({"hata": "Dosya çok büyük."}, 413)
    try:
        kimlik, ham = zarfi_ac(veri, session.get("USERID"))
    except ValueError as hata:
        return ({"hata": str(hata)}, 400)
    geri_yukle(kimlik, ham)
    session["USERID"] = kimlik
    session.setdefault("GAMEVERSION", "SocialEmpires0926bsec.swf")
    return {"durum": "ok", "kimlik": kimlik}
