"""Faz 3: etkinlik takvimi, haftalık turnuva (Elo), günlük hediye, kayıt yedeği."""

import io
import json
import os
import unittest
from datetime import date, datetime, timedelta

from ortak import KOK, bos_kayit  # noqa: F401

from oyun import config, elo, hediye, kayit_yedek, takvim
from oyun import sunucu as server
from oyun.yollar import SAVES_DIR


class TakvimTestleri(unittest.TestCase):
    def test_diyanet_bayram_tarihleri_2026_2030(self):
        beklenen = {
            2026: ("2026-03-20", "2026-05-27"), 2027: ("2027-03-09", "2027-05-16"),
            2028: ("2028-02-26", "2028-05-05"), 2029: ("2029-02-14", "2029-04-24"),
            2030: ("2030-02-04", "2030-04-13"),
        }
        for yil, (ramazan, kurban) in beklenen.items():
            self.assertEqual(takvim.bayram(yil, "ramazan").isoformat(), ramazan)
            self.assertEqual(takvim.bayram(yil, "kurban").isoformat(), kurban)

    def test_etkinlik_setleri(self):
        self.assertEqual(takvim.acik_setler(date(2026, 7, 10)), ["Harikalar"])
        self.assertIn("Cadılar Bayramı", takvim.acik_setler(date(2026, 10, 31)))
        self.assertIn("Mitoloji", takvim.acik_setler(date(2027, 5, 19)))   # Kurban 4. gün
        self.assertNotIn("Mitoloji", takvim.acik_setler(date(2027, 5, 20)))
        self.assertIn("Çin", takvim.acik_setler(date(2026, 12, 30)))      # yılbaşından önce
        self.assertIn("Çin", takvim.acik_setler(date(2027, 1, 3)))
        yaklasan = takvim.etkinlikler(date(2026, 7, 10))
        self.assertEqual(yaklasan[0]["ad"], "Zafer Bayramı")
        self.assertFalse(yaklasan[0]["aktif"])

    def test_takvim_kipinde_magaza(self):
        eski = config.tema_seti_kipi
        config.tema_seti_kipi = lambda: "takvim"
        eski_setler = takvim.acik_setler
        try:
            takvim.acik_setler = lambda gun=None: ["Harikalar", "Viking"]
            ids = config.takvimdeki_setler()
            vikingler = {str(i) for i in config.tema_setleri()["Viking"]}
            self.assertTrue(vikingler <= ids)
            kopya = config.get_client_game_config("tr")
            magazada = {e["id"] for e in kopya["items"] if e.get("in_store") == "1"}
            self.assertTrue(vikingler <= magazada)
        finally:
            config.tema_seti_kipi = eski
            takvim.acik_setler = eski_setler


class EloTestleri(unittest.TestCase):
    def test_yol_haritasi_ornegi(self):
        self.assertAlmostEqual(elo.beklenen(1500, 1600), 0.36, places=2)
        self.assertEqual(round(elo.guncelle(1500, 1600, 0.8, 0)), 1514)

    def test_k_katsayisi(self):
        self.assertEqual(elo.k_katsayisi(19, False), 32)
        self.assertEqual(elo.k_katsayisi(20, False), 16)
        self.assertEqual(elo.k_katsayisi(5, True), 16)

    def test_bot_reytingi_sabit_ve_sinirli(self):
        self.assertEqual(elo.bot_reytingi(0), 1000)
        self.assertLess(elo.bot_reytingi(100), elo.bot_reytingi(10000))
        self.assertLessEqual(elo.bot_reytingi(1e12), 2400)

    def test_hafta_pazartesi_baslar(self):
        self.assertEqual(elo.hafta(datetime(2026, 11, 1, 23, 59, tzinfo=takvim.TURKIYE)), "2026-10-26")
        self.assertEqual(elo.hafta(datetime(2026, 11, 2, 0, 0, tzinfo=takvim.TURKIYE)), "2026-11-02")


class HaftalikTurnuvaTestleri(unittest.TestCase):
    def setUp(self):
        self.yol = elo._dosya()
        if os.path.exists(self.yol):
            os.remove(self.yol)

    def test_odul_hafta_bitince_yalniz_ilk_10a(self):
        pazartesi = datetime(2026, 11, 2, 9, 0, tzinfo=takvim.TURKIYE)
        # 12 bot: puanları gerçek oyuncuların arasına karışsın
        botlar = {f"bot{i}": (f"Bot {i}", 900 + 100 * i) for i in range(12)}
        odenen = []
        self.assertIsNone(elo.haftayi_kapat(pazartesi, botlar, lambda *a: odenen.append(a)))
        for _ in range(4):  # 4. maç sayılmaz
            elo.mac_kaydet("guclu", "Güçlü", 100, pazartesi)
        elo.mac_kaydet("zayif", "Zayıf", 10, pazartesi)
        # Hafta içinde ödül yok
        self.assertIsNone(elo.haftayi_kapat(pazartesi + timedelta(days=6, hours=14), botlar, lambda *a: odenen.append(a)))
        self.assertEqual(odenen, [])
        # Saat ileri: pazartesi 00.00 hafta kapanır
        kapanan = elo.haftayi_kapat(pazartesi + timedelta(days=6, hours=15), botlar, lambda *a: odenen.append(a))
        sira = {o["id"]: o["sira"] for o in kapanan}
        self.assertEqual(next(o for o in kapanan if o["id"] == "guclu")["puan"], 300)
        self.assertEqual(sira["guclu"], 1)
        self.assertGreater(sira["zayif"], elo.ODULLU_SIRA)
        self.assertEqual(odenen, [("guclu", 847, 1)])  # Yanardağ Ejderhası
        # Yeni hafta temiz başlar ve ikinci kez ödenmez
        self.assertIsNone(elo.haftayi_kapat(pazartesi + timedelta(days=8), botlar, lambda *a: odenen.append(a)))
        self.assertEqual(len(odenen), 1)


class HediyeTestleri(unittest.TestCase):
    def test_seri_ve_kacirilan_gun(self):
        kayit = bos_kayit()
        gun = date(2026, 11, 2)
        self.assertEqual(hediye.al(kayit, gun)[0], 0)
        self.assertIsNone(hediye.al(kayit, gun))  # aynı gün ikinci kez yok
        self.assertEqual(hediye.al(kayit, gun + timedelta(days=1))[0], 1)
        self.assertEqual(hediye.al(kayit, gun + timedelta(days=2))[0], 2)
        # Bir gün kaçırıldı: sıfıra değil bir adım geri (3 yerine 2)
        self.assertEqual(hediye.al(kayit, gun + timedelta(days=4))[0], 2)
        esya, adet = hediye.ODULLER[0]
        self.assertGreaterEqual(kayit["privateState"]["gifts"][esya], adet)

    def test_yedinci_gunden_sonra_basa_doner(self):
        kayit = bos_kayit()
        gun = date(2026, 11, 2)
        sira = [hediye.al(kayit, gun + timedelta(days=i))[0] for i in range(8)]
        self.assertEqual(sira, [0, 1, 2, 3, 4, 5, 6, 0])


class YedekTestleri(unittest.TestCase):
    def setUp(self):
        self.uid = server.new_village()
        self.istemci = server.app.test_client()
        self.istemci.post("/", data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires0926bsec.swf"})
        self.yol = os.path.join(SAVES_DIR, f"{self.uid}.save.json")

    def _yukle(self, veri, istemci=None):
        return (istemci or self.istemci).post("/kayit/yukle", data={"dosya": (io.BytesIO(veri), "y.json")},
                                              content_type="multipart/form-data")

    def test_indir_yukle_bayt_bayt_ayni(self):
        with open(self.yol, "rb") as f:
            orijinal = f.read()
        cevap = self.istemci.get("/kayit/indir")
        self.assertIn("attachment", cevap.headers["Content-Disposition"])
        yedek = cevap.data
        # Kayıt değişsin, sonra yedekten geri dönülsün
        with open(self.yol, "w", encoding="utf-8") as f:
            f.write(orijinal.decode("utf-8").replace('"level"', '"level" ', 1))
        sonuc = self._yukle(yedek)
        self.assertEqual(sonuc.status_code, 200, sonuc.get_json())
        with open(self.yol, "rb") as f:
            self.assertEqual(f.read(), orijinal)
        self.assertTrue(os.path.exists(self.yol + ".bak"))
        # Yanıt yüklenen dosyadaki hiçbir değeri geri yansıtmaz.
        self.assertEqual(sonuc.get_json(), {"durum": "ok"})

    def test_bozuk_ozet_ve_kimlik_cakismasi(self):
        zarf = json.loads(self.istemci.get("/kayit/indir").data)
        bozuk = dict(zarf, kayit=zarf["kayit"].replace("0", "1", 1))
        self.assertIn("SHA-256", self._yukle(json.dumps(bozuk).encode()).get_json()["hata"])
        self.assertEqual(self._yukle(b"rastgele").status_code, 400)
        # Başka bir oyuncu bu kimliğin üzerine yazamaz
        baska = server.app.test_client()
        baska.post("/", data={"USERID": server.new_village(), "GAMEVERSION": "x"})
        self.assertEqual(self._yukle(json.dumps(zarf).encode(), baska).status_code, 400)

    def test_zarf_bicimi(self):
        zarf = kayit_yedek.zarf(self.uid)
        self.assertEqual(zarf["bicim"], kayit_yedek.BICIM)
        self.assertEqual(len(zarf["sha256"]), 64)


class SayfaUclariTestleri(unittest.TestCase):
    def test_hediye_hafta_takvim_uclari(self):
        istemci = server.app.test_client()
        istemci.post("/", data={"USERID": server.new_village(), "GAMEVERSION": "SocialEmpires0926bsec.swf"})
        durum = istemci.get("/hediye").get_json()
        self.assertTrue(durum["alinabilir"])
        self.assertEqual(len(durum["oduller"]), 7)
        self.assertEqual(istemci.post("/hediye/al").status_code, 200)
        self.assertEqual(istemci.post("/hediye/al").status_code, 409)
        hafta = istemci.get("/dunya/hafta").get_json()
        self.assertLessEqual(len(hafta["ilk"]), elo.ODULLU_SIRA)
        self.assertEqual(hafta["reyting"], 1500)
        self.assertIn("acik_setler", istemci.get("/dunya/takvim").get_json())


if __name__ == "__main__":
    unittest.main()
