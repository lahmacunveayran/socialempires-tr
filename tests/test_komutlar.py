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
        self._eski_komsu = command.neighbor_session
        command.session = lambda userid: self.kayit
        command.neighbor_session = lambda userid: self.kayit if userid == "test" else None
        command.save_session = lambda userid: None

    def tearDown(self):
        command.session = self._eski_session
        command.neighbor_session = self._eski_komsu
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

    def test_publish_score_maksimum_xp_dogru_seviyeye_cevrilir(self):
        # 2016089205 = 99. seviyenin XP eşiği; eskiden 0. seviyeye düşürüyordu.
        command.do_command("test", Constant.CMD_RT_PUBLISH_SCORE, [2016089205])
        self.assertEqual(self.kayit["maps"][0]["xp"], 2016089205)
        self.assertEqual(self.kayit["maps"][0]["level"], 99)

    def test_publish_score_absurt_xp_yok_sayilir(self):
        self.kayit["maps"][0]["xp"] = 140
        self.kayit["maps"][0]["level"] = 4
        command.do_command("test", Constant.CMD_RT_PUBLISH_SCORE, [10 ** 12])
        self.assertEqual(self.kayit["maps"][0]["xp"], 140)
        self.assertEqual(self.kayit["maps"][0]["level"], 4)

    def test_seviye_siniri_asilirsa_son_seviye(self):
        from get_game_config import get_game_config, get_level_from_xp
        self.assertEqual(get_level_from_xp(10 ** 12), len(get_game_config()["levels"]) - 1)

    # -- PvP ---------------------------------------------------------------
    def test_saldiri_sonucu_iki_tarafa_uygulanir(self):
        kurban = bos_kayit()
        kurban["playerInfo"]["pid"] = "rakip"
        kurban["playerInfo"]["name"] = "Rakip"
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum
        command.neighbor_session = cozum

        veri = json.dumps({
            "victim_id": "rakip", "map": 0, "win": 1, "duration": 20,
            "resources": {"x": 5, "g": 25},
            "resources_victim": {"g": 100},
            "attacker_units": [[512, 1, 0, 0]], "victim_units": [],
            "voluntary_end": 1,
        })
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])

        # İki tarafa da aynı miktar (istenen 100, tavan %10)
        self.assertEqual(self.kayit["maps"][0]["coins"], 50100)
        self.assertEqual(self.kayit["maps"][0]["xp"], 5)
        self.assertEqual(kurban["maps"][0]["coins"], 50000 - 100)

        raporlar = kurban["privateState"]["attacksReceived"]
        self.assertEqual(len(raporlar), 1)
        self.assertEqual(raporlar[0]["attacker_id"], "test")
        self.assertEqual(raporlar[0]["description"]["oponent"]["name"], "Test")

        gonderilen = self.kayit["privateState"]["attacksSent"]
        self.assertEqual(gonderilen[0]["victim_id"], "rakip")

    def test_ayni_hedefe_ikinci_saldiri_reddedilir(self):
        kurban = bos_kayit()
        kurban["playerInfo"]["pid"] = "rakip"
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum
        command.neighbor_session = cozum

        veri = json.dumps({
            "victim_id": "rakip", "map": 0, "win": 1,
            "resources": {"g": 0}, "resources_victim": {"g": 10},
        })
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        ilk = kurban["maps"][0]["coins"]
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        self.assertEqual(kurban["maps"][0]["coins"], ilk)

    def test_kalkanli_hedefe_saldiri_reddedilir(self):
        kurban = bos_kayit()
        kurban["playerInfo"]["pid"] = "rakip"
        kurban["privateState"]["shield_until"] = 2 ** 40
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum
        command.neighbor_session = cozum
        veri = json.dumps({"victim_id": "rakip", "map": 0, "win": 1,
                           "resources": {"g": 0}, "resources_victim": {"g": 10}})
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        self.assertEqual(kurban["maps"][0]["coins"], 50000)
        self.assertEqual(len(kurban["privateState"].get("attacksReceived", [])), 0)

    def test_intikam_ayni_hedefe_izin_verir(self):
        from engine import timestamp_now
        kurban = bos_kayit()
        kurban["playerInfo"]["pid"] = "rakip"
        self.kayit["privateState"]["attacksReceived"] = [{"time": timestamp_now(), "attacker_id": "rakip", "description": {}}]
        self.kayit["privateState"]["attacksSent"] = [{"victim_id": "rakip", "time": str(timestamp_now())}]
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum
        command.neighbor_session = cozum
        veri = json.dumps({"victim_id": "rakip", "map": 0, "win": 1,
                           "resources": {"g": 0}, "resources_victim": {"g": 10}})
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        self.assertEqual(kurban["maps"][0]["coins"], 50000 - 10)

    def test_kupa_kazanilir_ve_kaybedilir(self):
        kurban = bos_kayit()
        kurban["playerInfo"]["pid"] = "rakip"
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum
        command.neighbor_session = cozum
        veri = json.dumps({"victim_id": "rakip", "map": 0, "win": 1,
                           "resources": {"g": 0}, "resources_victim": {"g": 1}})
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        self.assertEqual(self.kayit["privateState"]["trophies"], 8)
        self.assertEqual(kurban["privateState"]["trophies"], 0)

    def test_saldiri_kurban_kaynagindan_fazla_alinamaz(self):
        kurban = bos_kayit()
        kurban["playerInfo"]["pid"] = "rakip"
        kurban["maps"][0]["coins"] = 30
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum
        command.neighbor_session = cozum
        veri = json.dumps({
            "victim_id": "rakip", "map": 0, "win": 1,
            "resources": {"g": 0}, "resources_victim": {"g": 100},
        })
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        # 30 coinin en fazla %10'u = 3 coin gider
        self.assertEqual(kurban["maps"][0]["coins"], 27)


    def test_xp_enjeksiyonu_sinirlanir(self):
        kurban = bos_kayit(); kurban["playerInfo"]["pid"] = "rakip"
        kurban["maps"][0]["level"] = 1
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum; command.neighbor_session = cozum
        once = self.kayit["maps"][0]["xp"]
        veri = json.dumps({"victim_id": "rakip", "map": 0, "win": 1,
                           "resources": {"x": 999999999}, "resources_victim": {}})
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        self.assertLessEqual(self.kayit["maps"][0]["xp"] - once, 2)

    def test_kupa_istemciden_alinmaz(self):
        kurban = bos_kayit(); kurban["playerInfo"]["pid"] = "rakip"
        cozum = lambda uid: self.kayit if uid == "test" else (kurban if uid == "rakip" else None)
        command.session = cozum; command.neighbor_session = cozum
        veri = json.dumps({"victim_id": "rakip", "map": 0, "win": 1,
                           "resources": {}, "resources_victim": {}, "trophies": 100000})
        command.do_command("test", Constant.CMD_END_ATTACK, [veri])
        self.assertEqual(self.kayit["privateState"]["trophies"], 8)

    def test_olmayan_esya_satilinca_iade_yok(self):
        once = self.kayit["maps"][0]["wood"]
        command.do_command("test", Constant.CMD_SELL, [99, 99, 1, 0, 0, "test"])
        self.assertEqual(self.kayit["maps"][0]["wood"], once)

    def test_saldiri_raporlari_temizlenir(self):
        self.kayit["privateState"]["attacksReceived"] = [{"time": 1}, {"time": 2}]
        command.do_command("test", Constant.CMD_CLEAN_ATTACKS, [])
        self.assertEqual(self.kayit["privateState"]["attacksReceived"], [])

    def test_saldiri_takimi_kaydedilir(self):
        command.do_command("test", Constant.CMD_SET_ATTACK_TEAM, [json.dumps({"units": [512, 516]})])
        self.assertEqual(self.kayit["privateState"]["teams"]["attack"], {"units": [512, 516]})

    def test_sosyal_bina_lonca_ile_tamamlanir(self):
        self.kayit["maps"][0]["items"].append([299, 56, 59, 0, 0, 0])
        command.do_command("test", Constant.CMD_FINISH_SI, [56, 59, 0, 299])
        esya = [e for e in self.kayit["maps"][0]["items"] if e[1] == 56 and e[2] == 59][0]
        self.assertGreaterEqual(len(esya), 8)
        self.assertEqual(esya[7]["workers"], 5)
        self.assertTrue(esya[7].get("guild"))

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



class DunyaTestleri(unittest.TestCase):
    def test_birim_sayilari_ve_guc(self):
        import world
        kayit = bos_kayit()
        kayit["maps"][0]["items"].append([512, 30, 30, 0, 0, 0, [], {}])
        self.assertEqual(world.birim_sayilari(kayit).get(512), 1)
        self.assertGreater(world.ordu_gucu({512: 2}), 0)

    def test_rapor_ekle(self):
        import world
        kurban = bos_kayit()
        saldiran = bos_kayit()
        world.rapor_ekle(kurban, saldiran, {"time": 1})
        self.assertEqual(len(kurban["privateState"]["attacksReceived"]), 1)

    def test_dunya_tick_ekonomiyi_ilerletir(self):
        import world
        bot = bos_kayit()
        bot["playerInfo"].update(pid="bot1", bot=True, name="Bot")
        kayitlar = {"bot1": bot}
        eski = (world.all_saves_userid, world.session, world.save_session)
        world.all_saves_userid = lambda: list(kayitlar)
        world.session = lambda uid: kayitlar.get(uid)
        world.save_session = lambda uid: None
        try:
            d = world.Dunya()
            d.ayar["saldiri_olasiligi"] = 0
            once = bot["maps"][0]["wood"]
            d.tek_tick()
            self.assertEqual(d.tick, 1)
            self.assertGreater(bot["maps"][0]["wood"], once)
        finally:
            world.all_saves_userid, world.session, world.save_session = eski



class CeviriTestleri(unittest.TestCase):
    def test_istemci_config_turkce_gelir(self):
        from get_game_config import get_game_config, get_client_game_config
        tr = get_client_game_config("tr")
        en = get_game_config()
        tr_sozluk = {e["name"]: e["text"] for e in tr["localization_strings"] if isinstance(e, dict)}
        en_sozluk = {e["name"]: e["text"] for e in en["localization_strings"] if isinstance(e, dict)}
        self.assertEqual(tr_sozluk.get("AUX_ACEPTAR"), "Kabul Et")
        self.assertEqual(en_sozluk.get("AUX_ACEPTAR"), "Accept")
        self.assertEqual(tr["levels"][0]["name"], "Köle")
        # Asıl config değişmemeli
        self.assertEqual(en["levels"][0]["name"], "Slave")

    def test_yer_tutucular_korunur(self):
        from turkce import dogrula
        self.assertEqual(dogrula("Hi #0#, you have #1# gold", "Merhaba #0#, #1# altının var"), [])



class TurnuvaAdaTestleri(unittest.TestCase):
    def test_turnuva_dort_oyuncuyla_kurulur(self):
        import turnuva
        kayitlar = {}
        for i in range(6):
            k = bos_kayit()
            k["playerInfo"].update(pid=f"b{i}", name=f"Bot {i}", bot=True)
            kayitlar[f"b{i}"] = k
        oyuncu = bos_kayit()
        oyuncu["playerInfo"].update(pid="u1", name="Oyuncu", bot=False)
        kayitlar["u1"] = oyuncu
        eski = (turnuva.all_saves_userid, turnuva.session, turnuva.save_session)
        turnuva.all_saves_userid = lambda: list(kayitlar)
        turnuva.session = lambda uid: kayitlar.get(uid)
        turnuva.save_session = lambda uid: None
        try:
            t = turnuva.turnuva_olustur("u1")
            self.assertEqual(len(t["players"]), 4)
            self.assertEqual(len(t["matches"]), 6)
        finally:
            turnuva.all_saves_userid, turnuva.session, turnuva.save_session = eski

    def test_adada_yedi_bolge_ve_fetih(self):
        import ada
        kayitlar = {}
        for i in range(8):
            k = bos_kayit()
            k["playerInfo"].update(pid=f"b{i}", name=f"Bot {i}", bot=True)
            kayitlar[f"b{i}"] = k
        oyuncu = bos_kayit()
        oyuncu["playerInfo"].update(pid="u1", name="Oyuncu", bot=False)
        kayitlar["u1"] = oyuncu
        eski = (ada.all_saves_userid, ada.session)
        ada.all_saves_userid = lambda: list(kayitlar)
        ada.session = lambda uid: kayitlar.get(uid)
        try:
            slotlar = ada.ada_slotlari(oyuncu)
            self.assertEqual(len(slotlar), 7)
            ada.fetih_kaydet(oyuncu, slotlar[0]["user_id"])
            self.assertEqual(ada.ada_durumu(oyuncu)["fetih"], 1)
        finally:
            ada.all_saves_userid, ada.session = eski


    def test_turnuva_bot_maclari_ve_tek_odul(self):
        import turnuva
        kayitlar = {}
        for i in range(7):
            k = bos_kayit()
            k["playerInfo"].update(pid=f"b{i}", name=f"Bot {i}", bot=True)
            k["maps"][0]["level"] = 10 + i
            kayitlar[f"b{i}"] = k
        oyuncu = bos_kayit()
        oyuncu["playerInfo"].update(pid="u1", name="Oyuncu", bot=False)
        kayitlar["u1"] = oyuncu
        eski = (turnuva.all_saves_userid, turnuva.session, turnuva.save_session)
        turnuva.all_saves_userid = lambda: list(kayitlar)
        turnuva.session = lambda uid: kayitlar.get(uid)
        turnuva.save_session = lambda uid: None
        try:
            t = turnuva.turnuva_olustur("u1")
            for _ in range(3):
                sonuc = turnuva.mac_baslat(t["id"], "u1")
                if not sonuc:
                    break
                turnuva.mac_bitir(t["id"], "u1", True)
            self.assertEqual(t["state"], "finished")
            self.assertEqual(oyuncu["privateState"]["trophies"], 30)
            turnuva.mac_bitir(t["id"], "u1", True)
            self.assertEqual(oyuncu["privateState"]["trophies"], 30)
        finally:
            turnuva.all_saves_userid, turnuva.session, turnuva.save_session = eski

    def test_ada_tamamlaninca_sonraki_adaya_gecer(self):
        import ada
        kayitlar = {}
        for i in range(7):
            k = bos_kayit()
            k["playerInfo"].update(pid=f"b{i}", name=f"Bot {i}", bot=True)
            kayitlar[f"b{i}"] = k
        oyuncu = bos_kayit()
        oyuncu["playerInfo"].update(pid="u1", name="Oyuncu", bot=False)
        kayitlar["u1"] = oyuncu
        eski = (ada.all_saves_userid, ada.session)
        ada.all_saves_userid = lambda: list(kayitlar)
        ada.session = lambda uid: kayitlar.get(uid)
        try:
            slotlar = ada.ada_slotlari(oyuncu)
            for slot in slotlar:
                ada.fetih_kaydet(oyuncu, slot["user_id"])
            self.assertEqual(ada.ada_durumu(oyuncu)["ada"], 100)
            self.assertEqual(ada.ada_durumu(oyuncu)["fetih"], 0)
        finally:
            ada.all_saves_userid, ada.session = eski

    def test_sezon_hafta_bicimi(self):
        import sezon
        self.assertRegex(sezon._hafta(), r"^\d{4}-W\d{2}$")


class MagazaGorevTestleri(unittest.TestCase):

    def test_komut_gorev_tamamla_odul(self):
        k = bos_kayit()
        eski_kaydet = command.save_session
        command.save_session = lambda uid: None
        command.session = lambda uid: k
        try:
            command.do_command("test", Constant.CMD_COMPLETE_MISSION, ["2", "0"])
            self.assertIn(2, k["privateState"]["completedMissions"])
            command.do_command("test", Constant.CMD_REWARD_MISSION, ["0", "2"])
            self.assertGreaterEqual(k["maps"][0]["coins"], 50000 + 10)
            self.assertIn(2, k["privateState"]["rewardedMissions"])
        finally:
            command.save_session = eski_kaydet

    def test_komut_teklif_al(self):
        k = bos_kayit()
        k["playerInfo"]["cash"] = 100
        eski_kaydet = command.save_session
        command.save_session = lambda uid: None
        command.session = lambda uid: k
        try:
            command.do_command("test", Constant.CMD_BUY_OFFER, ["1"])
            self.assertEqual(k["playerInfo"]["cash"], 75)
        finally:
            command.save_session = eski_kaydet



    def test_koleksiyon_basarisizsa_tuketmez(self):
        import koleksiyon
        from odul import depo, depo_adet
        k = bos_kayit()
        depo(k, 719, 15)
        self.assertFalse(koleksiyon.tamamla(k, 33))
        self.assertEqual(depo_adet(k, 719), 15)

    def test_depo_tutarsiz_kayitta_da_sinir_koyar(self):
        import magaza
        k = bos_kayit()
        k["playerInfo"]["cash"] = 1000
        k["privateState"]["warehouse_capacity"] = 1000
        k["privateState"]["warehouse_capacity_step"] = 19
        self.assertFalse(magaza.depo_kapasite(k, tek=True))
        self.assertEqual(k["playerInfo"]["cash"], 1000)

    def test_gorev_sifirlama_odulu_tekrar_vermez(self):
        import gorev
        k = bos_kayit()
        gorev.tamamla(k, 2)
        gorev.odul(k, 0, 2)
        once = k["maps"][0]["coins"]
        gorev.sifirla(k)
        gorev.tamamla(k, 2)
        self.assertFalse(gorev.odul(k, 0, 2))
        self.assertEqual(k["maps"][0]["coins"], once)

    def test_koleksiyon_costs_ayri_ayri_ister(self):
        import koleksiyon
        from odul import depo
        eksik = bos_kayit()
        depo(eksik, 719, 15)
        self.assertFalse(koleksiyon.tamamla(eksik, 33))
        tam = bos_kayit()
        depo(tam, 719, 15)
        depo(tam, 721, 20)
        self.assertTrue(koleksiyon.tamamla(tam, 33))

    def test_ic_ice_paket_cokmez(self):
        import magaza
        k = bos_kayit()
        k["playerInfo"]["cash"] = 100
        self.assertTrue(magaza.teklif_al(k, 0, 11))
        self.assertEqual(k["playerInfo"]["cash"], 40)
        from odul import depo_adet
        self.assertGreaterEqual(depo_adet(k, 60), 1)

    def test_negatif_carpan_reddedilir(self):
        import magaza
        k = bos_kayit()
        self.assertFalse(magaza.satin_al(k, 0, 1, 0, 0, True, -5))

    def test_depo_azami_kapasite(self):
        import magaza
        k = bos_kayit()
        k["privateState"]["warehouse_capacity_step"] = 19
        k["playerInfo"]["cash"] = 1000
        self.assertFalse(magaza.depo_kapasite(k, tek=True))

    def test_gorev_tamamla_ve_odul(self):
        import gorev
        k = bos_kayit()
        self.assertTrue(gorev.tamamla(k, 2))
        self.assertIn(2, k["privateState"]["completedMissions"])
        self.assertTrue(gorev.odul(k, 0, 2))
        self.assertFalse(gorev.odul(k, 0, 2))

    def test_teklif_paketi_cash_dusurur(self):
        import magaza
        k = bos_kayit()
        k["playerInfo"]["cash"] = 100
        self.assertTrue(magaza.teklif_al(k, 0, 1))
        self.assertEqual(k["playerInfo"]["cash"], 75)
        self.assertEqual(k["maps"][0]["coins"], 50000 + 5000)

    def test_cash_borsasi_ve_depo(self):
        import magaza
        k = bos_kayit()
        k["playerInfo"]["cash"] = 100
        self.assertTrue(magaza.cash_borsasi(k, 0))
        self.assertEqual(k["maps"][0]["coins"], 50000 + 2500)
        self.assertTrue(magaza.depo_kapasite(k))
        self.assertEqual(k["privateState"]["warehouse_capacity_step"], 1)

    def test_koleksiyon_tamamlanir(self):
        import koleksiyon
        k = bos_kayit()
        k["privateState"]["gifts"] = [0] * 700
        k["privateState"]["gifts"][509] = 1
        self.assertTrue(koleksiyon.tamamla(k, 1))
        self.assertIn("1", k["privateState"]["unitCollections"])
        self.assertFalse(koleksiyon.tamamla(k, 1))

    def test_etkinlikler_tek_kez(self):
        import etkinlik
        k = bos_kayit()
        self.assertTrue(etkinlik.pazartesi_bonus(k, 0))
        self.assertFalse(etkinlik.pazartesi_bonus(k, 0))
        self.assertTrue(etkinlik.hazine(k, 0))
        self.assertFalse(etkinlik.hazine(k, 0))

    def test_basari_acilir(self):
        import basari
        k = bos_kayit()
        k["privateState"]["completedMissions"] = [2]
        yeni = basari.kontrol(k)
        self.assertIn("ilk_gorev", yeni)


class SosyalTestleri(unittest.TestCase):
    def test_komsu_yardimi_odul_ve_kayit(self):
        import sosyal
        a = bos_kayit(); a["playerInfo"]["pid"] = "a"
        b = bos_kayit(); b["playerInfo"]["pid"] = "b"
        self.assertTrue(sosyal.yardim_et(a, b, "b"))
        self.assertEqual(a["maps"][0]["coins"], 50000 + 100)
        self.assertEqual(len(b["privateState"]["receivedAssists"]), 1)
        self.assertFalse(sosyal.yardim_et(a, b, "b"))  # aynı gün tekrar

    def test_hediye_gonder_ve_limit(self):
        import sosyal
        from odul import depo, depo_adet
        a = bos_kayit(); a["playerInfo"]["pid"] = "a"
        b = bos_kayit(); b["playerInfo"]["pid"] = "b"
        depo(a, 500, 1)
        self.assertTrue(sosyal.hediye_gonder(a, b, "b", 500))
        self.assertEqual(depo_adet(a, 500), 0)
        self.assertEqual(depo_adet(b, 500), 1)
        self.assertFalse(sosyal.hediye_gonder(a, b, "b", 500))


class CeviriKapsamTestleri(unittest.TestCase):
    def test_bos_olmayan_tum_metinler_cevrilmis(self):
        from get_game_config import get_game_config
        from turkce import _bolum_anahtarlari, cevirileri_yukle
        ceviri = cevirileri_yukle()
        eksik = [k for k, _b, m, _y in _bolum_anahtarlari(get_game_config()) if m.strip() and k not in ceviri]
        self.assertEqual(eksik, [])




    def test_yeni_paket_satin_alma(self):
        import magaza
        k = bos_kayit()
        k["playerInfo"]["cash"] = 100
        self.assertTrue(magaza.teklif_al(k, 0, 66))
        self.assertEqual(k["playerInfo"]["cash"], 60)
        from odul import depo_adet
        self.assertGreaterEqual(depo_adet(k, 9101), 1)

    def test_yeni_icerik_yuklendi(self):
        from get_game_config import get_game_config
        c = get_game_config()
        adlar = {i["id"]: i["name"] for i in c["items"]}
        self.assertEqual(adlar.get("9001"), "Büyük Ev")
        self.assertEqual(adlar.get("9101"), "Süper Şövalye")
        self.assertIn(66, [p["id"] for p in c["offer_packs"]])

    def test_istemci_ascii_modunda_turkce_harf_yok(self):
        from get_game_config import get_client_game_config
        c = get_client_game_config("tr", ascii_mode=True)
        metinler = [i["name"] for i in c["items"]]
        metinler += [m["title"] for m in c["missions"]]
        metinler += [e["text"] for e in c["localization_strings"] if isinstance(e, dict)]
        kotu = [m for m in metinler if any(h in m for h in "şğİıçöüŞĞÇÖÜ")]
        self.assertEqual(kotu, [])

    def test_esya_ve_gorev_turkce(self):
        from get_game_config import get_client_game_config
        c = get_client_game_config("tr")
        adlar = {i["id"]: i["name"] for i in c["items"]}
        self.assertEqual(adlar["1"], "Ev I")
        self.assertEqual(c["missions"][1]["title"][:3], "Köy")


class OyunDongusuTestleri(unittest.TestCase):
    def test_gunluk_giris_tek_kez(self):
        import gunluk
        k = bos_kayit()
        self.assertTrue(gunluk.giris(k))
        self.assertFalse(gunluk.giris(k))
        self.assertEqual(gunluk.durum(k)["seri"], 1)

    def test_gunluk_gorev_odulu(self):
        import gunluk
        k = bos_kayit()
        d = gunluk.durum(k)
        gorev = d["gorevler"][0]
        gorev["ilerleme"] = gorev["hedef"] - 1
        gorev["alindi"] = 0
        once = k["maps"][0]["coins"]
        gunluk.ilerle(k, gorev["id"], 1)
        self.assertEqual(gorev["alindi"], 1)
        self.assertGreaterEqual(k["maps"][0]["coins"], once)

    def test_haftalik_meydan_okuma(self):
        import gunluk
        k = bos_kayit()
        h = gunluk.durum(k)["haftalik"]
        h["ilerleme"] = h["hedef"] - 1
        h["alindi"] = 0
        gunluk.ilerle(k, h["id"], 1)
        self.assertEqual(h["alindi"], 1)

    def test_ittifak_kararli(self):
        from world import Dunya
        d = Dunya()
        self.assertEqual(d._ittifak("abc"), d._ittifak("abc"))
        self.assertIn(d._ittifak("abc"), (0, 1, 2))
        self.assertIn(d.ittifak_adi("abc"), ("Kizil Birlik", "Mavi Birlik", "Yesil Birlik"))

    def test_dunya_olayi_biter(self):
        import time
        from world import Dunya
        d = Dunya()
        d.aktif_olay = {"tur": "savas", "metin": "test", "bitis": int(time.time()) - 1}
        d._olay_guncelle(int(time.time()))
        self.assertIsNone(d.aktif_olay)

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

    def test_seviye_xp_ile_duzeltilir(self):
        kayit = bos_kayit()
        kayit["maps"][0]["xp"] = 2016089205
        kayit["maps"][0]["level"] = 0
        self.assertTrue(sessions._seviyeyi_duzelt(kayit))
        self.assertEqual(kayit["maps"][0]["level"], 99)

    def test_turkce_isim_yuklenirken_bozulmaz(self):
        userid = sessions.new_village()
        kayit = sessions.session(userid)
        kayit["playerInfo"]["name"] = "Gökbörü"
        sessions.save_session(userid)
        sessions.load_saved_villages()
        self.assertEqual(sessions.session(userid)["playerInfo"]["name"], "Gökbörü")

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
