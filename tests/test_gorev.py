"""Görev kitabının bulgu kaydı (docs/gorev/BULGULAR.json) denetlenebilir kalsın."""

import json
import os
import re
import unittest

from ortak import KOK

YOL = os.path.join(KOK, "docs", "gorev", "BULGULAR.json")
ALANLAR = {"id", "baslik", "sinif", "onem", "durum", "isaret", "kanit", "test", "pr", "onay", "notlar"}
DURUMLAR = {"acik", "dogrulandi", "curutuldu", "ci_bekliyor", "duzeltildi", "onay_bekliyor",
            "karar_verildi", "engelli", "ertelendi"}
SINIFLAR = {"hata", "ozellik", "karar"}
ONEMLER = {"Yüksek", "Orta", "Düşük"}
ISARETLER = {"✔", "◐", "?"}


class BulguKaydiTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(YOL, encoding="utf-8") as f:
            cls.kayit = json.load(f)

    def test_ust_alanlar(self):
        self.assertTrue({"surum", "guncelleme", "devam_noktasi", "maddeler"} <= set(self.kayit))
        self.assertRegex(self.kayit["guncelleme"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue({"faz", "madde", "sonraki_adim"} <= set(self.kayit["devam_noktasi"]))

    def test_maddeler(self):
        kimlikler = set()
        for m in self.kayit["maddeler"]:
            with self.subTest(m.get("id")):
                self.assertEqual(set(m), ALANLAR)
                self.assertRegex(m["id"], r"^[A-Z0-9]+-\d{2}$")
                self.assertNotIn(m["id"], kimlikler)
                kimlikler.add(m["id"])
                self.assertIn(m["durum"], DURUMLAR)
                self.assertIn(m["sinif"], SINIFLAR)
                self.assertIn(m["onem"], ONEMLER)
                self.assertIn(m["isaret"], ISARETLER)
                self.assertTrue(m["kanit"].strip(), "kanıtsız madde olmaz")
                if m["pr"] is not None:
                    self.assertRegex(m["pr"], r"^#\d+$")
                if m["durum"] == "duzeltildi":
                    self.assertIsNotNone(m["pr"], "düzeltilen madde bir PR'a bağlı olmalı")
                if m["durum"] == "karar_verildi":
                    self.assertTrue(m["onay"], "kararın kimden ve ne zaman geldiği yazılı olmalı")

    def test_devam_noktasi_var_olan_maddeyi_gosterir(self):
        madde = self.kayit["devam_noktasi"]["madde"]
        if madde is not None:
            self.assertIn(madde, {m["id"] for m in self.kayit["maddeler"]})

    def test_test_alanindaki_dosyalar_var(self):
        for m in self.kayit["maddeler"]:
            for yol in re.findall(r"(?:tests|araclar)/[\w/.-]+\.(?:py|js)", m["test"] or ""):
                with self.subTest(m["id"], yol=yol):
                    self.assertTrue(os.path.exists(os.path.join(KOK, yol)), yol)


if __name__ == "__main__":
    unittest.main()
