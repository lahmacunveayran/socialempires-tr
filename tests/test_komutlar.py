"""Komut işleyicileri: argüman sıraları istemci bytecode'undan alınmıştır.

Çalıştırma: python tests/test_komutlar.py
"""

import json
import unittest

from ortak import KomutTesti, bos_kayit


class EsyaKomutlari(KomutTesti):
    def test_buy_maliyet_xp_ve_yon(self):
        # [id, x, y, yon, kasaba, bedava, carpan, tur] - Ev I: 30 odun
        self.komut("buy", 1, 30, 31, 1, 0, 0, 1, "b")
        self.assertEqual(self.harita["wood"], 1000 - 30)
        self.assertEqual(self.harita["items"][-1][:4], [1, 30, 31, 1])
        self.assertGreater(self.harita["xp"], 0)

    def test_buy_indirim_carpani_uygulanir(self):
        self.komut("buy", 1, 30, 31, 0, 0, 0, "0.9", "u")
        self.assertEqual(self.harita["wood"], 1000 - 27)

    def test_buy_bedava(self):
        self.komut("buy", 1, 30, 31, 0, 0, 1, 1, "b")
        self.assertEqual(self.harita["wood"], 1000)
        self.assertEqual(self.harita["xp"], 0)

    def test_move_ve_orient(self):
        self.komut("move", 10, 10, 1, 40, 41, 2, 0, "MouseUsed")
        self.assertEqual(self.harita["items"][0][:4], [1, 40, 41, 2])
        self.komut("orient", 40, 41, 3, 0)
        self.assertEqual(self.harita["items"][0][3], 3)

    def test_sell_yuzde_bes_iade(self):
        self.komut("sell", 10, 10, 1, 0, 0, "")
        self.assertEqual(len(self.harita["items"]), 1)
        self.assertEqual(self.harita["wood"], 1000 + 1)  # 30 * 0.05

    def test_olmayan_esya_satilinca_iade_yok(self):
        self.komut("sell", 99, 99, 1, 0, 0, "")
        self.assertEqual(self.harita["wood"], 1000)

    def test_depoya_kaldir_ve_yerlestir(self):
        self.komut("store_item", 10, 10, 0, 1)
        self.assertEqual(self.ps["gifts"][1], 1)
        # place_gift: [id, x, y, yon, kasaba]
        self.komut("place_gift", 1, 5, 6, 1, 0)
        self.assertEqual(self.ps["gifts"], [])
        self.assertEqual(self.harita["items"][-1][:4], [1, 5, 6, 1])

    def test_depodaki_esyayi_sat(self):
        self.ps["gifts"] = [0, 2]
        self.komut("sell_stored_item", 1, 0)
        self.assertEqual(self.ps["gifts"], [0, 1])

    def test_depoya_cash_ile_esya(self):
        # [kasaba, id, cash]
        self.komut("buy_stored_item_cash", 0, 5, 7)
        self.assertEqual(self.ps["gifts"][5], 1)
        self.assertEqual(self.cash, 93)

    def test_upgrade_seviye_artirir(self):
        self.komut("upgrade", 10, 10, 0)
        self.assertEqual(self.harita["items"][0][5], 1)
        self.assertEqual(self.harita["items"][0][0], 1)

    def test_bina_kilidi_ve_tema(self):
        self.komut("unlock_building", "9001")  # min_level 20 -> 7 cash
        self.assertEqual(self.ps["unlockedEarlyBuildings"], {"9001": True})
        self.assertEqual(self.cash, 93)
        self.komut("unlock_skin", "3")
        self.komut("set_skin", 0, "3")
        self.assertEqual(self.ps["unlockedSkins"], {"3": True})
        self.assertEqual(self.harita["skin"], 3)

    def test_ikinci_kasaba_acilir(self):
        self.kayit["playerInfo"]["cash"] = 50
        self.komut("buy_map", 1, 1, "t", 0)
        self.assertEqual(len(self.kayit["maps"]), 2)
        self.assertEqual(self.kayit["maps"][1]["race"], "t")
        self.assertEqual(self.cash, 50 - 22)
        self.assertEqual(len(self.kayit["playerInfo"]["map_names"]), 2)


class UretimKomutlari(KomutTesti):
    def test_collect_kaynak_ve_sayac(self):
        # [x, y, kasaba, id, birimler, carpan, cash] - 19: altın madeni
        self.komut("collect_new", 20, 20, 0, 19, 1, 1, 0)
        self.assertGreater(self.harita["items"][1][4], 0)

    def test_collect_kisa_bicim(self):
        once = self.harita["xp"]
        self.komut("collect_new", 20, 20, 0, 19)
        self.assertGreaterEqual(self.harita["xp"], once)
        self.assertGreater(self.harita["items"][1][4], 0)

    def test_pazar_alim_istemci_formulu(self):
        # [kasaba, kaynak, satis, miktar]: odun tabanı 100 -> 100 odun = 100 altın
        self.komut("trade_resource_b", 0, "w", 0, 100)
        self.assertEqual(self.harita["coins"], 50000 - 100)
        self.assertEqual(self.harita["wood"], 1100)
        self.assertEqual(self.harita["resourcesTraded"]["w"], 1)
        # İkinci alım %2 pahalı
        self.komut("trade_resource_b", 0, "w", 0, 100)
        self.assertEqual(self.harita["coins"], 50000 - 100 - 102)

    def test_pazar_satis(self):
        self.komut("trade_resource_b", 0, "w", 1, 100)
        self.assertEqual(self.harita["coins"], 50000 + 75)
        self.assertEqual(self.harita["wood"], 900)
        self.assertEqual(self.harita["resourcesTraded"]["w"], -1)

    def test_birim_binaya_girer_cikar(self):
        self.harita["items"].append([512, 3, 3, 0, 0, 0])
        self.komut("push_unit", 3, 3, 512, 20, 20, 0)
        self.assertEqual(self.harita["items"][1][6], [512])
        self.komut("pop_unit", 20, 20, 0, 512, 4, 4, 2)
        self.assertEqual(self.harita["items"][1][6], [])
        self.assertEqual(self.harita["items"][-1][:4], [512, 4, 4, 2])

    def test_birim_deposu(self):
        self.harita["items"].append([512, 3, 3, 0, 0, 0])
        self.komut("add_unit_warehouse", 3, 3, 0, 512)
        self.assertEqual(self.harita["warehousedUnits"], [512])
        self.komut("reset_warehouse", 0)
        self.assertEqual(self.harita["warehousedUnits"], [])
        self.assertEqual(self.ps["gifts"][512], 1)

    def test_uretim_secimi_ve_yardim(self):
        self.komut("activate", 20, 20, 0, 19, 2)
        self.assertEqual(self.harita["items"][1][7]["cp"], 2)
        once = self.harita["items"][1][4]
        self.komut("accept_collect_help", 20, 20, 0, 19, "arkadas")
        self.assertEqual(self.harita["items"][1][4], once - 3600)


class GorevVeBonusKomutlari(KomutTesti):
    def test_gorev_tamamla_ve_odul_bir_kez(self):
        self.komut("complete_mission", 2, 0)
        self.komut("complete_mission", 2, 0)
        self.assertEqual(self.ps["completedMissions"], [2])
        self.komut("reward_mission", 0, 2)
        self.komut("reward_mission", 0, 2)
        self.assertEqual(self.harita["coins"], 50000 + 10)

    def test_gorev_atlama_bedeli(self):
        self.komut("complete_mission", 2, 1)
        self.assertEqual(self.cash, 98)

    def test_gunluk_bonus_istemcinin_odulu(self):
        # [altin, kasaba, kahraman, gun, cash]
        self.komut("win_bonus", 250, 0, 0, 1, 0)
        self.assertEqual(self.harita["coins"], 50250)
        self.assertEqual(self.ps["bonusNextId"], 2)
        self.komut("win_bonus", 0, 0, 555, 2, 0)
        self.assertEqual(self.ps["gifts"][555], 1)

    def test_pazartesi_ve_geri_donus(self):
        self.komut("weekly_reward", "g", 2500)
        self.assertEqual(self.harita["coins"], 52500)
        self.komut("comeback_reward", "u", 512, 3)
        self.assertEqual(self.ps["gifts"][512], 1)
        self.assertEqual(self.ps["comebackBonusCollected"], [3])

    def test_hazine_dogru_kasabaya(self):
        # [altin, xp, gorev, x, y, kasaba]
        self.komut("collect_treasure", 500, 60, 1, 0, 0, 0)
        self.assertEqual(self.harita["coins"], 50500)
        self.assertEqual(self.harita["xp"], 60)

    def test_teklif_paketi(self):
        self.kayit["playerInfo"]["cash"] = 100
        self.komut("buy_offer_pack", 0, 66)
        self.assertEqual(self.cash, 60)
        self.assertGreaterEqual(self.ps["gifts"][9101], 1)

    def test_birim_koleksiyonu_bir_kez(self):
        self.komut("unit_collections_completed", 4)
        self.komut("unit_collections_completed", 4)
        self.assertEqual(self.ps["unitCollectionsCompleted"], ["4"])
        self.assertEqual(self.cash, 101)

    def test_yardim_listesi_buyur(self):
        self.komut("set_help_map", "pvp")
        self.komut("set_help_map", "quest")
        self.assertEqual(self.ps["helpMap"], ["pvp", "quest"])

    def test_takimlar_moda_gore(self):
        self.komut("set_attack_team", "tournament", json.dumps([512, 516]))
        self.komut("set_attack_team", "quest", json.dumps([1]))
        self.assertEqual(self.ps["teams"], {"tournament": [512, 516], "quest": [1]})


class SeviyeKomutlari(KomutTesti):
    def test_bozuk_xp_yok_sayilir(self):
        self.komut("rt_publish_score", 10 ** 12)
        self.assertEqual(self.harita["xp"], 0)

    def test_seviye_siniri_asilirsa_son_seviye(self):
        from oyun.config import get_game_config, get_level_from_xp
        self.assertEqual(get_level_from_xp(10 ** 12), len(get_game_config()["levels"]) - 1)


class BuyuVeMezarlik(KomutTesti):
    def test_mana_altin_veya_cash(self):
        self.komut("buy_mana_new", 0, 0)
        self.assertEqual(self.harita["coins"], 50000 - 20000)
        self.komut("buy_mana_new", 0, 1)
        self.assertEqual(self.cash, 99)
        self.assertEqual(self.ps["mana"], 10)

    def test_buyu_al_ve_kullan(self):
        self.komut("buy_magic", 2, 0, 0)  # Fire Havoc: 1000 altın, 5 mana
        self.assertEqual(self.harita["coins"], 49000)
        self.assertIn("2", self.ps["magics"])
        self.ps["mana"] = 7
        self.komut("use_magic", 2)
        self.assertEqual(self.ps["mana"], 2)

    def test_mezarlik_ve_diriltme(self):
        self.komut("put_graveyard", 512)
        self.assertEqual(self.ps["deadHeroes"], {"512": 1})
        self.komut("resurrect_hero", 512, 5, 5, 0, "1")
        self.assertEqual(self.ps["deadHeroes"], {})
        self.assertEqual(self.ps["potion"], 0)
        self.assertEqual(self.harita["items"][-1][:3], [512, 5, 5])


class GenelDavranis(KomutTesti):
    def test_bozuk_komut_digerlerini_dusurmez(self):
        veri = {"commands": [
            {"cmd": "move", "args": ["bozuk"]},
            {"cmd": "complete_mission", "args": [2, 0]},
        ]}
        self.komutlar.command("test", veri)
        self.assertEqual(self.ps["completedMissions"], [2])

    def test_bilinmeyen_komut_hata_vermez(self):
        self.komut("boyle_bir_komut_yok", 1, 2)

    def test_istemcinin_tum_komutlari_karsilaniyor(self):
        """İstemci SWF'sinin gönderdiği tüm komut adları kayıtlı olmalı."""
        istemci = {
            "accept_collect_help", "activate", "activate_dragon", "activate_monster",
            "add_collectable", "add_items_store", "add_survival_vida_extra", "add_unit_warehouse",
            "admin_add_animal", "apply_rewards_ranking", "assist_neighbor", "assist_neighbor_new",
            "assist_receive", "assist_send_feed", "attack_player", "buy", "buy_cash", "buy_magic",
            "buy_map", "buy_mana_new", "buy_monster_step_cash", "buy_offer_pack", "buy_si_help",
            "buy_step_cash", "buy_stored_item_cash", "buy_super_offer_pack", "buy_survival_map",
            "buy_temple_step_cash", "clean_attacks", "clean_received_assists", "clear_message",
            "clear_tiles_area", "collect_new", "collect_treasure", "comeback_reward",
            "complete_mission", "complete_tutorial", "cross_promotion_finished", "darts_new_free",
            "darts_reset", "darts_shoot_balloon", "desactivate_dragon", "desactivate_monster",
            "end_attack", "end_quest", "end_survival", "exchange_cash_new", "expand",
            "fast_forward", "finish_collection", "finish_dragon_help", "finish_si", "game_status",
            "gold_statue_conversion", "graveyard_buy_potions", "increase_population", "kill",
            "load_map", "modify_position_univers", "move", "name_map", "next_dragon",
            "next_monster", "next_monster_step", "next_step", "next_temple_step", "orient",
            "perform_city_quest", "ping", "place_gift", "place_iphone", "place_stored_item",
            "pop_sell", "pop_unit", "push_unit", "put_graveyard", "reset",
            "reset_completed_missions", "reset_heavy_siege", "reset_position_univers",
            "reset_temple", "reset_warehouse", "reset_world_change", "resurrect_hero",
            "reward_mission", "rider_buy_step_cash", "rider_next_step", "rider_select",
            "rt_level_up", "rt_publish_achievement_unit", "rt_publish_score", "save_map", "sell",
            "sell_gift", "sell_iphone_item", "sell_stored_item", "set_attack_team",
            "set_fake_neighbors", "set_help_map", "set_info_showed", "set_quest_var",
            "set_resource_allies", "set_skin", "set_strategy", "set_variables", "spy_player",
            "start_heavy_siege", "start_quest", "start_survival", "store_add_items", "store_item",
            "store_item_frombug", "system_set_count_hack", "tournament_refund_resources",
            "tournament_substract_resources", "trade_resource_b", "unit_collections_completed",
            "unlock_building", "unlock_skin", "upgrade", "use_magic", "weekly_reward", "win_bonus",
            "buy_attacks_pack", "buy_spyings_pack", "buy_warehouse_capacity_single",
            "buy_pvp_territory", "place_warehoused_item",
        }
        self.assertEqual(sorted(istemci - set(self.komutlar.KOMUTLAR)), [])


class KomsuKomutlari(KomutTesti):
    def setUp(self):
        super().setUp()
        self.komsu = bos_kayit("komsu")
        self.kayitlar["komsu"] = self.komsu

    def test_komsuya_yardim(self):
        self.komut("assist_neighbor_new", "komsu", 0, json.dumps([[5, 5, 1], [6, 6, 19]]))
        self.assertEqual(self.harita["coins"], 50020)
        self.assertEqual(self.harita["xp"], 6)
        self.assertIn("ukomsu", self.ps["neighborAssists"])
        self.assertEqual(self.komsu["maps"][0]["receivedAssists"], {"utest": [[5, 5, 1], [6, 6, 19]]})

    def test_yardim_arabasi_ve_temizleme(self):
        self.harita["receivedAssists"] = {"ukomsu": [[5, 5, 19]]}
        self.komut("assist_receive", 0, 19)
        self.assertEqual(self.harita["xp"], 10)
        self.komut("clean_received_assists", "komsu", 0)
        self.assertEqual(self.harita["receivedAssists"], {})

    def test_sosyal_bina_iscisi(self):
        self.harita["items"].append([6, 40, 40, 0, 0, 0])
        self.komut("buy_si_help", 40, 40, 0, 6)
        self.assertEqual(self.cash, 98)
        self.assertEqual(self.harita["items"][-1][7]["si"], [0])
        self.komut("finish_si", 40, 40, 0, 6)
        self.assertNotIn("si", self.harita["items"][-1][7])

    def test_koleksiyon_parcasi(self):
        self.komut("add_collectable", 2, 3)
        self.assertEqual(self.ps["collections"][2], [0, 0, 0, 1, 0, 0])


class PvpKomutlari(KomutTesti):
    def setUp(self):
        super().setUp()
        self.kurban = bos_kayit("rakip")
        self.kurban["playerInfo"]["name"] = "Rakip"
        self.kayitlar["rakip"] = self.kurban

    def saldir(self, **ek):
        veri = {"victim_id": "rakip", "map": 0, "win": 1,
                "resources": {"g": 0}, "resources_victim": {"g": 10}}
        veri.update(ek)
        self.komut("end_attack", json.dumps(veri))

    def test_saldiri_sonucu_iki_tarafa_uygulanir(self):
        self.saldir(resources={"x": 5, "g": 25}, resources_victim={"g": 100})
        self.assertEqual(self.harita["coins"], 50100)
        self.assertEqual(self.harita["xp"], 5)
        self.assertEqual(self.kurban["maps"][0]["coins"], 50000 - 100)
        rapor = self.kurban["privateState"]["attacksReceived"][0]
        self.assertEqual(rapor["attacker_id"], "test")
        self.assertEqual(self.ps["attacksSent"][0]["victim_id"], "rakip")

    def test_ayni_hedefe_ikinci_saldiri_reddedilir(self):
        self.saldir()
        ilk = self.kurban["maps"][0]["coins"]
        self.saldir()
        self.assertEqual(self.kurban["maps"][0]["coins"], ilk)

    def test_kalkanli_hedefe_saldiri_reddedilir(self):
        self.kurban["privateState"]["shield_until"] = 2 ** 40
        self.saldir()
        self.assertEqual(self.kurban["maps"][0]["coins"], 50000)

    def test_kupa_kazanilir_ve_istemciden_alinmaz(self):
        self.saldir(trophies=100000)
        self.assertEqual(self.ps["trophies"], 8)

    def test_ganimet_kurbanin_yuzde_onu(self):
        self.kurban["maps"][0]["coins"] = 30
        self.saldir(resources_victim={"g": 100})
        self.assertEqual(self.kurban["maps"][0]["coins"], 27)

    def test_saldiri_raporlari_temizlenir(self):
        self.ps["attacksReceived"] = [{"time": 1}, {"time": 2}]
        self.komut("clean_attacks")
        self.assertEqual(self.ps["attacksReceived"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
