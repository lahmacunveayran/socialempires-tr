"""GOR-01: eski görev numaralarının 1.4.07 hedef numaralarına göçü (GEC-04)."""

import copy
import json
import os
import sys
import unittest

from ortak import KOK, bos_kayit

from oyun import kayit
from oyun.surum import gorev_tablosu, migrate_loaded_save, version_code
from oyun.yollar import SAVES_DIR

sys.path.insert(0, os.path.join(KOK, "araclar"))
import gorev_gocu  # noqa: E402


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def _degismezler(s):
    """I(s): göçün dokunmaması gereken değerler (YOL_HARITASI_1407 §2)."""
    return (s["playerInfo"].get("cash"), len(s["maps"]),
            [(m.get("level"), m.get("xp"), m.get("coins"), m.get("wood"), m.get("food"), m.get("stone"),
              sorted(map(tuple, m.get("items", [])))) for m in s["maps"]])


class Tablo(unittest.TestCase):
    def test_dosya_aractan_uretilenle_ayni(self):
        self.assertEqual(_oku(gorev_gocu.TABLO), json.loads(gorev_gocu._yaz_metni(gorev_gocu.uret())))

    def test_her_eslesmede_odul_ayni_ve_bire_bir(self):
        eski = {int(g["id"]): g for g in _oku(gorev_gocu.TABAN)["missions"]}
        yeni = {int(h["id"]): h for h in _oku(gorev_gocu.HEDEFLER)}
        t = gorev_tablosu()
        self.assertEqual(len(t), 190)
        self.assertEqual(len(set(t.values())), len(t), "iki eski görev aynı hedefe düşmez")
        for e, y in t.items():
            self.assertEqual(eski[e]["reward"], yeni[y]["reward"], (e, y))

    def test_bilinen_ornekler(self):
        t = gorev_tablosu()
        self.assertEqual(t[11], 11)  # eğitimdeki "Train 2 villagers"
        self.assertNotIn(110, t)  # aynı başlıklı Town Hall II görevi: ödülü başka, 1.4.07'de yok
        self.assertNotIn(113, t)  # "Get Treasure Chest!": 1.4.07'de 113 "Train 3 Medium Knights"
        self.assertEqual(t[136], 148)  # Big Church → Great Church
        self.assertEqual(t[125], 137)  # Build Tower III, numarası kaymış
        self.assertNotIn(30, t)  # 3 okçu → 5 okçu: iş değişti


class Goc(unittest.TestCase):
    def test_eski_istemci_kaydinda_butun_numaralar_cevrilir(self):
        k = bos_kayit()  # 0.05a
        k["privateState"].update(completedMissions=[11, 110, 113, 125, 136], rewardedMissions=[11, 113, 136])
        once = _degismezler(k)
        self.assertTrue(migrate_loaded_save(k))
        self.assertEqual(k["version"], version_code)
        self.assertEqual(k["privateState"]["completedMissions"], [11, 137, 148])
        self.assertEqual(k["privateState"]["rewardedMissions"], [11, 148])
        self.assertEqual(_degismezler(k), once)  # I(g(s)) = I(s)
        sonra = copy.deepcopy(k)
        self.assertFalse(migrate_loaded_save(k))  # g(g(s)) = g(s)
        self.assertEqual(k, sonra)

    def test_0_06a_kaydinda_yalnizca_yedektekiler_eski(self):
        k = bos_kayit()
        k["version"] = "0.06a"
        # 113 ve 136 göçten önce vardı; 242 (Attack 2 players) 1.4.07'de kazanıldı
        k["privateState"].update(completedMissions=[113, 136, 242], rewardedMissions=[136, 242])
        self.assertTrue(migrate_loaded_save(k, {113, 136}))
        self.assertEqual(k["privateState"]["completedMissions"], [148, 242])
        self.assertEqual(k["privateState"]["rewardedMissions"], [148, 242])

    def test_0_06a_yedeksiz_kayitta_numaralar_degismez(self):
        k = bos_kayit()
        k["version"] = "0.06a"
        k["privateState"].update(completedMissions=[113, 136], rewardedMissions=[113])
        self.assertTrue(migrate_loaded_save(k, set()))
        self.assertEqual(k["privateState"]["completedMissions"], [113, 136])

    def test_yuklemede_goc_oncesi_yedek_okunur(self):
        uid = "gorevgocu"
        eski = bos_kayit(uid)
        eski["privateState"].update(completedMissions=[113, 136], rewardedMissions=[136])
        simdi = copy.deepcopy(eski)
        simdi["version"] = "0.06a"
        simdi["privateState"].update(completedMissions=[113, 136, 242], rewardedMissions=[136, 242])
        os.makedirs(kayit.BACKUP_DIR, exist_ok=True)
        yollar = [os.path.join(kayit.BACKUP_DIR, f"{uid}.goc-{s}.save.json") for s in ("0.05a", "0.06a")]
        yol = os.path.join(SAVES_DIR, uid + ".save.json")
        for y in yollar + [yol, yol + ".bak"]:
            self.addCleanup(lambda y=y: os.path.exists(y) and os.remove(y))
        for y, veri in ((yollar[0], eski), (yol, simdi)):
            with open(y, "w", encoding="utf-8") as f:
                json.dump(veri, f)
        self.addCleanup(kayit.load_saved_villages)
        kayit.load_saved_villages()
        ps = _oku(yol)["privateState"]
        self.assertEqual(ps["completedMissions"], [148, 242])
        self.assertEqual(ps["rewardedMissions"], [148, 242])
        self.assertEqual(_oku(yollar[1])["privateState"]["completedMissions"], [113, 136, 242])  # 0.06a hâli de saklı


if __name__ == "__main__":
    unittest.main()
