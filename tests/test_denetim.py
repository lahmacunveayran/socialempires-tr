"""Bağımsız denetimin bulguları (DNT-*): bozuk kayıt, siteler arası istek, DNS yeniden bağlama."""

import copy
import json
import os
import unittest

from ortak import KOK, bos_kayit  # noqa: F401

from oyun import kayit, kayit_yedek
from oyun import sunucu as server
from oyun.yollar import SAVES_DIR


def _yaz(uid, veri, uzanti=".save.json"):
    with open(os.path.join(SAVES_DIR, uid + uzanti), "w", encoding="utf-8") as f:
        json.dump(veri, f)


def _sil(uid):
    for uzanti in (".save.json", ".save.json.bak", ".save.json.bozuk"):
        try:
            os.remove(os.path.join(SAVES_DIR, uid + uzanti))
        except OSError:
            pass


class BozukKayit(unittest.TestCase):
    def tearDown(self):
        for uid in ("surumsuz", "bakli", "bosharita"):
            _sil(uid)
        kayit.load_saved_villages()

    def test_tek_bozuk_kayit_sunucuyu_durdurmaz_kenara_alinir(self):
        bozuk = bos_kayit("surumsuz")
        del bozuk["version"]
        bozuk["maps"] = []
        _yaz("surumsuz", bozuk)
        kayit.load_saved_villages()  # önce KeyError/IndexError ile bütün yükleme düşüyordu
        self.assertNotIn("surumsuz", kayit.all_saves_userid())
        self.assertTrue(os.path.exists(os.path.join(SAVES_DIR, "surumsuz.save.json.bozuk")))
        self.assertTrue(kayit.all_saves_userid())  # diğer kayıtlar yüklendi

    def test_surumsuz_kayit_goc_edilir(self):
        eski = bos_kayit("surumsuz")
        del eski["version"]
        _yaz("surumsuz", eski)
        kayit.load_saved_villages()
        self.assertIn("surumsuz", kayit.all_saves_userid())

    def test_bozuk_kaydin_bak_dosyasi_geri_alinir(self):
        _yaz("bakli", {"playerInfo": {}}, ".save.json")
        _yaz("bakli", bos_kayit("bakli"), ".save.json.bak")
        kayit.load_saved_villages()
        self.assertIn("bakli", kayit.all_saves_userid())
        with open(os.path.join(SAVES_DIR, "bakli.save.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["playerInfo"]["pid"], "bakli")  # yeniden yazıldı

    def test_kayit_yazimi_canli_dosyayi_hic_kaldirmaz(self):
        uid = kayit.new_village()
        kayit.save_session(uid)
        yol = os.path.join(SAVES_DIR, uid + ".save.json")
        self.assertTrue(os.path.exists(yol) and os.path.exists(yol + ".bak"))
        with open(yol, encoding="utf-8") as f:
            self.assertNotIn("\n    ", f.read())  # girintisiz yazılır

    def test_yedekten_acilamayacak_kayit_alinmaz(self):
        kotu = bos_kayit("bosharita")
        kotu["maps"] = []
        ham = json.dumps(kotu).encode("utf-8")
        zarf = {"bicim": kayit_yedek.BICIM, "surum": 1, "kimlik": "bosharita", "ad": "x",
                "sha256": __import__("hashlib").sha256(ham).hexdigest(), "kayit": ham.decode()}
        with self.assertRaises(kayit_yedek.YedekHatasi) as h:
            kayit_yedek.zarfi_ac(json.dumps(zarf), "bosharita")
        self.assertEqual(h.exception.args[0], "sema")


class KokenDenetimi(unittest.TestCase):
    def setUp(self):
        self.uid = kayit.new_village()
        self.istemci = server.app.test_client()

    def test_baska_siteden_durum_degistiren_istek_reddedilir(self):
        for basliklar in ({"Origin": "https://kotu.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Origin": "null"}):
            self.assertEqual(self.istemci.post("/", data={"USERID": self.uid}, headers=basliklar).status_code, 403)
            self.assertEqual(self.istemci.get("/new.html", headers=basliklar).status_code, 403)
        # aynı kökenden (oyunun kendi sayfası) ve başlıksız (yerel araçlar) geçer
        self.assertEqual(self.istemci.post("/", data={"USERID": self.uid},
                                           headers={"Origin": "http://localhost"}).status_code, 302)
        self.assertEqual(self.istemci.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code, 200)

    def test_dns_yeniden_baglama_reddedilir(self):
        self.assertEqual(self.istemci.get("/", base_url="http://kotu.example:5050").status_code, 403)
        self.assertEqual(self.istemci.get("/kayit/indir", base_url="http://kotu.example:5050").status_code, 403)
        self.assertEqual(self.istemci.get("/", base_url="http://127.0.0.1:5050").status_code, 200)
        # ev ağındaki cihaz kendi gördüğü adresle gelir
        self.assertEqual(self.istemci.get("/", base_url="http://192.168.1.20:5050",
                                          environ_base={"REMOTE_ADDR": "192.168.1.30"}).status_code, 200)

    def test_cok_buyuk_govde_reddedilir(self):
        self.assertEqual(server.app.config["MAX_CONTENT_LENGTH"], 40 * 1024 * 1024)

    def test_oturum_anahtari_rastgele(self):
        self.assertNotEqual(server.app.secret_key, "SECRET_KEY")
        self.assertGreaterEqual(len(server.app.secret_key), 32)



class VarlikIndirme(unittest.TestCase):
    def test_basarisiz_indirme_on_dakika_yeniden_denenmez(self):
        from unittest import mock
        from oyun import varliklar
        cagri = []
        with mock.patch.object(varliklar, "_indir_dene", lambda p, h: cagri.append(p) or False):
            varliklar._basarisiz.pop("x/yok.png", None)
            self.assertFalse(varliklar._indir("x/yok.png", "/tmp/yok.png"))
            self.assertFalse(varliklar._indir("x/yok.png", "/tmp/yok.png"))
        self.assertEqual(cagri, ["x/yok.png"])  # ikinci istek beklemeden döner
        varliklar._basarisiz.pop("x/yok.png", None)


if __name__ == "__main__":
    unittest.main()
