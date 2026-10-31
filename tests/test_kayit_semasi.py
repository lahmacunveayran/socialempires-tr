"""GEC-04: 1.4.07'nin okuduğu yeni privateState alanları, şeması ve 0.08a göçü."""

import copy
import json
import os
import sys
import unittest
from collections import namedtuple

from ortak import KOK, bos_kayit

from oyun import kayit, kayit_semasi
from oyun.surum import migrate_loaded_save, version_code

sys.path.insert(0, os.path.join(KOK, "araclar"))
import kayit_alanlari  # noqa: E402

I = namedtuple("I", "ad isl hedefler")
ADLAR = {1: "privateState", 2: "shieldEndTime", 3: "potionsReceived", 4: "Player", 5: "[]"}


def _degismezler(s):
    return (s["playerInfo"].get("cash"), len(s["maps"]),
            [(m.get("level"), m.get("xp"), m.get("coins"), m.get("wood"), m.get("food"), m.get("stone"),
              sorted(map(tuple, m.get("items", [])))) for m in s["maps"]])


def _kayit_07():
    k = bos_kayit()
    k["version"] = "0.07a"
    k["privateState"]["attacksSent"] = [
        {"description": {"win": 1}}, {"description": {"win": "1"}}, {"description": {"win": 0}},
        {"from": "bot"},  # bot akını: sonuç yok, sayılmaz
    ]
    return k


class Arac(unittest.TestCase):
    def test_atlama_ve_hata_ayiklama_satiri_izlenir(self):
        islemler = {
            0: I("getlex", (4,), ()), 2: I("getproperty", (1,), ()),
            4: I("jump", (), (20,)), 8: I("getproperty", (3,), ()),   # atlanan anlamsız kod: sayılmaz
            20: I("debugline", (7,), ()), 22: I("getproperty", (2,), ()),
        }
        self.assertEqual(kayit_alanlari.okunan_alanlar(islemler, ADLAR.get), {"shieldEndTime"})

    def test_yerele_alinan_privatestate(self):
        islemler = {
            0: I("getproperty", (1,), ()), 2: I("coerce", (9,), ()), 4: I("setlocal_2", (), ()),
            5: I("getlocal_2", (), ()), 6: I("getproperty", (3,), ()),
            8: I("getlocal_1", (), ()), 9: I("getproperty", (2,), ()),   # başka yerel: sayılmaz
            11: I("getproperty", (1,), ()), 13: I("getproperty", (5,), ()),  # dizin erişimi ad değil
        }
        self.assertEqual(kayit_alanlari.okunan_alanlar(islemler, ADLAR.get), {"potionsReceived"})

    def test_semada_istemcinin_yeni_alanlarinin_hepsi_var(self):
        with open(os.path.join(KOK, "docs", "inceleme", "1407-kayit-alanlari.json"), encoding="utf-8") as f:
            olcum = json.load(f)
        self.assertEqual(len(olcum["yeni"]), 18)
        self.assertEqual(set(kayit_semasi.ALANLAR) - set(olcum["yeni"]), {"attacksWon"})
        self.assertLessEqual(set(olcum["yeni"]), set(kayit_semasi.ALANLAR))


class Goc(unittest.TestCase):
    def test_yoklugu_bozan_alanlar_eklenir(self):
        k = _kayit_07()
        once = _degismezler(k)
        self.assertTrue(migrate_loaded_save(k))
        ps = k["privateState"]
        self.assertEqual(k["version"], version_code)
        self.assertEqual((ps["purchasedShields"], ps["recruitmentPrices"]), ([], []))
        self.assertEqual((ps["shieldEndTime"], ps["shieldCooldown"], ps["potionsReceived"]), (0, 0, 0))
        self.assertEqual(ps["tournamentFormation"], 0)
        self.assertEqual((ps["attacksWon"], ps["attacksLost"]), (2, 1))
        self.assertEqual(kayit_semasi.guvence_hatalari(ps), [])
        self.assertEqual(_degismezler(k), once)  # I(g(s)) = I(s)
        sonra = copy.deepcopy(k)
        self.assertFalse(migrate_loaded_save(k))  # g(g(s)) = g(s)
        self.assertEqual(k, sonra)

    def test_yoklugu_ozelligi_kapali_tutan_alan_eklenmez(self):
        k = _kayit_07()
        migrate_loaded_save(k)
        for ad in ("showDailyBonus", "collectGame", "barracksQueues", "resurrectableUnits"):
            self.assertNotIn(ad, k["privateState"])
        # ilk alım teklifi sahibinin kararıyla açık (KAR-10): ilk 3 gün görünür
        self.assertEqual((k["privateState"]["firstPurchaseTimestamp"], k["privateState"]["numDayLogged"]), (0, 1))

    def test_var_olan_deger_korunur_yanlis_tur_duzelir(self):
        k = _kayit_07()
        k["privateState"].update(shieldEndTime=1700000000, attacksWon=9, purchasedShields={"a": 1},
                                 tournamentFormation=True)
        migrate_loaded_save(k)
        ps = k["privateState"]
        self.assertEqual((ps["shieldEndTime"], ps["attacksWon"]), (1700000000, 9))
        self.assertEqual((ps["purchasedShields"], ps["tournamentFormation"]), ([], 0))

    def test_eski_kayit_zincirin_sonuna_gelir(self):
        k = bos_kayit()  # 0.05a
        migrate_loaded_save(k)
        self.assertEqual(kayit_semasi.guvence_hatalari(k["privateState"]), [])

    def test_yeni_koy_alanlarla_dogar_dogrulama_eksigi_yakalar(self):
        uid = kayit.new_village()
        self.assertEqual(kayit_semasi.guvence_hatalari(kayit.session(uid)["privateState"]), [])
        kayit.kaydi_dogrula(kayit.session(uid))
        bozuk = copy.deepcopy(kayit.session(uid))
        bozuk["privateState"]["recruitmentPrices"] = None
        with self.assertRaises(ValueError):
            kayit.kaydi_dogrula(bozuk)


if __name__ == "__main__":
    unittest.main()
