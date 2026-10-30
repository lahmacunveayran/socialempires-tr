"""Android uygulamasına girecek oyun dosyalarını Gradle derlemesinden önce hazırlar.

android/app/build/oyun-verisi/ : Chaquopy'nin Python kaynak klasörü (oyun/, templates/, config/...,
                                 araclar/ paket olarak, Ruffle paketi). Uygulamada salt okunurdur.
android/app/build/oyun-res/    : uygulama simgesi (oyunun kendi simgesi, templates/img/simge-192.png).

Social Point varlıkları uygulamaya konmaz; ilk açılışta indirilir (Windows paketiyle aynı).

Kullanım:
    python araclar/android_paketi.py [--cikti android/app/build] [--ruffle yol|yok]
"""

import argparse
import base64
import hashlib
import os
import shutil
import sys
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from oyun import ruffle  # noqa: E402

KLASORLER = ["oyun", "templates", "config", "ceviri", "villages", "stub", "mods",
             os.path.join("assets", "fonts")]
DOSYALAR = ["ayarlar.json", "LICENSE"]
ARACLAR = (".py", ".json")
ATLANAN = shutil.ignore_patterns("__pycache__", "*.pyc", "*.log")


def ruffle_paketi(kaynak=None):
    if kaynak:
        with open(kaynak, "rb") as f:
            veri = f.read()
    else:
        print(f"[+] Ruffle indiriliyor: {ruffle.PAKET_URL}")
        with urllib.request.urlopen(ruffle.PAKET_URL, timeout=300) as yanit:
            veri = yanit.read()
    ozet = base64.b64encode(hashlib.sha512(veri).digest()).decode()
    if ozet != ruffle.PAKET_SHA512:
        raise SystemExit("Ruffle paketinin SHA-512 özeti tutmuyor")
    return veri


def hazirla(cikti, ruffle_kaynak=None):
    veri_klasoru = os.path.join(cikti, "oyun-verisi")
    res_klasoru = os.path.join(cikti, "oyun-res")
    for klasor in (veri_klasoru, res_klasoru):
        shutil.rmtree(klasor, ignore_errors=True)

    for ad in KLASORLER:
        shutil.copytree(os.path.join(KOK, ad), os.path.join(veri_klasoru, ad), ignore=ATLANAN)
    for ad in DOSYALAR:
        shutil.copyfile(os.path.join(KOK, ad), os.path.join(veri_klasoru, ad))
    araclar = os.path.join(veri_klasoru, "araclar")
    os.makedirs(araclar)
    for ad in sorted(os.listdir(os.path.join(KOK, "araclar"))):
        if ad.endswith(ARACLAR):
            shutil.copyfile(os.path.join(KOK, "araclar", ad), os.path.join(araclar, ad))
    # Chaquopy modülleri APK'dan yükler; araclar/ gerçek bir paket olunca içe aktarılabilir
    open(os.path.join(araclar, "__init__.py"), "w").close()

    if ruffle_kaynak != "yok":
        with open(os.path.join(veri_klasoru, "ruffle-paketi.tgz"), "wb") as f:
            f.write(ruffle_paketi(ruffle_kaynak))

    simge = os.path.join(res_klasoru, "mipmap-xxxhdpi")
    os.makedirs(simge)
    shutil.copyfile(os.path.join(KOK, "templates", "img", "simge-192.png"), os.path.join(simge, "ic_launcher.png"))
    print(f"[+] Android oyun dosyalari hazir: {veri_klasoru}")
    return veri_klasoru


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cikti", default=os.path.join(KOK, "android", "app", "build"))
    ap.add_argument("--ruffle", help="indirilmiş Ruffle .tgz yolu ya da 'yok'")
    secenek = ap.parse_args()
    hazirla(secenek.cikti, secenek.ruffle)
