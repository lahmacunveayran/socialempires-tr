"""Python kurulu olmayan Windows için çift tıkla açılan paket üretir.

Gömülü Python (python.org "embeddable package") + gerekli paketlerin
Windows tekerlekleri + oyun dosyaları + "Social Empires.bat" başlatıcısı tek
bir zip'e konur; yanına SHA-256 özeti yazılır. PyInstaller yerine bu yol
seçildi: derleme yok ve antivirüs yanlış alarmı en az.

Social Point varlıkları pakete konmaz (ilk açılışta indirilir). Ruffle
(MIT/Apache) indirilmişse lisanslarıyla birlikte pakete girer.

Kullanım:
    python araclar/windows_paketi.py [--surum 3.12.10] [--python-zip yol] [--cikti dist]
"""

import argparse
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

# Pakete girecek proje dosyaları (KOK'a göre)
KLASORLER = ["oyun", "templates", "config", "ceviri", "villages", "stub", "mods",
             os.path.join("assets", "fonts")]
DOSYALAR = ["server.py", "ayarlar.json", "requirements.txt", "varliklari_indir.py",
            "LICENSE", "README.md", "FLASH.md"]
ARACLAR = (".py", ".json", ".csv")
ATLANAN = ("__pycache__", ".pyc", ".log")

BASLATICI = r"""@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
title Social Empires Sunucusu
echo ============================================
echo  Social Empires Turkce
echo ============================================
echo Sunucu baslatiliyor. Oyun tarayicida kendiliginden acilacak:
echo   http://127.0.0.1:5050/
echo Oyunu kapatmak icin bu pencereyi kapatin.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$u='http://127.0.0.1:5050/saglik/hazir'; for($i=0;$i -lt 240;$i++){ try { $r=Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 1; if($r.StatusCode -eq 200){ Start-Process 'http://127.0.0.1:5050/'; break } } catch {}; Start-Sleep -Milliseconds 500 }"
"%~dp0python\python.exe" server.py
pause
"""

BENIOKU = """Social Empires Türkçe - Windows paketi
=====================================

1. Zip'i bir klasöre açın (ör. Belgeler\\SocialEmpires).
2. "Social Empires.bat" dosyasına çift tıklayın. Python kurmanız gerekmez.
3. Tarayıcı kendiliğinden açılır: http://127.0.0.1:5050/

İlk açılışta oyun varlıkları internetten indirilir; sonra internet gerekmez.
Kayıtlarınız "saves" klasöründedir.

Windows "Windows bilgisayarınızı korudu" (SmartScreen) derse:
  "Ek bilgi" bağlantısına, sonra "Yine de çalıştır" düğmesine basın.
Paket imzasızdır (imza sertifikası yılda 200-600 dolar). Dosyanın
değişmediğini, yanındaki .sha256 dosyasındaki özetle PowerShell'de
denetleyebilirsiniz:
  Get-FileHash .\\{zip} -Algorithm SHA256
"""


def python_zip(surum, yol=None):
    if yol:
        with open(yol, "rb") as f:
            return f.read()
    url = f"https://www.python.org/ftp/python/{surum}/python-{surum}-embed-amd64.zip"
    print(f"[+] Gomulu Python indiriliyor: {url}")
    with urllib.request.urlopen(url, timeout=300) as yanit:
        return yanit.read()


def tekerlekler(hedef, surum):
    kisa = ".".join(surum.split(".")[:2])
    komut = [sys.executable, "-m", "pip", "download", "--quiet", "--only-binary=:all:",
             "--platform", "win_amd64", "--python-version", kisa, "--implementation", "cp",
             "-d", hedef, "-r", os.path.join(KOK, "requirements.txt"),
             # pip işaretleri bu makineye göre değerlendirir: Windows'a özgü bağımlılık
             "colorama"]
    print("[+] Windows paketleri indiriliyor (pip download)...")
    subprocess.check_call(komut)
    return [os.path.join(hedef, ad) for ad in sorted(os.listdir(hedef)) if ad.endswith(".whl")]


def _ekle(z, kaynak, hedef):
    if os.path.isdir(kaynak):
        for klasor, alt, dosyalar in os.walk(kaynak):
            alt[:] = [a for a in alt if a not in ATLANAN]
            for ad in dosyalar:
                if not ad.endswith(ATLANAN):
                    yol = os.path.join(klasor, ad)
                    z.write(yol, os.path.join(hedef, os.path.relpath(yol, kaynak)))
    elif os.path.exists(kaynak):
        z.write(kaynak, hedef)


def paketle(python_veri, tekerlek_yollari, cikti, ad):
    os.makedirs(cikti, exist_ok=True)
    zip_yolu = os.path.join(cikti, f"{ad}.zip")
    kok = ad
    with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        # Gömülü Python: ._pth dosyası site-packages'ı ve oyun kökünü yola ekler.
        with zipfile.ZipFile(io.BytesIO(python_veri)) as py:
            pth = [n for n in py.namelist() if n.endswith("._pth")]
            if not pth:
                raise SystemExit("Gomulu Python zip'inde ._pth dosyasi yok")
            for n in py.namelist():
                if n in pth:
                    satirlar = [s for s in py.read(n).decode().splitlines() if s and not s.startswith("#")]
                    satirlar += ["Lib\\site-packages", "..", "import site"]
                    z.writestr(f"{kok}/python/{n}", "\r\n".join(satirlar) + "\r\n")
                else:
                    z.writestr(f"{kok}/python/{n}", py.read(n))
        for tekerlek in tekerlek_yollari:
            with zipfile.ZipFile(tekerlek) as t:
                for n in t.namelist():
                    z.writestr(f"{kok}/python/Lib/site-packages/{n}", t.read(n))
        for klasor in KLASORLER:
            _ekle(z, os.path.join(KOK, klasor), f"{kok}/{klasor.replace(os.sep, '/')}")
        for dosya in DOSYALAR:
            _ekle(z, os.path.join(KOK, dosya), f"{kok}/{dosya}")
        for dosya in sorted(os.listdir(os.path.join(KOK, "araclar"))):
            if dosya.endswith(ARACLAR):
                z.write(os.path.join(KOK, "araclar", dosya), f"{kok}/araclar/{dosya}")
        from oyun import ruffle
        if ruffle.hazir_mi():
            _ekle(z, ruffle.KLASOR, f"{kok}/download_assets/ruffle/{ruffle.SURUM}")
        z.writestr(f"{kok}/Social Empires.bat", BASLATICI.replace("\n", "\r\n"))
        z.writestr(f"{kok}/BENIOKU.txt", BENIOKU.replace("{zip}", f"{ad}.zip").replace("\n", "\r\n"))
    with open(zip_yolu, "rb") as f:
        ozet = hashlib.sha256(f.read()).hexdigest()
    with open(zip_yolu + ".sha256", "w", encoding="ascii") as f:
        f.write(f"{ozet}  {ad}.zip\n")
    return zip_yolu, ozet


def main():
    from oyun.surum import version_code
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--surum", default="3.12.10", help="gömülü Python sürümü")
    ap.add_argument("--python-zip", help="önceden indirilmiş python-*-embed-amd64.zip")
    ap.add_argument("--cikti", default=os.path.join(KOK, "dist"))
    ap.add_argument("--ad", help="zip adı (varsayılan: SocialEmpiresTR-<sürüm>-windows)")
    arg = ap.parse_args()
    gecici = tempfile.mkdtemp(prefix="se-paket-")
    try:
        veri = python_zip(arg.surum, arg.python_zip)
        zip_yolu, ozet = paketle(veri, tekerlekler(gecici, arg.surum), arg.cikti,
                                 arg.ad or f"SocialEmpiresTR-{version_code}-windows")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print(f"[+] {zip_yolu} ({os.path.getsize(zip_yolu) / 1e6:.1f} MB)")
    print(f"    SHA-256: {ozet}")


if __name__ == "__main__":
    main()
