"""Uçtan uca HTTP testleri (Flask test istemcisi, canlı port gerekmez).

Sunucu geçici bir kayıt klasörüyle açılır ve oraya bot köyleri üretir.
Çalıştırma: python tests/test_http.py
"""

import os
import unittest

from ortak import KOK

from oyun import sunucu as server  # noqa: E402

UID = None
BASE = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


class HttpDumanTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global UID
        UID = server.new_village()
        cls.istemci = server.app.test_client()
        cls.istemci.post("/", data={"USERID": UID, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})

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

    def test_oyun_surumu_sabit(self):
        # Tek istemci 1.4.07; formdan gelen başka sürüm (ya da yol) oyuna geçmez
        istemci = server.app.test_client()
        istemci.post("/", data={"USERID": UID, "GAMEVERSION": "../../ayarlar.json"})
        sayfa = istemci.get("/play.html").get_data(as_text=True)
        self.assertIn("flash/SocialEmpires1.4.07sec_fixed.swf", sayfa)
        self.assertNotIn("ayarlar.json", sayfa)
        self.assertNotIn('name="GAMEVERSION"', istemci.get("/").get_data(as_text=True))

    def test_config_turkce(self):
        cevap = self.istemci.get(f"{BASE}/get_game_config.php?USERID=x&user_key=1&language=tr&client_id=c")
        self.assertEqual(cevap.status_code, 200)
        veri = cevap.get_json()
        adlar = [e["name"] for e in veri["items"]]
        self.assertEqual(adlar[0], "Ev I")
        self.assertIn("Köylü eğit", [m["title"] for m in veri["missions"]])

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

    def test_dunya_haritasi(self):
        cevap = self.istemci.get(f"{BASE}/get_continent_ranking.php?USERID={UID}&map=0&worldChange=0&user_key=1")
        veri = cevap.get_json()
        self.assertEqual(len(veri["continent"]), 8)
        self.assertEqual(veri["continent"][0]["nivel"], 1)
        self.assertIn(UID, [g["user_id"] for g in veri["continent"]])

    def _servis(self, uc, veri):
        import hashlib
        import hmac
        import json
        cevap = self.istemci.post(f"{BASE}/{uc}?USERID={UID}&user_key=1",
                                  data={"data": "imza;" + json.dumps(veri)})
        imza, govde = cevap.get_data(as_text=True).split(";", 1)
        beklenen = hmac.new(b"3m0d3pwiupoetn7ysa02", govde.encode(), hashlib.sha256).hexdigest()
        self.assertEqual(imza, beklenen)
        return json.loads(govde)

    def test_buyucu_iksirleri(self):
        from oyun.kayit import session
        kayit = session(UID)
        ps = kayit["privateState"]
        kayit["playerInfo"]["cash"] = 100
        for _ in range(3):  # başbüyücü (index 2) her zaman başarır
            ps["kompuLastTimeStamp"] = -1  # bekleme süresini atla
            self.assertEqual(self._servis("kompu_try.php", {"index": 2, "town": 0})["data"], True)
        self.assertEqual(ps["kompuSpells"], 3)
        self.assertEqual(ps["kompuSteps"], [3])
        self.assertEqual(ps["gifts"][2138], 1)
        self.assertEqual(kayit["playerInfo"]["cash"], 70)
        # bekleme süresi dolmadan deneme reddedilir
        self.assertEqual(self._servis("kompu_try.php", {"index": 2, "town": 0})["result"], "error")
        self.assertEqual(self._servis("kompu_hurry_up.php", {"town": 0})["data"], True)
        self.assertEqual(kayit["playerInfo"]["cash"], 65)
        # parası yetmeyen deneme ve hızlandırma reddedilir
        kayit["playerInfo"]["cash"] = 3
        ps["kompuLastTimeStamp"] = -1
        self.assertEqual(self._servis("kompu_try.php", {"index": 2, "town": 0})["result"], "error")
        self.assertEqual(self._servis("kompu_hurry_up.php", {"town": 0})["result"], "error")
        self.assertEqual(kayit["playerInfo"]["cash"], 3)

    def test_buyucu_tamamlaninca_bir_kez_kaydedilir(self):
        from oyun.kayit import session
        kayit = session(UID)
        ps = kayit["privateState"]
        kayit["playerInfo"]["cash"] = 1000
        ps["kompuSpells"] = 11
        ps["kompuLastTimeStamp"] = -1
        self.assertEqual(self._servis("kompu_try.php", {"index": 2, "town": 0})["data"], True)
        self.assertEqual(len(ps["kompuCompleted"]), 1)
        ps["kompuLastTimeStamp"] = -1
        self.assertEqual(self._servis("kompu_try.php", {"index": 2, "town": 0})["result"], "error")
        self.assertEqual(len(ps["kompuCompleted"]), 1)
        ps.update(kompuSpells=0, kompuSteps=[], kompuCompleted=[])

    def test_istemci_hatasi_ve_kayip_esya(self):
        self.assertEqual(self._servis("report_error.php", {"error_id": "1"})["result"], "success")
        from oyun.kayit import session
        session(UID)["maps"][0]["items"].append([92, 70, 70, 0, 0, 0])
        cevap = self.istemci.post(f"{BASE}/register_found_item.php?USERID={UID}",
                                  data={"sender_id": UID, "item_id": "1"})
        self.assertIn("id", cevap.get_json())
        self.assertNotIn(92, [e[0] for e in session(UID)["maps"][0]["items"]])

    def test_config_buyucu_teklifi_donemli(self):
        veri = self.istemci.get(f"{BASE}/get_game_config.php?USERID=x&user_key=1&language=tr").get_json()
        teklif = veri["kompu_offers"][0]
        self.assertEqual(teklif["starts_at"], teklif["id"] * 30 * 86400)
        self.assertEqual(teklif["game_type"], 0)
        self.assertIn("KOMPU_WIZZARD_COSTS", veri["globals"])

    def test_oyuncu_profili(self):
        from oyun.kayit import session
        session(UID)["privateState"]["attacksSent"] = [
            {"time": 1, "victim_id": "x", "description": {"win": 1}},
            {"time": 2, "victim_id": "y", "description": {"win": 0}},
            {"time": 3, "victim_id": "z"},  # bot akını kaydı: sonuç yok
        ]
        veri = self.istemci.get(f"{BASE}/get_public_player_info.php?USERID={UID}&user_key=1").get_json()
        self.assertEqual(veri["pid"], UID)
        self.assertIn("map_names", veri)
        self.assertEqual((veri["attacks_won"], veri["attacks_lost"]), (1, 1))

    def test_turnuva_bilgisi_data_icinde(self):
        veri = self._servis("tournaments/get_tournament_info.php", {"user_id": UID})
        self.assertIn("tournament_friends", veri["data"])
        self.assertIn("tournament_reward_id", veri["data"])


if __name__ == "__main__":
    unittest.main()
