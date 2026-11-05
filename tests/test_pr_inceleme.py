"""PR incelemesinin API'siz parçaları: farkta yorumlanabilir satırlar ve bulguların ayrılması."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import ortak  # noqa: F401  (yol ve geçici kayıt klasörü)
from ortak import KOK

sys.path.insert(0, os.path.join(KOK, "araclar"))
import pr_inceleme  # noqa: E402

FARK = """diff --git a/oyun/a.py b/oyun/a.py
--- a/oyun/a.py
+++ b/oyun/a.py
@@ -10,3 +10,4 @@ def f():
 x = 1
-y = 2
+y = 3
+z = 4
 return x
diff --git a/eski.py b/eski.py
--- a/eski.py
+++ /dev/null
@@ -1,1 +0,0 @@
-silindi
"""


class PrIncelemeTestleri(unittest.TestCase):
    def test_yorumlanabilir_satirlar(self):
        s = pr_inceleme.yorumlanabilir_satirlar(FARK)
        self.assertEqual(s, {"oyun/a.py": {10, 11, 12, 13}})

    def test_ayir(self):
        s = pr_inceleme.yorumlanabilir_satirlar(FARK)
        b1 = {"dosya": "oyun/a.py", "satir": 11, "onem": "Orta", "tur": "hata", "metin": "m"}
        b2 = {"dosya": "oyun/a.py", "satir": 99, "onem": "Düşük", "tur": "kalite", "metin": "m"}
        b3 = {"dosya": "yok.py", "satir": 1, "onem": "Düşük", "tur": "kalite", "metin": "m"}
        icerde, disarda = pr_inceleme.ayir([b1, b2, b3], s)
        self.assertEqual(icerde, [b1])
        self.assertEqual(disarda, [b2, b3])

    def test_ozet_isaretli_ve_disardakileri_yazar(self):
        b = {"dosya": "x.py", "satir": 5, "onem": "Orta", "tur": "hata", "metin": "sorun"}
        govde = pr_inceleme.ozet_metni("tamam", [b], "")
        self.assertTrue(govde.startswith(pr_inceleme.ISARET))
        self.assertIn("`x.py:5`", govde)

    def test_sema_katı(self):
        self.assertFalse(pr_inceleme.SEMA["additionalProperties"])
        self.assertFalse(pr_inceleme.SEMA["properties"]["bulgular"]["items"]["additionalProperties"])

    def test_icerigi_arti_ya_da_eksiyle_baslayan_satir_baslik_sanilmaz(self):
        # eklenen "++ x" farkta "+++ x", silinen "-- y" farkta "--- y" görünür
        fark = ("diff --git a/n.md b/n.md\n--- a/n.md\n+++ b/n.md\n@@ -1,3 +1,3 @@\n a\n"
                "--- y\n+++ x\n b\n")
        self.assertEqual(pr_inceleme.yorumlanabilir_satirlar(fark), {"n.md": {1, 2, 3}})

    def test_sayisiz_parca_basligi_tek_satir(self):
        fark = "--- a/t.py\n+++ b/t.py\n@@ -5 +5 @@\n-eski\n+yeni\n"
        self.assertEqual(pr_inceleme.yorumlanabilir_satirlar(fark), {"t.py": {5}})

    def test_sembolik_bag_ve_depo_disi_okunmaz(self):
        with tempfile.TemporaryDirectory() as ust:
            kok = os.path.join(ust, "depo")
            os.makedirs(os.path.join(kok, "d"))
            with open(os.path.join(kok, "d", "a.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")
            gizli = os.path.join(ust, "gizli")  # depo dışında, okunabilir bir dosya
            with open(gizli, "w", encoding="utf-8") as f:
                f.write("ANAHTAR\n")
            yollar = ["d/a.py", "../gizli", gizli]
            try:
                os.symlink(gizli, os.path.join(kok, "bag.txt"))
                yollar.append("bag.txt")
            except (OSError, NotImplementedError):
                pass  # Windows'ta yetki yoksa bağ kurulamaz; depo dışı denetimi yine sınanır
            with mock.patch.object(pr_inceleme, "KOK", kok):
                baglam, _ = pr_inceleme.dosya_baglami(yollar)
        self.assertEqual(baglam, '<dosya yol="d/a.py">\nx = 1\n\n</dosya>')

    def test_bozuk_cevap_cokertmez(self):
        self.assertEqual(pr_inceleme.cevabi_coz('{"ozet": "iyi", "bulgular": []}'),
                         ({"ozet": "iyi", "bulgular": []}, None))
        for metin in ("", "{bozuk", '{"ozet": 3, "bulgular": []}', "[]"):
            with self.subTest(metin=metin):
                sonuc, hata = pr_inceleme.cevabi_coz(metin)
                self.assertIsNone(sonuc)
                self.assertTrue(hata)

    def test_kuru_kosuda_eksik_ortam_anlasilir_hata(self):
        with mock.patch.dict(os.environ, {"REPO": "", "PR": ""}), \
                mock.patch.object(sys, "argv", ["pr_inceleme.py", "--kuru"]):
            with self.assertRaises(SystemExit) as c:
                pr_inceleme.main()
        self.assertIn("REPO", str(c.exception.code))


class AnaAkisTestleri(unittest.TestCase):
    """main(): GitHub ve API taklit edilir; yazılan yorumlar incelenir."""

    def setUp(self):
        self.yazilan = []
        bulgu = {"dosya": "oyun/a.py", "satir": 11, "onem": "Orta", "tur": "hata", "metin": "sorun"}
        self.cevap = ({"ozet": "özet", "bulgular": [bulgu]}, None, "maliyet")

        def gh(*args, girdi=None):
            if args[:2] == ("pr", "view"):
                return json.dumps({"title": "t", "body": "", "headRefOid": "abc", "files": []})
            if args[:2] == ("pr", "diff"):
                return FARK
            if args[0] == "api" and "--paginate" in args:
                return "[[]]"
            yol = next(a for a in args if a.startswith("repos/"))
            if yol.endswith("/reviews") and self.inceleme_hatasi:
                raise subprocess.CalledProcessError(1, "gh", stderr="HTTP 422")
            self.yazilan.append((yol, json.loads(girdi)))
            return "{}"

        self.inceleme_hatasi = False
        self.yamalar = [mock.patch.object(pr_inceleme, "gh", gh),
                        mock.patch.object(pr_inceleme, "incele", lambda m, t: self.cevap),
                        mock.patch.dict(os.environ, {"REPO": "s/d", "PR": "7", "MODEL": "m"}),
                        mock.patch.object(sys, "argv", ["pr_inceleme.py"])]
        for y in self.yamalar:
            y.start()

    def tearDown(self):
        for y in self.yamalar:
            y.stop()

    def test_bulgu_satir_ici_ozet_ayrica(self):
        pr_inceleme.main()
        yollar = [y for y, _ in self.yazilan]
        self.assertEqual(yollar, ["repos/s/d/pulls/7/reviews", "repos/s/d/issues/7/comments"])
        self.assertEqual(self.yazilan[0][1]["comments"][0]["line"], 11)
        self.assertNotIn("`oyun/a.py:11`", self.yazilan[1][1]["body"])

    def test_satir_ici_reddedilirse_bulgu_ozete_duser(self):
        self.inceleme_hatasi = True
        pr_inceleme.main()
        self.assertEqual([y for y, _ in self.yazilan], ["repos/s/d/issues/7/comments"])
        govde = self.yazilan[0][1]["body"]
        self.assertIn("`oyun/a.py:11` (Orta, hata): sorun", govde)
        self.assertIn("yazılamadı", govde)

    def test_api_hatasinda_ozet_yazilir_is_duser(self):
        self.cevap = (None, "API hatası (400): Credit balance is too low", "")
        with self.assertRaises(SystemExit):
            pr_inceleme.main()
        self.assertEqual(len(self.yazilan), 1)
        self.assertIn("Credit balance is too low", self.yazilan[0][1]["body"])


if __name__ == "__main__":
    unittest.main()
