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

from oyun.kayit import (all_saves_userid, gecerli_uid, kaydi_dogrula, load_saved_villages,
                        save_lock)
from oyun import kaynaklar
from oyun.sunucu import app
from oyun.yollar import SAVES_DIR

BICIM = "SocialEmpiresTR-yedek"

# Kullanıcıya gösterilen iletiler sabittir; istisnanın metni dışarı verilmez.
HATALAR = {
    "bicim": "Dosya bir imparatorluk yedeği değil.",
    "ozet": "Yedek bozulmuş: SHA-256 özeti tutmuyor.",
    "okunamadi": "Yedekteki kayıt okunamadı.",
    "sema": "Yedekteki kayıt geçerli bir imparatorluk değil.",
    "kimlik": "Yedeğin kimliği tutarsız.",
    "cakisma": "Bu bilgisayarda aynı kimlikle başka bir imparatorluk var; "
               "üzerine yazmak için o imparatorlukla giriş yapın.",
}


class YedekHatasi(ValueError):
    """`kod`: HATALAR anahtarı."""

    def __init__(self, kod):
        super().__init__(kod)
        self.kod = kod
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
    """Zarfı denetler; (kimlik, ham bayt) döndürür ya da YedekHatasi."""
    try:
        zarf_ = json.loads(veri)
    except (ValueError, UnicodeDecodeError):
        raise YedekHatasi("bicim")
    if not isinstance(zarf_, dict) or zarf_.get("bicim") != BICIM or not isinstance(zarf_.get("kayit"), str):
        raise YedekHatasi("bicim")
    ham = zarf_["kayit"].encode("utf-8")
    if hashlib.sha256(ham).hexdigest() != zarf_.get("sha256"):
        raise YedekHatasi("ozet")
    try:
        kayit = json.loads(ham)
    except ValueError:
        raise YedekHatasi("okunamadi")
    try:
        kaydi_dogrula(kayit)  # sunucunun bir sonraki açılışını bozacak kayıt içeri alınmaz
    except ValueError:
        raise YedekHatasi("sema")
    kimlik = str(kayit["playerInfo"].get("pid", ""))
    if kimlik != zarf_.get("kimlik") or not gecerli_uid(kimlik):
        raise YedekHatasi("kimlik")
    if kimlik != oturum_uid and kimlik in all_saves_userid():
        raise YedekHatasi("cakisma")
    return kimlik, ham


def geri_yukle(kimlik, ham):
    yol = _yol(kimlik)
    with save_lock:
        if os.path.exists(yol):
            shutil.copyfile(yol, yol + ".bak")  # copy2 değil: Android öznitelik kopyalamayı reddeder
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
    except YedekHatasi as hata:
        return ({"hata": HATALAR.get(hata.kod, HATALAR["bicim"])}, 400)
    geri_yukle(kimlik, ham)
    session["USERID"] = kimlik
    session["GAMEVERSION"] = kaynaklar.ISTEMCI
    return {"durum": "ok"}
