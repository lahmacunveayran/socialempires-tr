"""Faz 0: önbellek başlıkları, ETag/304, sıkıştırma ve sabitlenmiş Ruffle."""

import base64
import gzip
import hashlib
import io
import os
import shutil
import tarfile
import tempfile
import unittest

from ortak import KOK  # noqa: F401

from oyun import aktarim
from oyun import ruffle as Ruffle
from oyun import sunucu as server

BASE = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"
CONFIG = f"{BASE}/get_game_config.php?USERID=x&user_key=1&language=tr&client_id=c"


def sahte_paket():
    """npm paketine benzeyen küçük bir .tgz ve SHA-512 özeti."""
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode="w:gz") as tar:
        for ad, icerik in (("package/ruffle.js", b"// ruffle " * 200),
                           ("package/abc.wasm", b"\0asm" + b"\1" * 4000),
                           ("package/ruffle.js.map", b"{}"),
                           ("package/alt/kacis.js", b"x")):
            bilgi = tarfile.TarInfo(ad)
            bilgi.size = len(icerik)
            tar.addfile(bilgi, io.BytesIO(icerik))
    veri = tampon.getvalue()
    return veri, base64.b64encode(hashlib.sha512(veri).digest()).decode()


class OnbellekTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.istemci = server.app.test_client()

    def test_politikalar(self):
        p = aktarim.onbellek_politikasi
        self.assertEqual(p("/ruffle/0.7.1/ruffle.js"), aktarim.DEGISMEZ)
        self.assertEqual(p(aktarim.STATIK + "swf/music/a.mp3"), aktarim.DEGISMEZ)
        self.assertEqual(p(aktarim.STATIK + "flash/SocialEmpires0926bsec.swf"), aktarim.SORARAK)
        self.assertEqual(p("/img/logo.png"), aktarim.GUNLUK)
        self.assertEqual(p("/"), aktarim.SORARAK)
        self.assertEqual(p(CONFIG), aktarim.SORARAK)

    def test_config_sikistirilir_ve_304_doner(self):
        duz = self.istemci.get(CONFIG)
        self.assertEqual(duz.headers.get("Content-Encoding"), None)
        self.assertEqual(duz.headers["Cache-Control"], "no-cache")

        cevap = self.istemci.get(CONFIG, headers={"Accept-Encoding": "gzip, deflate, br"})
        self.assertEqual(cevap.headers["Content-Encoding"], "gzip")
        self.assertIn("Accept-Encoding", cevap.headers["Vary"])
        self.assertEqual(gzip.decompress(cevap.data), duz.data)
        self.assertLess(len(cevap.data) * 5, len(duz.data))

        etag = cevap.headers["ETag"]
        self.assertNotEqual(etag, duz.headers["ETag"])
        tekrar = self.istemci.get(CONFIG, headers={"Accept-Encoding": "gzip", "If-None-Match": etag})
        self.assertEqual(tekrar.status_code, 304)
        self.assertEqual(tekrar.data, b"")

    def test_eksik_varlik_kalici_onbellege_girmez(self):
        cevap = self.istemci.get(aktarim.STATIK + "yok/..%2F..%2Fkacis.png")
        self.assertNotEqual(cevap.status_code, 200)
        self.assertEqual(cevap.headers["Cache-Control"], "no-cache")

    def test_kucuk_yanit_sikistirilmaz(self):
        cevap = self.istemci.get("/saglik/hazir", headers={"Accept-Encoding": "gzip"})
        self.assertIsNone(cevap.headers.get("Content-Encoding"))


class RuffleTestleri(unittest.TestCase):
    def setUp(self):
        self.eski = Ruffle.KLASOR
        self.gecici = tempfile.mkdtemp(prefix="se-ruffle-")
        Ruffle.KLASOR = os.path.join(self.gecici, "ruffle", Ruffle.SURUM)
        self.istemci = server.app.test_client()

    def tearDown(self):
        Ruffle.KLASOR = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def test_ozet_tutmazsa_kullanilmaz(self):
        veri, _ = sahte_paket()
        self.assertFalse(Ruffle.hazirla(veri))
        self.assertFalse(Ruffle.hazir_mi())

    def test_paket_acilir_ve_sikistirilmis_sunulur(self):
        veri, ozet = sahte_paket()
        self.assertTrue(Ruffle.hazirla(veri, ozet))
        Ruffle.brotli_baslat(bekle=True)
        dosyalar = set(os.listdir(Ruffle.KLASOR))
        self.assertIn("ruffle.js.gz", dosyalar)
        self.assertNotIn("ruffle.js.map", dosyalar)
        self.assertNotIn("kacis.js", dosyalar)

        yol = f"/ruffle/{Ruffle.SURUM}/abc.wasm"
        cevap = self.istemci.get(yol, headers={"Accept-Encoding": "gzip"})
        self.assertEqual(cevap.status_code, 200)
        self.assertEqual(cevap.mimetype, "application/wasm")
        self.assertEqual(cevap.headers["Content-Encoding"], "gzip")
        self.assertEqual(cevap.headers["Cache-Control"], aktarim.DEGISMEZ)
        self.assertTrue(gzip.decompress(cevap.data).startswith(b"\0asm"))
        cevap.close()

        duz = self.istemci.get(yol)
        self.assertIsNone(duz.headers.get("Content-Encoding"))
        duz.close()

        self.assertEqual(self.istemci.get(f"/ruffle/{Ruffle.SURUM}/ruffle.js.gz").status_code, 404)
        self.assertEqual(self.istemci.get("/ruffle/0.0.1/ruffle.js").status_code, 404)

    def test_oyun_sayfasi_sabit_surumu_kullanir(self):
        uid = server.new_village()
        self.istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires0926bsec.swf"})
        sayfa = self.istemci.get("/ruffle.html").get_data(as_text=True)
        self.assertIn(f"/ruffle/{Ruffle.SURUM}/ruffle.js", sayfa)
        self.assertNotIn("unpkg.com", sayfa)
        deneme = self.istemci.get("/ruffle-deneme.html").get_data(as_text=True)
        self.assertIn(Ruffle.DENEME_URL, deneme)


if __name__ == "__main__":
    unittest.main()
