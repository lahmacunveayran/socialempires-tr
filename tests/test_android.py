"""Android uygulaması: yazılabilir klasör, Python girişi, oyun dosyalarının hazırlanması (DAG-05)."""

import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ortak import KOK

ANDROID = os.path.join(KOK, "android")
GIRIS = os.path.join(ANDROID, "app", "src", "main", "python", "android_giris.py")


def modul(ad, yol):
    tanim = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(tanim)
    tanim.loader.exec_module(m)
    return m


class TabanDizini(unittest.TestCase):
    def test_yazilabilir_klasor_ortam_degiskeninden(self):
        with tempfile.TemporaryDirectory() as taban:
            ortam = {k: v for k, v in os.environ.items() if k != "SE_KAYIT_DIZINI"}
            ortam["SE_TABAN_DIZINI"] = taban
            cikti = subprocess.run(
                [sys.executable, "-c", "import json; from oyun import yollar as y; print(json.dumps("
                 "[y.BASE_DIR, y.SAVES_DIR, y.INDIRILEN_DIR, y.AYARLAR, y.MODS_DIR, y.TEMPLATES_DIR]))"],
                cwd=KOK, env=ortam, capture_output=True, text=True, check=True).stdout
            base, kayit, indirilen, ayar, modlar, sablon = json.loads(cikti)
            self.assertEqual(base, taban)
            self.assertEqual(kayit, os.path.join(taban, "saves"))
            self.assertEqual(indirilen, os.path.join(taban, "download_assets"))
            self.assertEqual(ayar, os.path.join(taban, "ayarlar.json"))
            self.assertEqual(modlar, os.path.join(taban, "mods"))
            self.assertEqual(sablon, os.path.join(KOK, "templates"))  # oyun dosyaları yerinde okunur


class AndroidGirisi(unittest.TestCase):
    def setUp(self):
        self.eski = os.environ.get("SE_TABAN_DIZINI")
        self.giris = modul("android_giris", GIRIS)

    def tearDown(self):
        if self.eski is None:
            os.environ.pop("SE_TABAN_DIZINI", None)
        else:
            os.environ["SE_TABAN_DIZINI"] = self.eski

    def test_ilk_acilista_ayar_ve_modlar_kopyalanir(self):
        with tempfile.TemporaryDirectory() as d:
            taban = os.path.join(d, "socialempires")
            self.giris.hazirla(taban, kok=KOK)
            self.assertEqual(os.environ["SE_TABAN_DIZINI"], taban)
            with open(os.path.join(taban, "ayarlar.json"), encoding="utf-8") as f:
                self.assertFalse(json.load(f)["ev_agi"])  # uygulamada sunucu yalnızca cihazın kendisine açık
            self.assertEqual(sorted(os.listdir(os.path.join(taban, "mods"))),
                             sorted(os.listdir(os.path.join(KOK, "mods"))))

    def test_guncellemede_kullanici_ayarlarina_dokunulmaz(self):
        with tempfile.TemporaryDirectory() as taban:
            with open(os.path.join(taban, "ayarlar.json"), "w", encoding="utf-8") as f:
                f.write('{"zaman_olcegi": 1.0}')
            os.makedirs(os.path.join(taban, "mods"))
            self.giris.hazirla(taban, kok=KOK)
            with open(os.path.join(taban, "ayarlar.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"zaman_olcegi": 1.0})
            self.assertEqual(os.listdir(os.path.join(taban, "mods")), [])


    def test_android_oznitelik_kopyalamayi_reddetse_de_kurulur(self):
        # Gerçek cihazda (emülatör, Android 14) copytree SELinux özniteliğini kopyalayamayıp EACCES ile düştü
        def reddet(*a, **k):
            raise PermissionError(13, "Permission denied")
        with tempfile.TemporaryDirectory() as d, mock.patch.object(shutil, "copystat", reddet):
            taban = os.path.join(d, "socialempires")
            self.giris.hazirla(taban, kok=KOK)
            self.assertEqual(sorted(os.listdir(os.path.join(taban, "mods"))),
                             sorted(os.listdir(os.path.join(KOK, "mods"))))


class Oznitelikler(unittest.TestCase):
    def test_calisan_kod_oznitelik_kopyalamaz(self):
        # copy2/copytree/copystat Android'de EACCES verir; çalışma anındaki kod yalnızca içerik kopyalar
        dosyalar = glob.glob(os.path.join(KOK, "oyun", "*.py")) + [GIRIS,
                                                                  os.path.join(KOK, "araclar", "bot_koy_uret.py")]
        for yol in dosyalar:
            with open(yol, encoding="utf-8") as f:
                kod = f.read()
            self.assertIsNone(re.search(r"shutil\.(copy2|copytree|copystat|copy)\(", kod), yol)


class KisitliGpu(unittest.TestCase):
    def test_256_uniformlu_gpuda_ruffle_webgl_cizicisi(self):
        # Emülatörde (ve birçok mobil GPU'da) wgpu-webgl, 256 köşe uniform sınırını aşıp çöktü (DAG-07)
        with open(os.path.join(KOK, "templates", "js", "oyun.js"), encoding="utf-8") as f:
            kod = f.read()
        self.assertIn("MAX_VERTEX_UNIFORM_VECTORS) <= 256", kod)
        self.assertIn('preferredRenderer = "webgl"', kod)


class OyunDosyalari(unittest.TestCase):
    def test_hazirlanan_dosyalar(self):
        paketci = modul("android_paketi", os.path.join(KOK, "araclar", "android_paketi.py"))
        with tempfile.TemporaryDirectory() as cikti:
            veri = paketci.hazirla(cikti, "yok")
            for yol in ("oyun/sunucu.py", "templates/oyun.html", "config/game_config_20120826.json",
                        "villages/initial.json", "ayarlar.json", "araclar/__init__.py",
                        "araclar/bot_koy_uret.py", "araclar/unit_templates.json", "assets/fonts"):
                self.assertTrue(os.path.exists(os.path.join(veri, yol)), yol)
            self.assertFalse(os.path.exists(os.path.join(veri, "tests")))
            for kok, klasorler, dosyalar in os.walk(veri):
                self.assertNotIn("__pycache__", klasorler, kok)
            self.assertTrue(os.path.isfile(os.path.join(cikti, "oyun-res", "mipmap-xxxhdpi", "ic_launcher.png")))


class Proje(unittest.TestCase):
    def oku(self, *yol):
        with open(os.path.join(ANDROID, *yol), encoding="utf-8") as f:
            return f.read()

    def test_paket_adlari_tutarli(self):
        gradle = self.oku("app", "build.gradle.kts")
        ad = re.search(r'namespace = "([\w.]+)"', gradle).group(1)
        self.assertIn(f'applicationId = "{ad}"', gradle)
        java = os.path.join(ANDROID, "app", "src", "main", "java", *ad.split("."), "MainActivity.java")
        with open(java, encoding="utf-8") as f:
            self.assertIn(f"package {ad};", f.read())
        self.assertIn('android:name=".MainActivity"', self.oku("app", "src", "main", "AndroidManifest.xml"))
        self.assertIn(f"PAKET={ad}", self.oku("sinama.sh"))

    def test_python_surumu_ci_ile_ayni(self):
        # Chaquopy, uygulamanın Python sürümünü derleme makinesinde de ister
        surum = re.search(r'version = "(3\.\d+)"', self.oku("app", "build.gradle.kts")).group(1)
        with open(os.path.join(KOK, ".github", "workflows", "android.yml"), encoding="utf-8") as f:
            self.assertIn(f'python-version: "{surum}"', f.read())

    def test_python_bagimliliklari_requirements_ile_ayni(self):
        with open(os.path.join(KOK, "requirements.txt"), encoding="utf-8") as f:
            gerekli = {s.strip().lower() for s in f if s.strip() and not s.startswith("#")}
        kurulan = set(re.findall(r'install\("([\w-]+)"\)', self.oku("app", "build.gradle.kts")))
        # brotli isteğe bağlı (yalnızca Ruffle'ı önceden sıkıştırır); Android'de gzip yeter
        self.assertEqual(kurulan, gerekli - {"brotli"})

    def test_tam_ekran(self):
        java = self.oku("app", "src", "main", "java", "io", "github", "lahmacunveayran", "socialempirestr",
                        "MainActivity.java")
        # Sayfa uygulamada olduğunu kullanıcı ajanındaki işaretten anlar ve oyun modunu açar
        isaret = re.search(r'AJAN_ISARETI = " ([\w-]+)"', java).group(1)
        with open(os.path.join(KOK, "templates", "js", "oyun.js"), encoding="utf-8") as f:
            self.assertIn(f"/{isaret}/.test(navigator.userAgent)", f.read())
        # Android 11+ çubukları güncel yöntemle gizler; oyunun (Ruffle'ın) tam ekran isteği karşılanır
        for parca in ("WindowInsetsController", "systemBars()", "onShowCustomView", "onHideCustomView",
                      "setTextZoom(100)", "LAYOUT_IN_DISPLAY_CUTOUT_MODE"):
            self.assertIn(parca, java)
        self.assertIn('android:screenOrientation="sensorLandscape"', self.oku("app", "src", "main", "AndroidManifest.xml"))


if __name__ == "__main__":
    unittest.main()
