# -*- coding: utf-8 -*-
"""Uçtan uca HTTP duman testleri (Flask test istemcisi, canlı port gerekmez)."""

import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
os.chdir(KOK)

# Testler geçici bir kayıt klasörü kullanır: yerel kayıtlara bağımlı olmaz,
# onları değiştirmez. Botlar sunucu açılışında bu klasöre üretilir.
import bundle  # noqa: E402
GECICI_KAYIT = tempfile.mkdtemp(prefix="se-test-")
bundle.SAVES_DIR = GECICI_KAYIT

import server  # noqa: E402

UID = None
BASE = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


class HttpDumanTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global UID
        UID = server.new_village()
        cls.istemci = server.app.test_client()
        cls.istemci.post("/", data={"USERID": UID, "GAMEVERSION": "SocialEmpires0926bsec.swf"})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(GECICI_KAYIT, ignore_errors=True)

    def test_giris_sayfasi(self):
        istemci = server.app.test_client()
        cevap = istemci.get("/")
        self.assertEqual(cevap.status_code, 200)

    def test_saglik(self):
        cevap = self.istemci.get("/saglik")
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        self.assertEqual(veri["durum"], "ok")
        self.assertGreater(veri["oyuncu"], 0)

    def test_giris_listesinde_bot_yok(self):
        istemci = server.app.test_client()
        sayfa = istemci.get("/").get_data(as_text=True)
        self.assertIn(UID, sayfa)
        self.assertNotIn("Kara Han", sayfa)

    def test_bilinmeyen_komsu_500_vermez(self):
        cevap = self.istemci.post(
            f"{BASE}/get_player_info.php",
            data={"USERID": UID, "user_key": "1", "client_id": "c", "user": "yok-boyle-biri"},
        )
        self.assertEqual(cevap.status_code, 200)
        self.assertEqual(cevap.get_json()["result"], "error")

    def test_bosluklu_varlik_yolu_kabul_edilir(self):
        os.makedirs(os.path.join(KOK, "assets", "swf", "music"), exist_ok=True)
        yol = os.path.join(KOK, "assets", "swf", "music", "_test bosluk.mp3")
        with open(yol, "wb") as f:
            f.write(b"ID3" + b"\0" * 100)
        try:
            cevap = self.istemci.get("/default01.static.socialpointgames.com/static/socialempires/swf/music/_test%20bosluk.mp3")
            self.assertEqual(cevap.status_code, 200)
            cevap.close()
        finally:
            os.remove(yol)

    def test_gecersiz_kimlik_reddedilir(self):
        istemci = server.app.test_client()
        cevap = istemci.post("/", data={"USERID": "../../kacis", "GAMEVERSION": "x"})
        self.assertEqual(cevap.status_code, 400)

    def test_oyun_sayfasi(self):
        cevap = self.istemci.get("/play.html")
        self.assertEqual(cevap.status_code, 200)

    def test_config_turkce(self):
        cevap = self.istemci.get(f"{BASE}/get_game_config.php?USERID=x&user_key=1&language=tr&client_id=c")
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        adlar = [e["name"] for e in veri["items"]]
        self.assertEqual(adlar[0], "Ev I")
        self.assertIn("Köylüyü eğit", [m["title"] for m in veri["missions"]])

    def test_turkce_font_yayini(self):
        cevap = self.istemci.get("/default01.static.socialpointgames.com/static/socialempires/fonts/tr_ErasBold.swf")
        self.assertEqual(cevap.status_code, 200)
        self.assertIn(cevap.data[:3], (b"CWS", b"FWS", b"ZWS"))

    def test_turkce_font_dosyalari(self):
        for ad in ("tr_ArialRoundedBold.swf", "tr_ErasBold.swf"):
            yol = os.path.join(KOK, "assets", "fonts", ad)
            self.assertTrue(os.path.exists(yol), ad)
            with open(yol, "rb") as f:
                self.assertIn(f.read(3), (b"CWS", b"FWS", b"ZWS"))

    def test_ada_yedi_bolge(self):
        cevap = self.istemci.get(f"{BASE}/get_continent.php?USERID={UID}&map=99&worldChange=0&user_key=1")
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        self.assertEqual(len(veri["continent"]), 7)
        self.assertIn("arCurrentConquered", veri)

    def test_turnuva_odasi(self):
        cevap = self.istemci.post(
            f"{BASE}/tournaments/get_tournament_info.php",
            data={"USERID": UID, "user_key": "1", "data": "x;" + '{"user_id":"' + UID + '"}'},
        )
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        self.assertEqual(veri["result"], "ok")
        self.assertEqual(len(veri["tournament"]["players"]), 4)


    def test_gunluk_durum(self):
        cevap = self.istemci.get(f"{BASE}/get_daily.php?USERID={UID}&user_key=1")
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        self.assertEqual(veri["result"], "ok")
        self.assertEqual(len(veri["daily"]["gorevler"]), 3)
        self.assertIn("haftalik", veri["daily"])

    def test_sosyal_durum(self):
        cevap = self.istemci.get(f"{BASE}/get_social.php?USERID={UID}&user_key=1")
        self.assertEqual(cevap.status_code, 200)
        self.assertEqual(cevap.get_json()["result"], "ok")


if __name__ == "__main__":
    unittest.main()
