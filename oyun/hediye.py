"""Ücretsiz Hediyeler: 7 günlük, giderek büyüyen günlük hediye sandığı.

Bir gün kaçırılınca seri sıfıra değil bir adım geri döner. Hediyeler
depoya (privateState.gifts) yazılır: istemci açıkken kaynakları sunucudan
değiştirmek bir sonraki açılışta geri gitmeye yol açar, depo ise oyun
açılırken okunur.
"""

from datetime import date

from flask import session

from oyun.dunya import turkce_ad
from oyun.kayit import save_lock, save_session, session as kayit_oturumu
from oyun.komutlar import depo_ekle
from oyun.sunucu import app
from oyun.takvim import bugun

# (eşya kimliği, adet): 1. günden 7. güne
ODULLER = [(510, 2), (512, 1), (511, 2), (9102, 1), (9103, 1), (9101, 1), (849, 1)]


def _durum(kayit):
    return kayit["privateState"].setdefault("gunluk_hediye", {"adim": 0, "son": ""})


def sira(durum, gun):
    """Bugün alınacak hediyenin sırası (0-6) ve bugün alınabilir mi."""
    adim = int(durum.get("adim", 0)) % len(ODULLER)
    son = durum.get("son")
    if not son:
        return adim, True
    gecen = (gun - date.fromisoformat(son)).days
    if gecen <= 0:
        return (adim - 1) % len(ODULLER), False
    if gecen >= 2:  # bir gün kaçırıldı: bir adım geri
        adim = max(0, adim - 1)
    return adim, True


def al(kayit, gun):
    """Hediyeyi depoya yazar; (sıra, eşya, adet) ya da bugün alındıysa None."""
    durum = _durum(kayit)
    adim, alinabilir = sira(durum, gun)
    if not alinabilir:
        return None
    esya, adet = ODULLER[adim]
    depo_ekle(kayit, esya, adet)
    durum["adim"] = (adim + 1) % len(ODULLER)
    durum["son"] = gun.isoformat()
    return adim, esya, adet


def _oduller():
    return [{"gun": i + 1, "esya": e, "ad": turkce_ad(e), "adet": a} for i, (e, a) in enumerate(ODULLER)]


@app.route("/hediye")
def hediye_durumu():
    kayit = kayit_oturumu(session.get("USERID", ""))
    if not kayit:
        return ({"hata": "Önce giriş yapın."}, 401)
    adim, alinabilir = sira(_durum(kayit), bugun())
    return {"sira": adim, "alinabilir": alinabilir, "oduller": _oduller()}


@app.route("/hediye/al", methods=["POST"])
def hediye_al():
    uid = session.get("USERID", "")
    kayit = kayit_oturumu(uid)
    if not kayit:
        return ({"hata": "Önce giriş yapın."}, 401)
    with save_lock:
        sonuc = al(kayit, bugun())
        if sonuc is None:
            return ({"hata": "Bugünün hediyesini zaten aldın. Yarın yine gel!"}, 409)
        save_session(uid)
    adim, esya, adet = sonuc
    return {"durum": "ok", "gun": adim + 1, "ad": turkce_ad(esya), "adet": adet,
            "ileti": f"{adet} {turkce_ad(esya)} deponda. Oyunu yeniden açınca yerleştirebilirsin."}
