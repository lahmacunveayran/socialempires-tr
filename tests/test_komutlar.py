# -*- coding: utf-8 -*-
"""Sunucu komutlarının birim testleri.

Flask ve jsonpatch kurulu olmasa da çalışsın diye ikisi için hafif
stub'lar kurulur; testler doğrudan `command.do_command` çağırır.

Çalıştırma:
    python tests\\test_komutlar.py
"""

import copy
import json
import os
import shutil
import sys
import types
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)


# --- flask stub -----------------------------------------------------------
try:
    import flask  # noqa: F401
except ImportError:
    _flask = types.ModuleType("flask")
    _flask.session = {}
    sys.modules["flask"] = _flask

# --- jsonpatch stub (RFC 6902'nin kullanılan alt kümesi) ------------------
try:
    import jsonpatch  # noqa: F401
except ImportError:
    _jp = types.ModuleType("jsonpatch")

    def _parcalar(yol):
        return [p.replace("~1", "/").replace("~0", "~") for p in yol.split("/")[1:]]

    def _bul(doc, parcalar_):
        hedef = doc
        for p in parcalar_:
            hedef = hedef[int(p)] if isinstance(hedef, list) else hedef[p]
        return hedef

    def _ekle(doc, parcalar_, deger):
        if not parcalar_:
            return deger
        ust = _bul(doc, parcalar_[:-1])
        son = parcalar_[-1]
        if isinstance(ust, list):
            if son == "-":
                ust.append(deger)
            else:
                ust.insert(int(son), deger)
        else:
            ust[son] = deger
        return doc

    def _sil(doc, parcalar_):
        ust = _bul(doc, parcalar_[:-1])
        son = parcalar_[-1]
        if isinstance(ust, list):
            del ust[int(son)]
        else:
            del ust[son]
        return doc

    def apply_patch(doc, patch, in_place=False):
        hedef = doc if in_place else copy.deepcopy(doc)
        for islem in patch:
            op = islem["op"]
            yol = _parcalar(islem["path"])
            if op == "add":
                hedef = _ekle(hedef, yol, islem["value"])
            elif op == "replace":
                _bul(hedef, yol[:-1])[yol[-1]] = islem["value"]
            elif op == "test":
                assert _bul(hedef, yol) == islem["value"], "test basarisiz"
            elif op == "remove":
                _sil(hedef, yol)
            elif op == "copy":
                _ekle(hedef, yol, copy.deepcopy(_bul(hedef, _parcalar(islem["from"]))))
            elif op == "move":
                deger = copy.deepcopy(_bul(hedef, _parcalar(islem["from"])))
                _sil(hedef, _parcalar(islem["from"]))
                _ekle(hedef, yol, deger)
            else:
                raise NotImplementedError(op)
        return hedef

    _jp.apply_patch = apply_patch
    _jp.make_patch = lambda a, b: []
    sys.modules["jsonpatch"] = _jp

import command  # noqa: E402
import sessions  # noqa: E402
from constants import Constant  # noqa: E402


def bos_kayit():
    return {
        "version": "0.05a",
        "playerInfo": {"pid": "test", "name": "Test", "cash": 100, "default_map": 0},
        "maps": [{
            "id": 0, "coins": 50000, "wood": 1000, "stone": 1000, "food": 1000,
            "xp": 0, "level": 10, "expansions": [13],
            "items": [[1, 10, 10, 0, 0, 0], [19, 20, 20, 0, 0, 0]],
            "resourcesTraded": {},
        }],
        "privateState": {
            "gifts": [], "completedMissions": [], "rewardedMissions": [],
            "potion": 1, "marketTimestamp": 0, "lastUpgrades": [],
        },
    }


class KomutTestleri(unittest.TestCase):
    def setUp(self):
        self.kayit = bos_kayit()
        self._eski_session = command.session
        self._eski_save = command.save_session
        command.session = lambda userid: self.kayit
        command.save_session = lambda userid: None

    def tearDown(self):
        command.session = self._eski_session
        command.save_session = self._eski_save

    def test_bozuk_komut_digerlerini_dusurmez(self):
        veri = {
            "ts": 0, "first_number": 0, "accessToken": "x",
            "tries": 0, "publishActions": 0,
            "commands": [
                {"cmd": Constant.CMD_COLLECT, "args": []},          # hatalı komut
                {"cmd": Constant.CMD_UPGRADE, "args": [1, 10, 10, 0]},
            ],
        }
        kaydedilen = []
        command.save_session = lambda userid: kaydedilen.append(userid)
        command.command("test", veri)
        self.assertEqual(kaydedilen, ["test"])
        self.assertEqual(self.kayit["maps"][0]["items"][0][0], 2)

    # -- yükseltme ---------------------------------------------------------
    def test_yukseltme_esya_id_ve_konumdan_bulunur(self):
        command.do_command("test", Constant.CMD_UPGRADE, [1, 10, 10, 0])
        esya = self.kayit["maps"][0]["items"][0]
        self.assertEqual(esya[0], 2, "House I, House II'ye yükselmeliydi")
        self.assertEqual(self.kayit["maps"][0]["wood"], 1000 - 60)
        self.assertEqual(self.kayit["maps"][0]["xp"], 6)

    def test_yukseltme_arguman_sirasi_degisse_de_calisir(self):
        # aynı üçlü farklı sırada: (10, 0, 1, 10)
        command.do_command("test", Constant.CMD_UPGRADE, [10, 0, 1, 10])
        self.assertEqual(self.kayit["maps"][0]["items"][0][0], 2)

    def test_yukseltme_hedef_id_gonderilse_de_calisir(self):
        # istemci mevcut bina yerine hedef kimliği (2) göndermiş olsun
        command.do_command("test", Constant.CMD_UPGRADE, [2, 10, 10, 0])
        self.assertEqual(self.kayit["maps"][0]["items"][0][0], 2)

    def test_yukseltilemeyen_esya_hata_vermez(self):
        command.do_command("test", Constant.CMD_UPGRADE, [19, 20, 20, 0])
        self.assertEqual(self.kayit["maps"][0]["items"][1][0], 19)

    def test_yukseltme_yetersiz_kaynakta_reddedilir(self):
        self.kayit["maps"][0]["wood"] = 10
        command.do_command("test", Constant.CMD_UPGRADE, [1, 10, 10, 0])
        self.assertEqual(self.kayit["maps"][0]["items"][0][0], 1)
        self.assertEqual(self.kayit["maps"][0]["wood"], 10)

    def test_collect_zaman_damgasi_guncellenir(self):
        esya = self.kayit["maps"][0]["items"][1]  # (20,20) Tree
        self.assertEqual(esya[4], 0)
        command.do_command("test", Constant.CMD_COLLECT, [20, 20, 0, 19, 1, 1, 0])
        self.assertGreater(esya[4], 0)
        self.assertEqual(self.kayit["maps"][0]["wood"], 1000 + 20)

    def test_bos_collect_cokmez(self):
        command.do_command("test", Constant.CMD_COLLECT, [])

    # -- pazar -------------------------------------------------------------
    def test_pazar_alim_json_paketiyle(self):
        veri = json.dumps({"resource": "w", "amount": 100, "action": "buy", "map": 0})
        command.do_command("test", Constant.CMD_TRADE_RESOURCE, [veri])
        harita = self.kayit["maps"][0]
        self.assertEqual(harita["wood"], 1100)
        self.assertEqual(harita["coins"], 50000 - 100 * 100)
        self.assertEqual(harita["resourcesTraded"]["w"], 100)

    def test_pazar_satim_json_paketiyle(self):
        veri = json.dumps({"resource": "f", "amount": 100, "action": "sell", "map": 0})
        command.do_command("test", Constant.CMD_TRADE_RESOURCE, [veri])
        harita = self.kayit["maps"][0]
        self.assertEqual(harita["food"], 900)
        self.assertEqual(harita["coins"], 50000 + int(100 * 0.75 * 100))
        self.assertEqual(harita["resourcesTraded"]["f"], -25)  # MAX_DECREMENTS sınırı

    def test_pazar_yetersiz_altin_reddeder(self):
        self.kayit["maps"][0]["coins"] = 10
        veri = json.dumps({"resource": "w", "amount": 100, "action": "buy"})
        command.do_command("test", Constant.CMD_TRADE_RESOURCE, [veri])
        self.assertEqual(self.kayit["maps"][0]["wood"], 1000)
        self.assertEqual(self.kayit["maps"][0]["coins"], 10)

    def test_pazar_sayaci_guncellenir(self):
        command.do_command("test", Constant.CMD_SET_RESOURCES_TRADED, [json.dumps({"w": 7, "s": 3})])
        self.assertEqual(self.kayit["maps"][0]["resourcesTraded"], {"w": 7, "s": 3})

    # -- depo --------------------------------------------------------------
    def test_depoya_ekle_ve_yerlestir(self):
        command.do_command("test", Constant.CMD_ADD_ITEMS_TO_STORE, [json.dumps({"id": 5, "count": 2})])
        self.assertEqual(self.kayit["privateState"]["gifts"][5], 2)

        command.do_command("test", Constant.CMD_PLACE_STORED_ITEM, [5, 30, 30, 0])
        self.assertEqual(self.kayit["privateState"]["gifts"][5], 1)
        self.assertIn([5, 30, 30, 0], [i[:4] for i in self.kayit["maps"][0]["items"]])

    def test_depodan_satim(self):
        self.kayit["privateState"]["gifts"] = [0, 0, 0, 0, 0, 1]
        command.do_command("test", Constant.CMD_SELL_STORED, [5, 0])
        self.assertLessEqual(len(self.kayit["privateState"]["gifts"]), 5)

    # -- diriltme / görev --------------------------------------------------
    def test_resurrect_hero_calismazsa_hata_vermez(self):
        command.do_command("test", Constant.CMD_RESURRECT_HERO, [512, 5, 5, 0, "1"])
        eklenen = self.kayit["maps"][0]["items"][-1]
        self.assertEqual(eklenen[0], 512)
        self.assertEqual(eklenen[1:3], [5, 5])

    def test_gorev_iki_kez_tamamlanmaz(self):
        command.do_command("test", Constant.CMD_COMPLETE_MISSION, [2, 0])
        command.do_command("test", Constant.CMD_COMPLETE_MISSION, [2, 0])
        self.assertEqual(self.kayit["privateState"]["completedMissions"].count(2), 1)

    def test_gorev_odulu_iki_kez_verilmez(self):
        self.kayit["privateState"]["completedMissions"] = [2]
        command.do_command("test", Constant.CMD_REWARD_MISSION, [0, 2])
        ilk = self.kayit["maps"][0]["coins"]
        command.do_command("test", Constant.CMD_REWARD_MISSION, [0, 2])
        self.assertEqual(self.kayit["maps"][0]["coins"], ilk)

    def test_gercek_kayit_uzerinde_yukseltme(self):
        """Gerçek bir köy kaydı (7 elemanlı eşyalar) üzerinde yükseltme."""
        from get_game_config import get_item_from_id
        yol = os.path.join(KOK, "villages", "AcidCaos.json")
        with open(yol, encoding="utf-8") as f:
            kayit = json.load(f)
        command.session = lambda userid: kayit

        harita = kayit["maps"][0]
        harita["coins"] = 10 ** 6
        harita["wood"] = 10 ** 6
        harita["stone"] = 10 ** 6

        hedef = None
        for esya in harita["items"]:
            cfg = get_item_from_id(esya[0])
            if cfg and cfg.get("upgrades_to") not in (0, "0", None):
                hedef = esya
                break
        self.assertIsNotNone(hedef, "Test kaydında yükseltilebilir bina yok")

        eski_id = hedef[0]
        yeni_id = int(get_item_from_id(eski_id)["upgrades_to"])
        command.do_command("test", Constant.CMD_UPGRADE, [eski_id, hedef[1], hedef[2], 0])
        self.assertEqual(hedef[0], yeni_id)
        # Kayıt yeniden JSON'a yazılabiliyor mu?
        json.dumps(kayit)


class KayitTestleri(unittest.TestCase):
    def setUp(self):
        gecici_kok = os.path.join(KOK, "tests", "_gecici")
        os.makedirs(gecici_kok, exist_ok=True)
        self.gecici = os.path.join(gecici_kok, f"{os.getpid()}-{id(self)}")
        os.makedirs(self.gecici, exist_ok=True)
        self._eski_saves = sessions.SAVES_DIR
        self._eski_backup = sessions.BACKUP_DIR
        sessions.SAVES_DIR = self.gecici
        sessions.BACKUP_DIR = os.path.join(self.gecici, "backups")

    def tearDown(self):
        sessions.SAVES_DIR = self._eski_saves
        sessions.BACKUP_DIR = self._eski_backup
        shutil.rmtree(self.gecici, ignore_errors=True)

    def test_004a_kaydi_005a_ya_migrate_edilir(self):
        from version import migrate_loaded_save
        kayit = bos_kayit()
        kayit["version"] = "0.04a"
        del kayit["privateState"]["marketTimestamp"]
        del kayit["maps"][0]["resourcesTraded"]
        self.assertTrue(migrate_loaded_save(kayit))
        self.assertEqual(kayit["version"], "0.05a")
        self.assertEqual(kayit["privateState"]["marketTimestamp"], 0)
        self.assertEqual(kayit["maps"][0]["resourcesTraded"], {})

    def test_atomik_kayit_ve_yedek(self):
        userid = sessions.new_village()
        yol = os.path.join(self.gecici, f"{userid}.save.json")
        self.assertTrue(os.path.exists(yol))

        sessions.save_session(userid)  # ikinci yazım -> .bak oluşmalı
        self.assertTrue(os.path.exists(yol + ".bak"))
        self.assertFalse(os.path.exists(yol + ".tmp"))

        with open(yol, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["version"], "0.05a")


class ZamanOlcegiTestleri(unittest.TestCase):
    def test_istemci_config_sureleri_bolunur(self):
        from get_game_config import get_game_config, get_client_game_config
        os.environ["TIME_SCALE"] = "2"
        try:
            ham = get_game_config()
            istemci = get_client_game_config()
            mill_ham = next(i for i in ham["items"] if i["id"] == "5")
            mill_istemci = next(i for i in istemci["items"] if i["id"] == "5")
            self.assertAlmostEqual(float(mill_ham["activation"]), 21600)
            self.assertAlmostEqual(float(mill_istemci["activation"]), 10800)
        finally:
            os.environ.pop("TIME_SCALE", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
