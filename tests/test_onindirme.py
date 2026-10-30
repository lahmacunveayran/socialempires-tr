"""Çevrimdışı paket: dosya listesi, indirme ve uçlar (DAG-09)."""

import os
import tempfile
import time
import unittest
from unittest import mock

from ortak import KOK

from oyun import onindirme, varliklar
from oyun import sunucu as server


class Liste(unittest.TestCase):
    def test_liste_bicimi_ve_secimi(self):
        satirlar = onindirme.liste()
        yollar = [y for y, _, _ in satirlar]
        self.assertEqual(len(yollar), len(set(yollar)))
        self.assertEqual(sorted(y for y in yollar if y.startswith("flash/")),
                         ["flash/SELoader.swf", "flash/SocialEmpires1.4.07sec_fixed.swf"])
        self.assertTrue(all(b > 0 for _, b, _ in satirlar))
        self.assertFalse(set(yollar) & set(varliklar.ESDEGERLER))  # sunucu bu adlarla hiç sunmaz
        oncelikler = [o for _, _, o in satirlar]
        self.assertEqual(oncelikler, sorted(oncelikler))  # indirme sırası: önemliler önce
        temel = sum(b for _, b, o in satirlar if o <= onindirme.PAKETLER["temel"])
        self.assertLess(temel, 250e6)
        # Haritada rastgele beliren kayıp eşyalar temel pakette (internetsiz denemede eksik çıkmıştı)
        self.assertIn(("buildingsprites/jinetePerdido.swf", 1), {(y, o) for y, _, o in satirlar})


class Kaynak(unittest.TestCase):
    """Varlıklar dal adından değil sabit commit'ten iner (KYN-03)."""

    def test_kaynak_sabit_committe(self):
        from oyun import kaynaklar
        self.assertRegex(kaynaklar.COMMIT, r"^[0-9a-f]{40}$")
        self.assertEqual(varliklar.VARLIK_KAYNAKLARI[0], kaynaklar.HAM_VARLIK)
        self.assertIn(f"/{kaynaklar.COMMIT}/assets/", kaynaklar.HAM_VARLIK)

    def test_hicbir_dosya_dal_adiyla_indirmiyor(self):
        dosyalar = ["oyun/varliklar.py", "varliklari_indir.py", "araclar/onindirme_listesi.py",
                    "araclar/turkce_font_uret.py"]
        for yol in dosyalar:
            with open(os.path.join(KOK, yol), encoding="utf-8") as f:
                metin = f.read()
            self.assertNotIn("socialemperors/main", metin, yol)
            self.assertNotRegex(metin, r'DAL\s*=\s*"main"', yol)


class IstemciOzeti(unittest.TestCase):
    """1.4.07 istemcisi özetiyle denetlenir; özet uymayan dosya sunulmaz (GEC-02)."""

    def setUp(self):
        self.klasor = tempfile.mkdtemp()
        self.yol = os.path.join(self.klasor, "istemci.swf")
        varliklar._dogrulanan.clear()
        self.addCleanup(varliklar._dogrulanan.clear)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.klasor, ignore_errors=True)

    def yaz(self, veri):
        with open(self.yol, "wb") as f:
            f.write(veri)

    def test_ozet_uymayan_dosya_reddedilir(self):
        import hashlib
        from oyun import kaynaklar
        self.yaz(b"sahte istemci")
        self.assertFalse(varliklar.ozet_uyuyor(kaynaklar.ISTEMCI_YOLU, self.yol))
        with mock.patch.dict(varliklar.OZETLER,
                             {kaynaklar.ISTEMCI_YOLU: hashlib.sha256(b"sahte istemci").hexdigest()}):
            self.assertTrue(varliklar.ozet_uyuyor(kaynaklar.ISTEMCI_YOLU, self.yol))
            self.yaz(b"degisti!")  # aynı ad, başka içerik: önbellek boyut ve zamanla yenilenir
            os.utime(self.yol, ns=(time.time_ns() + 10**9,) * 2)
            self.assertFalse(varliklar.ozet_uyuyor(kaynaklar.ISTEMCI_YOLU, self.yol))

    def test_ozeti_olmayan_dosya_denetlenmez(self):
        self.yaz(b"x")
        self.assertTrue(varliklar.ozet_uyuyor("images_new/x.png", self.yol))

    def test_oyun_swf_adi(self):
        self.assertTrue(varliklar._oyun_swf_mi("SocialEmpires1.4.07sec_fixed.swf"))
        self.assertTrue(varliklar._oyun_swf_mi("SocialEmpires0926bsec.swf"))
        for ad in ("SocialEmpires.swf", "SocialEmpires../x.swf", "SocialEmpires1-4.swf", "Baska1.swf"):
            self.assertFalse(varliklar._oyun_swf_mi(ad), ad)


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
