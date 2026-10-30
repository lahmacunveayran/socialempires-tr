"""Çeviri kapsamı (araclar/ceviri_kapsami.py) ve config hattı (araclar/config_hatti.py) ölçüm araçları.

Gerçek istemci gerekmez: küçük bir SWF (test_komut_imzalari.swf_kur) ve elle kurulmuş config ile sınanır.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

import ortak  # noqa: F401

sys.path.insert(0, os.path.join(ortak.KOK, "araclar"))
import ceviri_kapsami as ck  # noqa: E402
import config_hatti as ch  # noqa: E402
from test_komut_imzalari import abc_kur, swf_kur  # noqa: E402


class DilMetni(unittest.TestCase):
    def test_dil_metni(self):
        self.assertTrue(ck.dil_metni_mi("Buy now"))
        self.assertTrue(ck.dil_metni_mi("<b>OK</b>"))
        self.assertFalse(ck.dil_metni_mi("12:30"))
        self.assertFalse(ck.dil_metni_mi("#0# / #1#"))
        self.assertFalse(ck.dil_metni_mi("<br>"))
        self.assertFalse(ck.dil_metni_mi("x"))
        self.assertFalse(ck.dil_metni_mi(None))

    def test_oran(self):
        o = ck.oran([("a", "Attack", True), ("b", "Defend", False), ("c", "100", False)])
        self.assertEqual((o["cevrilen"], o["gereken"]), (1, 2))
        self.assertAlmostEqual(o["T"], 0.5)
        self.assertEqual(o["kalan"], [("b", "Defend")])
        self.assertEqual(ck.oran([])["T"], 1.0)

    def test_hedef_metinleri(self):
        hedefler = [{"id": 0, "title": "none", "description": "none", "instructions": ""},
                    {"id": 7, "title": "Build a farm", "description": "Farms give food", "instructions": "Click"}]
        self.assertEqual(ck.hedef_metinleri(hedefler), [
            ("goal:7:baslik", "Build a farm"), ("goal:7:aciklama", "Farms give food"),
            ("goal:7:talimat", "Click")])


class Olcum(unittest.TestCase):
    def test_dort_oran(self):
        config = {
            "localization_strings": [{"name": "A", "text": "Attack #0#"}, {"name": "B", "text": "Defend"}],
            "items": [{"id": 1, "name": "Farm"}],
            "goals": [{"id": 3, "title": "Win", "description": "none", "instructions": ""}],
        }
        ceviriler = {"loc:A": "Saldır #0#", "loc:B": "Savun yer tutucusuz #1#", "item:1": "Çiftlik"}
        sozluk = {"metin_alanlari": {}, "statik_yazilar": {}, "as3_dizeleri": {"Level ": "Seviye "}}
        sonuc = ck.olc(swf_kur(abc_kur()), config, sozluk=sozluk, ceviriler=ceviriler)
        # B'nin çevirisi yer tutucuyu bozuyor: gönderilmez, çevrilmemiş sayılır
        self.assertEqual((sonuc["config_loc"]["cevrilen"], sonuc["config_loc"]["gereken"]), (1, 2))
        self.assertEqual(sonuc["config_bolumleri"]["esya"]["T"], 1.0)
        self.assertEqual((sonuc["hedefler"]["cevrilen"], sonuc["hedefler"]["gereken"]), (0, 1))
        self.assertEqual((sonuc["as3_dizeleri"]["cevrilen"], sonuc["as3_dizeleri"]["gereken"]), (1, 1))
        self.assertEqual(sonuc["swf_metin_alanlari"]["gereken"], 0)
        self.assertIn("Config loc adları", ck.markdown([("deneme", sonuc)]))

    def test_config_kur_yamalari_sirayla_uygular_ve_tekrari_atar(self):
        klasor = tempfile.mkdtemp()
        try:
            taban = os.path.join(klasor, "taban.json")
            with open(taban, "w", encoding="utf-8") as f:
                json.dump({"items": [{"id": 1, "v": "eski"}], "globals": {}}, f)
            yamalar = os.path.join(klasor, "patch")
            os.mkdir(yamalar)
            for ad, yama in (("b.json", [{"op": "add", "path": "/globals/X", "value": 2}]),
                             ("a.json", [{"op": "add", "path": "/items/-", "value": {"id": 1, "v": "yeni"}},
                                         {"op": "add", "path": "/globals/X", "value": 1}])):
                with open(os.path.join(yamalar, ad), "w", encoding="utf-8") as f:
                    json.dump(yama, f)
            config = ck.config_kur([yamalar], taban)
        finally:
            shutil.rmtree(klasor)
        self.assertEqual(config["items"], [{"id": 1, "v": "yeni"}])
        self.assertEqual(config["globals"]["X"], 2)  # a.json'dan sonra b.json


class ConfigHatti(unittest.TestCase):
    C = {
        "items": [{"id": 1, "ad": "Farm", "sure": 5}, {"id": 2, "ad": "Mill"}],
        "localization_strings": [{"id": "9", "name": "OK", "text": "OK"}],
        "globals": {"X": 1},
    }

    def durum(self, islem):
        return ch.islem_durumu(self.C, islem)[0]

    def test_durumlar(self):
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 2, "ad": "Mill"}}), "aynı")
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 1, "ad": "Farm"}}),
                         "kapsanıyor")
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 1, "ad": "Çiftlik"}}),
                         "farklı")
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 3}}), "yeni")
        self.assertEqual(self.durum({"op": "add", "path": "/globals/X", "value": 1}), "aynı")
        self.assertEqual(self.durum({"op": "add", "path": "/globals/Y", "value": 1}), "yeni")
        self.assertEqual(self.durum({"op": "replace", "path": "/globals/Y", "value": 1}), "yolu yok")
        self.assertEqual(self.durum({"op": "add", "path": "/yok/Z", "value": 1}), "yolu yok")
        # yerelleştirmede eş `name` ile bulunur, `id` farkı alan farkı olarak görünür
        durum, ayrinti = ch.islem_durumu(self.C, {"op": "add", "path": "/localization_strings/-",
                                                  "value": {"id": "1", "name": "OK", "text": "OK"}})
        self.assertEqual((durum, ayrinti), ("farklı", {"alanlar": ["id"]}))

    def test_hukum(self):
        self.assertEqual(ch.hukum({"aynı": 2, "kapsanıyor": 1}), "gider")
        self.assertEqual(ch.hukum({"aynı": 1, "yeni": 1}), "kalır")
        self.assertEqual(ch.hukum({"yeni": 1, "farklı": 1}), "çatışır")
        self.assertEqual(ch.hukum({"farklı": 1, "yolu yok": 1}), "uygulanamaz")

    def test_dokunulan_anahtarlar(self):
        yama = [{"op": "add", "path": "/globals/DRAGONS", "value": 1}, {"op": "add", "path": "/items/-"}]
        self.assertEqual(ch.dokunulan_anahtarlar(yama), {"globals", "DRAGONS", "items"})


if __name__ == "__main__":
    unittest.main()
