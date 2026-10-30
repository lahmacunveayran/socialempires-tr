"""Sürümü sabitlenmiş Ruffle (Flash öykünücüsü) dosyaları.

Ruffle her açılışta unpkg'den çekilirse oyun internetsiz açılmaz ve yeni bir
sürüm habersiz gelir. Bunun yerine npm paketinin belirli bir sürümü bir kez
indirilir, bütünlüğü (SHA-512) doğrulanır ve download_assets/ruffle/<sürüm>/
altına açılır. WASM dosyaları (~14 MB) bir kez gzip ve (brotli kuruluysa)
brotli ile önceden sıkıştırılır; brotli 11. düzeyde dosya başına ~40 saniye
sürdüğü için istek sırasında yapılamaz, arka planda üretilir.

Bu modül Flask'a bağlı değildir; varliklari_indir.py de kullanır.
"""

import base64
import gzip
import hashlib
import io
import os
import shutil
import tarfile
import tempfile
import threading
import urllib.request

from oyun.yollar import INDIRILEN_DIR

SURUM = "0.7.1"
PAKET_URL = f"https://registry.npmjs.org/@ruffle-rs/ruffle/-/ruffle-{SURUM}.tgz"
PAKET_SHA512 = "6ZWxx/cfX3RoNyQ1AVimECSae4gKqMxdPimOD+chiIcOFiJS0ATGKcjkretxNT03lqNUpiSyJjF55AuvvZ+QeA=="
# Gece sürümleri yalnızca /ruffle-deneme.html sayfasında, unpkg'den denenir.
DENEME_URL = "https://unpkg.com/@ruffle-rs/ruffle@nightly/ruffle.js"

KLASOR = os.path.join(INDIRILEN_DIR, "ruffle", SURUM)
SIKISTIRILACAK = (".js", ".wasm")
TURLER = {".js": "text/javascript", ".wasm": "application/wasm", ".map": "application/json"}

_kilit = threading.Lock()
_brotli_is = None


def hazir_mi():
    return os.path.isfile(os.path.join(KLASOR, "ruffle.js"))


def _paketi_ac(veri):
    """Paketteki dosyaları KLASOR'e yazar (alt klasör ve bağlantılar atlanır)."""
    gecici = tempfile.mkdtemp(prefix="ruffle-", dir=os.path.dirname(KLASOR))
    try:
        with tarfile.open(fileobj=io.BytesIO(veri), mode="r:gz") as tar:
            for uye in tar.getmembers():
                ad = uye.name.split("/", 1)[-1]
                if not uye.isfile() or "/" in ad or ad.startswith(".") or ad.endswith(".map"):
                    continue
                with tar.extractfile(uye) as kaynak, open(os.path.join(gecici, ad), "wb") as hedef:
                    shutil.copyfileobj(kaynak, hedef)
        if not os.path.isfile(os.path.join(gecici, "ruffle.js")):
            raise OSError("Ruffle paketinde ruffle.js yok")
        for ad in os.listdir(gecici):
            if ad.endswith(SIKISTIRILACAK):
                yol = os.path.join(gecici, ad)
                with open(yol, "rb") as f, gzip.open(yol + ".gz", "wb", compresslevel=9) as g:
                    shutil.copyfileobj(f, g)
        shutil.rmtree(KLASOR, ignore_errors=True)
        os.replace(gecici, KLASOR)  # atomik: yarım klasör sunulmaz
    except BaseException:
        shutil.rmtree(gecici, ignore_errors=True)
        raise


def hazirla(veri=None, beklenen=PAKET_SHA512):
    """Ruffle yoksa indirip açar. Başarılıysa True. `veri`: test için paket."""
    if hazir_mi():
        return True
    with _kilit:
        if hazir_mi():
            return True
        os.makedirs(os.path.dirname(KLASOR), exist_ok=True)
        try:
            if veri is None:
                print(f" [+] Ruffle {SURUM} indiriliyor (yalnizca ilk acilista)...")
                with urllib.request.urlopen(PAKET_URL, timeout=120) as yanit:
                    veri = yanit.read()
            ozet = base64.b64encode(hashlib.sha512(veri).digest()).decode()
            if ozet != beklenen:
                print(" ! Ruffle paketinin SHA-512 ozeti tutmuyor; kullanilmadi")
                return False
            _paketi_ac(veri)
        except (OSError, tarfile.TarError) as hata:
            print(f" ! Ruffle hazirlanamadi: {hata}")
            return False
    brotli_baslat()
    return True


def _brotli_uret():
    try:
        import brotli
    except ImportError:
        return
    for ad in sorted(os.listdir(KLASOR)):
        yol = os.path.join(KLASOR, ad)
        if not ad.endswith(SIKISTIRILACAK) or os.path.exists(yol + ".br"):
            continue
        with open(yol, "rb") as f:
            sikisik = brotli.compress(f.read(), quality=11)
        with open(yol + ".br.tmp", "wb") as f:
            f.write(sikisik)
        os.replace(yol + ".br.tmp", yol + ".br")
    print(f" [+] Ruffle {SURUM} brotli ile sikistirildi")


def brotli_baslat(bekle=False):
    """Eksik .br dosyalarını arka planda üretir (brotli paketi kuruluysa)."""
    global _brotli_is
    if not hazir_mi():
        return
    if _brotli_is is None or not _brotli_is.is_alive():
        _brotli_is = threading.Thread(target=_brotli_uret, name="ruffle-brotli", daemon=True)
        _brotli_is.start()
    if bekle:
        _brotli_is.join()


def dosya(ad, kabul_edilen=""):
    """İstenen dosyanın (yol, içerik türü, kodlama) üçlüsü; yoksa None.

    `kabul_edilen`: istemcinin Accept-Encoding başlığı. Önceden sıkıştırılmış
    sürüm varsa ve istemci kabul ediyorsa o döner.
    """
    # Yol istekten değil, klasörün kendi listesinden gelir (izin listesi):
    # "../" gibi adlar listede olmadığı için hiçbir zaman dosya yoluna dönüşmez.
    dosyalar = sunulanlar()
    yol = dosyalar.get(ad)
    if yol is None:
        return None
    tur = TURLER.get(os.path.splitext(yol)[1], "application/octet-stream")
    kabul = {k.split(";")[0].strip() for k in kabul_edilen.lower().split(",")}
    for kodlama, uzanti in (("br", ".br"), ("gzip", ".gz")):
        sikisik = _sikisik(yol, uzanti)
        if kodlama in kabul and sikisik:
            return sikisik, tur, kodlama
    return yol, tur, None


def sunulanlar():
    """{dosya adı: yol}: klasördeki sunulabilir dosyalar (sıkıştırılmış kopyalar hariç)."""
    if not os.path.isdir(KLASOR):
        return {}
    return {ad: os.path.join(KLASOR, ad) for ad in os.listdir(KLASOR)
            if not ad.startswith(".") and not ad.endswith((".gz", ".br", ".tmp"))
            and os.path.isfile(os.path.join(KLASOR, ad))}


def _sikisik(yol, uzanti):
    return yol + uzanti if os.path.isfile(yol + uzanti) else None
