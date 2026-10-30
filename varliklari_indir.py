# -*- coding: utf-8 -*-
"""Oyun varlıklarını (SWF, görsel, müzik; ~1,3 GB) assets/ altına indirir.

Varlıklar boyutları yüzünden depoda tutulmaz. Sunucu eksik dosyaları
oynarken tek tek indirebilir; bu betik ise hepsini bir kerede indirir,
böylece oyun internetsiz ve daha hızlı açılır.

Kaynak: AcidCaos/socialemperors deposundaki assets/ klasörü.
assets/ altında zaten bulunan dosyalara (ör. Türkçe fontlar) dokunulmaz.

Oyunu tarayıcıda çalıştıran Ruffle'ın sabitlenmiş sürümü de indirilir.

Kullanım:
    python varliklari_indir.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

DEPO = "AcidCaos/socialemperors"
DAL = "main"
KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(KOK, "assets")


def _kopyala(kaynak_kok):
    """kaynak_kok altındaki dosyaları, var olanları ezmeden HEDEF'e kopyalar."""
    yeni = 0
    for klasor, _, dosyalar in os.walk(kaynak_kok):
        for ad in dosyalar:
            kaynak = os.path.join(klasor, ad)
            hedef = os.path.join(HEDEF, os.path.relpath(kaynak, kaynak_kok))
            if os.path.exists(hedef):
                continue
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copy2(kaynak, hedef)
            yeni += 1
    return yeni


def git_ile():
    if shutil.which("git") is None:
        return False
    gecici = tempfile.mkdtemp(prefix="se-assets-")
    try:
        print("[1/2] git ile indiriliyor (bu biraz surebilir)...")
        komutlar = [
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
             "-b", DAL, f"https://github.com/{DEPO}.git", gecici],
            ["git", "-C", gecici, "sparse-checkout", "set", "assets"],
        ]
        for komut in komutlar:
            if subprocess.call(komut) != 0:
                return False
        print("[2/2] assets/ klasorune kopyalaniyor...")
        print(f"[+] {_kopyala(os.path.join(gecici, 'assets'))} yeni dosya eklendi.")
        return True
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def http_ile():
    print("[1/2] Dosya listesi aliniyor...")
    url = f"https://api.github.com/repos/{DEPO}/git/trees/{DAL}?recursive=1"
    with urllib.request.urlopen(url, timeout=60) as yanit:
        agac = json.load(yanit)
    dosyalar = [o["path"] for o in agac["tree"]
                if o["type"] == "blob" and o["path"].startswith("assets/")]
    print(f"[2/2] {len(dosyalar)} dosya kontrol ediliyor...")
    yeni = 0
    for i, yol in enumerate(dosyalar, 1):
        hedef = os.path.join(KOK, *yol.split("/"))
        if os.path.exists(hedef):
            continue
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        ham = f"https://raw.githubusercontent.com/{DEPO}/{DAL}/{urllib.parse.quote(yol)}"
        gecici = hedef + ".indir"
        try:
            with urllib.request.urlopen(ham, timeout=60) as yanit, open(gecici, "wb") as f:
                shutil.copyfileobj(yanit, f)
            os.replace(gecici, hedef)
            yeni += 1
        except OSError as hata:
            print(f" ! {yol}: {hata}")
            if os.path.exists(gecici):
                os.remove(gecici)
        if i % 200 == 0:
            print(f"    {i}/{len(dosyalar)}")
    print(f"[+] {yeni} yeni dosya eklendi.")
    return True


if __name__ == "__main__":
    if not git_ile():
        print("git kullanilamadi; dosyalar tek tek indirilecek.")
        http_ile()
    sys.path.insert(0, KOK)
    from oyun import ruffle
    if ruffle.hazirla():
        print(f"[+] Ruffle {ruffle.SURUM} hazir; sikistiriliyor (bir dakika kadar surebilir)...")
        ruffle.brotli_baslat(bekle=True)
    if not os.path.exists(os.path.join(HEDEF, "flash", "SocialEmpires0926bsec.swf")):
        print("UYARI: oyun dosyasi hala eksik; internet baglantinizi kontrol edin.")
        sys.exit(1)
    print("Tamam. Oyun varliklari hazir.")
