"""PR incelemesinin API'siz parçaları: farkta yorumlanabilir satırlar ve bulguların ayrılması."""

import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
