"""Faz 1 ve 2: oyun sayfası, Diyar Haberleri ve Şeref Kürsüsü."""

import unittest

from ortak import KOK  # noqa: F401

from oyun import diyar
from oyun import dunya as Dunya
from oyun import sunucu as server


class OyunSayfasiTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uid = server.new_village()
        cls.istemci = server.app.test_client()
        cls.istemci.post("/", data={"USERID": cls.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})

    def test_oyun_sayfasi_ruffle_ve_giris_dugmesi(self):
        adres = "http://192.168.1.20:5050"
        istemci = server.app.test_client()
        lan = {"REMOTE_ADDR": "192.168.1.30"}  # ev ağındaki tablet
        istemci.post("/", base_url=adres, environ_base=lan,
                     data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        sayfa = istemci.get("/play.html", base_url=adres, environ_base=lan).get_data(as_text=True)
        self.assertIn('id="kralliga-gir"', sayfa)
        # Telefon ev ağından açınca varlıklar da aynı adresten insin.
        self.assertIn("http://192.168.1.20:5050/default01.static.socialpointgames.com", sayfa)
        self.assertNotIn("unpkg.com", sayfa)

    def test_flash_sayfasi_ayri(self):
        sayfa = self.istemci.get("/flash.html").get_data(as_text=True)
        self.assertIn("application/x-shockwave-flash", sayfa)

    def test_statik_dosyalar(self):
        for yol in ("/js/oyun.js", "/css/oyun.css", "/hazine",
                    "/fonts/baloo-2-latin-800-normal.woff2"):
            cevap = self.istemci.get(yol)
            self.assertEqual(cevap.status_code, 200, yol)
            cevap.close()

    def test_rutbe_adlari(self):
        self.assertTrue(Dunya.rutbe(8))
        self.assertNotEqual(Dunya.rutbe(8), Dunya.rutbe(9))
        self.assertTrue(Dunya.turkce_ad(512))


class GirisSayfasiTestleri(unittest.TestCase):
    def test_imparatorluk_kartlari(self):
        uid = server.new_village()
        sayfa = server.app.test_client().get("/").get_data(as_text=True)
        self.assertIn("/css/oyun.css", sayfa)
        self.assertIn(f'name="USERID" value="{uid}"', sayfa)
        self.assertIn('href="/new.html"', sayfa)
        self.assertIn('id="yedek-dosyasi"', sayfa)

    def test_karttan_giris(self):
        uid = server.new_village()
        istemci = server.app.test_client()
        cevap = istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        self.assertEqual(cevap.status_code, 302)
        self.assertEqual(istemci.get("/play.html").status_code, 200)


class KursuTestleri(unittest.TestCase):
    def test_siralama_ve_onbellek(self):
        istemci = server.app.test_client()
        uid = server.new_village()
        istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        diyar._kursu["zaman"] = 0
        veri = istemci.get("/dunya/kursu").get_json()
        self.assertLessEqual(len(veri["ilk"]), diyar.KURSU_BOYU)
        seviyeler = [(o["seviye"], o["xp"]) for o in veri["ilk"]]
        self.assertEqual(seviyeler, sorted(seviyeler, reverse=True))
        self.assertTrue(all(o["rutbe"] for o in veri["ilk"]))
        self.assertEqual(veri["ben"]["id"], uid)
        # 60 saniye içinde aynı liste (kayıtlar yeniden taranmaz)
        self.assertIs(diyar.kursu(), diyar.kursu())


class HaberTestleri(unittest.TestCase):
    def setUp(self):
        self.eski = Dunya.etkin
        self.dunya = Dunya.Dunya()
        Dunya.etkin = self.dunya

    def tearDown(self):
        Dunya.etkin = self.eski

    def test_sonra_numarasindan_sonrakiler(self):
        for i in range(5):
            self.dunya.olay("savas", f"olay {i}")
        istemci = server.app.test_client()
        veri = istemci.get("/dunya/olaylar?sonra=3").get_json()
        self.assertEqual([o["metin"] for o in veri["olaylar"]], ["olay 3", "olay 4"])
        self.assertEqual(veri["son"], 5)
        self.assertEqual(istemci.get("/dunya/olaylar?sonra=5").get_json()["olaylar"], [])
        # Sunucu yeniden başlamışsa istemcinin büyük numarası sıfırlanır.
        self.assertEqual(len(istemci.get("/dunya/olaylar?sonra=999").get_json()["olaylar"]), 5)
        self.assertEqual(istemci.get("/dunya/olaylar?sonra=abc").status_code, 200)

    def test_turda_en_fazla_bir_ekonomi_haberi(self):
        self.dunya.tek_tick()
        ekonomi = [o for o in self.dunya.olaylar if o["tur"] == "ekonomi"]
        self.assertLessEqual(len(ekonomi), 1)
        self.assertEqual(self.dunya._ekonomi_haberleri, [])


if __name__ == "__main__":
    unittest.main()


class DagitimTestleri(unittest.TestCase):
    def test_manifest(self):
        cevap = server.app.test_client().get("/manifest.webmanifest")
        veri = cevap.get_json(force=True)
        self.assertEqual(veri["display"], "standalone")
        self.assertEqual({s["sizes"] for s in veri["icons"]}, {"192x192", "512x512"})
        for simge in veri["icons"]:
            self.assertEqual(server.app.test_client().get(simge["src"]).status_code, 200)

    def test_yerel_ag_adresi(self):
        self.assertRegex(server.yerel_ag_adresi(), r"^\d+\.\d+\.\d+\.\d+$")


class HilePaneliTestleri(unittest.TestCase):
    def test_panel_oyunun_kaynak_resimleriyle(self):
        istemci = server.app.test_client()
        istemci.post("/", data={"USERID": server.new_village(), "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        sayfa = istemci.get("/cheat").get_data(as_text=True)
        self.assertIn("/css/oyun.css", sayfa)
        for resim in ("collect_g0.jpg", "collect_w0.jpg", "collect_s0.jpg", "collect_f0.jpg"):
            self.assertIn(f"images_new/{resim}", sayfa)
        cevap = istemci.post("/cheat/uygula", json={"islem": "kaynak", "tur": "wood", "miktar": 1000})
        self.assertEqual(cevap.status_code, 200)
        self.assertIn("odun", cevap.get_json()["ozet"])
