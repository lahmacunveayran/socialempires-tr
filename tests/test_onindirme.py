"""Çevrimdışı paket: dosya listesi, indirme ve uçlar (DAG-09)."""

import os
import tempfile
import time
import unittest
from unittest import mock

from ortak import KOK  # noqa: F401

from oyun import onindirme, varliklar
from oyun import sunucu as server


class Liste(unittest.TestCase):
    def test_liste_bicimi_ve_secimi(self):
        satirlar = onindirme.liste()
        yollar = [y for y, _, _ in satirlar]
        self.assertEqual(len(yollar), len(set(yollar)))
        self.assertEqual(sorted(y for y in yollar if y.startswith("flash/")),
                         ["flash/SELoader.swf", "flash/SocialEmpires0926bsec.swf"])
        self.assertTrue(all(b > 0 for _, b, _ in satirlar))
        self.assertFalse(set(yollar) & set(varliklar.ESDEGERLER))  # sunucu bu adlarla hiç sunmaz
        oncelikler = [o for _, _, o in satirlar]
        self.assertEqual(oncelikler, sorted(oncelikler))  # indirme sırası: önemliler önce
        temel = sum(b for _, b, o in satirlar if o <= onindirme.PAKETLER["temel"])
        self.assertLess(temel, 250e6)
        # Haritada rastgele beliren kayıp eşyalar temel pakette (internetsiz denemede eksik çıkmıştı)
        self.assertIn(("buildingsprites/jinetePerdido.swf", 1), {(y, o) for y, _, o in satirlar})


class Indirme(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        hedef = self.gecici.name

        def sahte_indir(yol):
            if yol == "bozuk.png":
                return None
            tam = os.path.join(hedef, yol)
            os.makedirs(os.path.dirname(tam), exist_ok=True)
            with open(tam, "wb") as f:
                f.write(b"x" * 100)
            return tam

        self.yamalar = [
            mock.patch.object(onindirme, "_liste_onbellegi",
                              [("a/bir.png", 100, 0), ("bozuk.png", 100, 1), ("b/iki.swf", 100, 2)]),
            mock.patch.object(varliklar, "INDIRILEN_VARLIKLAR", hedef),
            mock.patch.object(varliklar, "varlik_yolu", sahte_indir),
            mock.patch.object(onindirme, "ASSETS_DIR", os.path.join(hedef, "yok")),
        ]
        for y in self.yamalar:
            y.start()
        self.istemci = server.app.test_client()

    def tearDown(self):
        for y in self.yamalar:
            y.stop()
        self.gecici.cleanup()

    def bekle(self):
        for _ in range(200):
            if not onindirme._durum["calisiyor"]:
                return
            time.sleep(0.01)
        self.fail("indirme bitmedi")

    def test_temel_paket_iner_basarisiz_sayilir(self):
        yanit = self.istemci.post("/cevrimdisi/baslat", data={"paket": "temel"})
        self.assertEqual(yanit.status_code, 202)
        self.bekle()
        ozet = self.istemci.get("/cevrimdisi/durum").get_json()
        self.assertEqual(ozet["paketler"]["temel"]["dosya"], 2)
        self.assertEqual(ozet["paketler"]["temel"]["inen_dosya"], 1)
        self.assertEqual(ozet["paketler"]["tam"]["inen_dosya"], 1)  # tam paketin dosyası inmedi
        self.assertEqual(ozet["basarisiz"], 1)

    def test_yer_yoksa_baslamaz(self):
        with mock.patch.object(onindirme, "_bos_alan", lambda: 0):
            yanit = self.istemci.post("/cevrimdisi/baslat", data={"paket": "tam"})
        self.assertEqual(yanit.status_code, 409)
        self.assertEqual(yanit.get_json()["hata"], "yer")

    def test_bilinmeyen_paket(self):
        self.assertEqual(self.istemci.post("/cevrimdisi/baslat", data={"paket": "x"}).status_code, 400)

    def test_yalnizca_bu_cihazdan(self):
        uzak = {"REMOTE_ADDR": "192.168.1.20"}
        self.assertEqual(self.istemci.post("/cevrimdisi/baslat", data={"paket": "temel"},
                                           environ_base=uzak).status_code, 403)
        self.assertEqual(self.istemci.post("/cevrimdisi/durdur", environ_base=uzak).status_code, 403)
        self.assertEqual(self.istemci.get("/cevrimdisi", environ_base=uzak).status_code, 200)


if __name__ == "__main__":
    unittest.main()
