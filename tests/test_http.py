# -*- coding: utf-8 -*-
"""Uçtan uca HTTP duman testleri (Flask test istemcisi, canlı port gerekmez)."""

import os
import sys
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

import server  # noqa: E402

UID = "740548c4-fe42-4286-b14c-55d97d943231"
BASE = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


class HttpDumanTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._eski_kaydet = server.save_session
        server.save_session = lambda uid: None  # testler canlı kayıtları yazmasın
        cls.istemci = server.app.test_client()
        cls.istemci.post("/", data={"USERID": UID, "GAMEVERSION": "SocialEmpires0926bsec.swf"})

    @classmethod
    def tearDownClass(cls):
        server.save_session = cls._eski_kaydet

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

    def test_gecersiz_kimlik_reddedilir(self):
        istemci = server.app.test_client()
        cevap = istemci.post("/", data={"USERID": "../../kacis", "GAMEVERSION": "x"})
        self.assertEqual(cevap.status_code, 400)

    def test_oyun_sayfasi(self):
        cevap = self.istemci.get("/play.html")
        self.assertEqual(cevap.status_code, 200)

    def test_config_turkce_ve_ascii(self):
        cevap = self.istemci.get(f"{BASE}/get_game_config.php?USERID=x&user_key=1&language=en&client_id=c")
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        adlar = [e["name"] for e in veri["items"]]
        self.assertEqual(adlar[0], "Ev I")
        self.assertFalse(any(any(h in a for h in "şğİıçöüŞĞÇÖÜ") for a in adlar))

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

    def test_sosyal_durum(self):
        cevap = self.istemci.get(f"{BASE}/get_social.php?USERID={UID}&user_key=1")
        self.assertEqual(cevap.status_code, 200)
        self.assertEqual(cevap.get_json()["result"], "ok")


if __name__ == "__main__":
    unittest.main()
