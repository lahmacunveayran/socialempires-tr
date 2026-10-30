"""Çevrimdışı paket (/cevrimdisi): oyun varlıklarını bir kerede indirir, sonra oyun internetsiz oynanır.

Liste config/onindirme.tsv'dedir (araclar/onindirme_listesi.py üretir). İki boy:
- temel (~180 MB): oyun, arayüz, efekt, müzik, mağazadaki eşyaların ve büyülerin çizimleri,
- tam (~1,1 GB): yapılandırmadaki bütün çizimler (mağazada olmayan ödül ve bot binaları dahil).
İnmiş dosyalar atlanır; yarıda kalırsa (uygulama kapanır, internet gider) kaldığı yerden sürer. İndirme
oyunun kendi indiricisini kullanır (varliklar.varlik_yolu). Başlatıp durdurmak yalnızca bu cihazdan yapılır.
"""

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import render_template, request

from oyun import varliklar
from oyun.hile import _hile_izinli as yerel_mi
from oyun.sunucu import app
from oyun.surum import version_name
from oyun.yollar import ASSETS_DIR, CONFIG_DIR, INDIRILEN_DIR

LISTE = os.path.join(CONFIG_DIR, "onindirme.tsv")
PAKETLER = {"temel": 1, "tam": 2}  # paket -> en yüksek öncelik
ES_ZAMANLI = 6
PAY = 50 * 1024 * 1024  # indirmeden sonra diskte kalması gereken boşluk

_kilit = threading.Lock()
_durum = {"calisiyor": False, "paket": None, "basarisiz": 0, "hata": None}
_dur = threading.Event()
_liste_onbellegi = None


def liste():
    """[(yol, bayt, öncelik)], indirme sırasıyla."""
    global _liste_onbellegi
    if _liste_onbellegi is None:
        with open(LISTE, encoding="utf-8") as f:
            _liste_onbellegi = [(y, int(b), int(o)) for y, b, o in
                                (s.rstrip("\n").split("\t") for s in f if s.strip() and not s.startswith("#"))]
    return _liste_onbellegi


def inmis_mi(yol):
    return (os.path.isfile(os.path.join(ASSETS_DIR, yol))
            or os.path.isfile(os.path.join(varliklar.INDIRILEN_VARLIKLAR, yol)))


def ozet():
    paketler = {}
    for ad, sinir in PAKETLER.items():
        dosyalar = [(y, b) for y, b, o in liste() if o <= sinir]
        inen = [(y, b) for y, b in dosyalar if inmis_mi(y)]
        paketler[ad] = {"dosya": len(dosyalar), "bayt": sum(b for _, b in dosyalar),
                        "inen_dosya": len(inen), "inen_bayt": sum(b for _, b in inen)}
    return dict(_durum, paketler=paketler)


def _bos_alan():
    klasor = INDIRILEN_DIR
    while not os.path.isdir(klasor) and os.path.dirname(klasor) != klasor:
        klasor = os.path.dirname(klasor)
    return shutil.disk_usage(klasor).free


def _indir(eksikler):
    try:
        with ThreadPoolExecutor(ES_ZAMANLI) as havuz:
            for sonuc in havuz.map(lambda y: None if _dur.is_set() else varliklar.varlik_yolu(y), eksikler):
                if sonuc is None and not _dur.is_set():
                    _durum["basarisiz"] += 1
    except Exception as hata:  # indirme iş parçacığı sunucuyu düşürmesin
        _durum["hata"] = str(hata)
    finally:
        _durum["calisiyor"] = False


def baslat(paket):
    """İndirmeyi arka planda başlatır. (tamam, hata_kodu)"""
    if paket not in PAKETLER:
        return False, "paket"
    with _kilit:
        if _durum["calisiyor"]:
            return False, "suruyor"
        eksikler = [(y, b) for y, b, o in liste() if o <= PAKETLER[paket] and not inmis_mi(y)]
        if sum(b for _, b in eksikler) + PAY > _bos_alan():
            return False, "yer"
        _dur.clear()
        _durum.update(calisiyor=True, paket=paket, basarisiz=0, hata=None)
        threading.Thread(target=_indir, args=([y for y, _ in eksikler],), name="cevrimdisi-paket",
                         daemon=True).start()
    return True, None


@app.route("/cevrimdisi")
def cevrimdisi_sayfasi():
    return render_template("cevrimdisi.html", yerel=yerel_mi(), version=version_name)


@app.route("/cevrimdisi/durum")
def cevrimdisi_durum():
    return ozet()


@app.route("/cevrimdisi/baslat", methods=["POST"])
def cevrimdisi_baslat():
    if not yerel_mi():
        return {"hata": "yerel"}, 403
    tamam, hata = baslat(request.form.get("paket", ""))
    return (ozet(), 202) if tamam else ({**ozet(), "hata": hata}, 409 if hata != "paket" else 400)


@app.route("/cevrimdisi/durdur", methods=["POST"])
def cevrimdisi_durdur():
    if not yerel_mi():
        return {"hata": "yerel"}, 403
    _dur.set()
    return ozet()
