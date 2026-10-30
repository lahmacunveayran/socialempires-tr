"""Wi-Fi ile taşıma: gönderen sunucunun uçları, adres ve kod denetimi, alma (DAG-10)."""

import json
import unittest
import urllib.parse
from unittest import mock

from ortak import KOK  # noqa: F401

from oyun import kayit, tasima
from oyun import sunucu as server

KOD = "123456"


class Tasima(unittest.TestCase):
    def setUp(self):
        self.uid = kayit.new_village()
        self.gonderen = tasima.gonderici.test_client()
        self.istemci = server.app.test_client()
        tasima._gonderim.update(kod=KOD, bitis=tasima.time.time() + 60, yanlis=0, gonderilen=0)

        def getir(adres, yol, kod):
            tasima._ev_agi_adresi(adres)
            yanit = self.gonderen.get(f"{yol}?kod={urllib.parse.quote(kod or '')}")
            if yanit.status_code != 200:
                raise tasima.TasimaHatasi("kod" if yanit.status_code == 403 else "yok")
            return yanit.data

        self.yama = mock.patch.object(tasima, "_getir", getir)
        self.yama.start()

    def tearDown(self):
        self.yama.stop()
        tasima._gonderim.update(kod=None, bitis=0, yanlis=0)

    def test_kod_olmadan_hicbir_sey_verilmez(self):
        self.assertEqual(self.gonderen.get("/liste?kod=000000").status_code, 403)
        self.assertEqual(self.gonderen.get(f"/kayit/{self.uid}").status_code, 403)
        tasima._gonderim.update(bitis=0)  # süre doldu
        self.assertEqual(self.gonderen.get(f"/liste?kod={KOD}").status_code, 403)

    def test_liste_botlari_vermez(self):
        botlar = [u for u in kayit.all_saves_userid() if kayit.session(u)["playerInfo"].get("bot")]
        liste = self.gonderen.get(f"/liste?kod={KOD}").get_json()["imparatorluklar"]
        uidler = {k["userid"] for k in liste}
        self.assertIn(self.uid, uidler)
        self.assertFalse(uidler & set(botlar))
        if botlar:
            self.assertEqual(self.gonderen.get(f"/kayit/{botlar[0]}?kod={KOD}").status_code, 404)

    def test_cok_yanlis_kod_gonderimi_kapatir(self):
        with mock.patch.object(tasima, "gonderimi_durdur") as durdur, mock.patch.object(tasima, "EN_COK_YANLIS", 3):
            for _ in range(3):
                self.gonderen.get("/liste?kod=999999")
            for _ in range(50):  # kapatma ayrı iş parçacığında
                if durdur.called:
                    break
                tasima.time.sleep(0.01)
        self.assertTrue(durdur.called)

    def test_yalnizca_ev_agi_adresi(self):
        for iyi in ("192.168.1.20", "10.0.0.7", "172.20.1.2"):
            self.assertEqual(tasima._ev_agi_adresi(iyi), iyi)
        for kotu in ("127.0.0.1", "8.8.8.8", "169.254.1.1", "ornek.com", "", None, "192.168.1.20:80/x"):
            with self.assertRaises(tasima.TasimaHatasi):
                tasima._ev_agi_adresi(kotu)

    def test_alinan_kayit_ayni_ve_oturum_acilir(self):
        once = kayit.session(self.uid)["playerInfo"]["pid"]
        yanit = self.istemci.post("/tasima/al", data={"adres": "192.168.1.20", "kod": KOD, "uid": self.uid})
        self.assertEqual(yanit.status_code, 200, yanit.get_json())
        self.assertEqual(yanit.get_json()["imparatorluk"]["userid"], self.uid)
        self.assertEqual(kayit.session(self.uid)["playerInfo"]["pid"], once)
        with self.istemci.session_transaction() as oturum:
            self.assertEqual(oturum["USERID"], self.uid)

    def test_liste_bu_cihazdakini_isaretler(self):
        yanit = self.istemci.post("/tasima/liste", data={"adres": "192.168.1.20", "kod": KOD})
        liste = {k["userid"]: k for k in yanit.get_json()["imparatorluklar"]}
        self.assertEqual(liste[self.uid]["burada"]["userid"], self.uid)

    def test_yanlis_kod_ve_adres_iletisi(self):
        yanit = self.istemci.post("/tasima/liste", data={"adres": "192.168.1.20", "kod": "000000"})
        self.assertEqual(yanit.status_code, 400)
        self.assertEqual(yanit.get_json()["hata"], tasima.HATALAR["kod"])
        yanit = self.istemci.post("/tasima/liste", data={"adres": "8.8.8.8", "kod": KOD})
        self.assertEqual(yanit.get_json()["hata"], tasima.HATALAR["adres"])

    def test_yalnizca_bu_cihazdan(self):
        uzak = {"REMOTE_ADDR": "192.168.1.30"}
        for yol in ("/tasima/gonder", "/tasima/gonder/durdur", "/tasima/liste", "/tasima/al"):
            self.assertEqual(self.istemci.post(yol, environ_base=uzak).status_code, 403, yol)

    def test_zarf_yedekle_ayni_bicimde(self):
        zarf = json.loads(self.gonderen.get(f"/kayit/{self.uid}?kod={KOD}").data)
        self.assertEqual(zarf["kimlik"], self.uid)
        self.assertEqual(zarf["bicim"], "SocialEmpiresTR-yedek")



class TasimaKaynaklari(unittest.TestCase):
    """DNT: gönderen sunucu açılıp kapanınca iş parçacığı bırakmaz; alan taraf yönlendirme izlemez."""

    def test_acip_kapatmak_is_parcacigi_birakmaz(self):
        import socket
        import threading
        def bos_port():  # 5051 başka bir sunucuda açık olabilir; her tur ayrı port (yalnızca sızıntı ölçülür)
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        once = threading.active_count()
        for _ in range(3):
            with mock.patch.object(tasima, "PORT", bos_port()):
                tasima.gonderimi_baslat()
                tasima.gonderimi_durdur()
        # dinleme döngüsü bir sonraki yoklamada biter; önce her açıp kapatma 2 iş parçacığı bırakıyordu
        for _ in range(50):
            if threading.active_count() <= once:
                break
            tasima.time.sleep(0.1)
        self.assertLessEqual(threading.active_count(), once)

    def test_yonlendirme_izlenmez(self):
        import http.server
        import threading

        class Yonlendir(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "http://8.8.8.8/")
                self.end_headers()

            def log_message(self, *a):
                pass

        sunucu = http.server.HTTPServer(("127.0.0.1", 0), Yonlendir)
        threading.Thread(target=sunucu.handle_request, daemon=True).start()
        with self.assertRaises(tasima.urllib.error.HTTPError) as h:
            tasima._ACICI.open(f"http://127.0.0.1:{sunucu.server_port}/liste", timeout=5)
        self.assertEqual(h.exception.code, 302)
        sunucu.server_close()


if __name__ == "__main__":
    unittest.main()
