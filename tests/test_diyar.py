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
        cls.istemci.post("/", data={"USERID": cls.uid, "GAMEVERSION": "SocialEmpires0926bsec.swf"})

    def test_oyun_sayfasi_ruffle_ve_giris_dugmesi(self):
        adres = "http://192.168.1.20:5050"
        istemci = server.app.test_client()
        istemci.post("/", base_url=adres, data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires0926bsec.swf"})
        sayfa = istemci.get("/play.html", base_url=adres).get_data(as_text=True)
        self.assertIn('id="kralliga-gir"', sayfa)
        self.assertIn("/js/gokyuzu.js", sayfa)
        # Telefon ev ağından açınca varlıklar da aynı adresten insin.
        self.assertIn("http://192.168.1.20:5050/default01.static.socialpointgames.com", sayfa)
        self.assertNotIn("unpkg.com", sayfa)

    def test_flash_sayfasi_ayri(self):
        sayfa = self.istemci.get("/flash.html").get_data(as_text=True)
        self.assertIn("application/x-shockwave-flash", sayfa)

    def test_statik_dosyalar(self):
        for yol in ("/js/oyun.js", "/js/gokyuzu.js", "/css/oyun.css", "/hazine"):
            cevap = self.istemci.get(yol)
            self.assertEqual(cevap.status_code, 200, yol)
            cevap.close()

    def test_rutbe_adlari(self):
        self.assertTrue(Dunya.rutbe(8))
        self.assertNotEqual(Dunya.rutbe(8), Dunya.rutbe(9))
        self.assertTrue(Dunya.turkce_ad(512))


class KursuTestleri(unittest.TestCase):
    def test_siralama_ve_onbellek(self):
        istemci = server.app.test_client()
        uid = server.new_village()
        istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires0926bsec.swf"})
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
