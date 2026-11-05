"""Daha önce hiç testi olmayan, nakit ya da depo değiştiren komutlar (TST-02).

Her testin beklenen değeri istemcinin 1.4.07 bayt kodundan okundu (yöntem adı testte yazılı; okuma aracı
`araclar/abc_okur.py`). `Config.*` sabitleri istemcide derlenmiş değerdir, `globals.*` game_config'ten gelir: istemci
de aynı config'i okur. Uygulamanın kendi çıktısı beklenen değer yapılmadı.
"""

import json
import unittest

from ortak import KomutTesti


class NakitleKahraman(KomutTesti):
    """PopupHeroes/onBuyItem: bedel cost_unit_cash nakit, xp her durumda; sunak (150) varsa kahraman yanına konur,
    yoksa depoya konur (store_add_items ayrıca gelir) ve buy_cash koordinatı pencerenin konumudur."""

    SIFACI = 502  # Healer: cost_unit_cash 4, xp 25

    def test_sunak_varsa_haritaya(self):
        self.harita["items"].append([150, 30, 30, 0, 0, 0])
        self.komut("buy_cash", self.SIFACI, 37, 41, 1, 0)
        self.assertEqual(self.cash, 100 - 4)
        self.assertEqual(self.harita["xp"], 25)
        self.assertEqual(self.harita["items"][-1][:4], [self.SIFACI, 37, 41, 1])

    def test_sunak_yoksa_yalnizca_depoya(self):
        once = [list(e) for e in self.harita["items"]]
        self.komutlar.command("test", {"commands": [
            {"cmd": "store_add_items", "args": [json.dumps([self.SIFACI])]},
            {"cmd": "buy_cash", "args": [self.SIFACI, 512, 300, 0, 0]},
        ]})
        self.assertEqual(self.cash, 100 - 4)
        self.assertEqual(self.harita["xp"], 25)
        self.assertEqual(self.harita["items"], once)  # kahraman iki kez verilmez
        self.assertEqual(self.ps["gifts"][self.SIFACI], 1)


class HayattaKalma(KomutTesti):
    def test_ek_can(self):
        # PopupSurvival/buyLifeWithCash: bedel parseInt(globals.SURVIVAL_BUY_LIVE_CASH) = 3, argüman [bedel];
        # survivalVidasExtra bir artar
        self.komut("add_survival_vida_extra", 3)
        self.komut("add_survival_vida_extra", 3)
        self.assertEqual(self.cash, 100 - 6)
        self.assertEqual(self.ps["survivalVidasExtra"], 2)

    def test_harita_acma(self):
        # PopupSurvival/onUnlock: bedel globals.SURVIVAL_UNLOCK_MAP_CASH[i], argüman [tema_id, bedel];
        # survivalMaps[tema_id] = {ts: 0, tp: 0}
        self.komut("buy_survival_map", 7, 30)
        self.assertEqual(self.cash, 70)
        self.assertEqual(self.ps["survivalMaps"], {"7": {"ts": 0, "tp": 0}})


class AgirKusatma(KomutTesti):
    def test_nakitle_bitirme_ve_odul(self):
        # PopupHeavySiege/onPayCashClick: globals.HEAVY_SIEGE_COST_CASH (20) düşer, resetHeavySiege(true) [1, ödül];
        # ödül storeItem(..., false) ile komutsuz depoya: sunucu ekler
        self.ps["timeStampHeavySiegeAttack"] = 123
        self.komut("reset_heavy_siege", 1, 19)
        self.assertEqual(self.cash, 80)
        self.assertEqual(self.ps["timeStampHeavySiegeAttack"], 0)
        self.assertGreater(self.ps["timeStampHeavySiegePeriod"], 0)
        self.assertEqual(self.ps["gifts"][19], 1)

    def test_yenerek_bitirme_bedelsiz(self):
        # HeavySiegeCollectiveAI/Killed: resetHeavySiege(false) [0, ödül]: nakit yok
        self.komut("reset_heavy_siege", 0, 0)
        self.assertEqual(self.cash, 100)
        self.assertEqual(self.ps.get("gifts"), [])


class SaldiriPaketleri(KomutTesti):
    def test_saldiri_ve_casusluk_paketi(self):
        # PopUpBuyAssault/onBuyAttack: Config.COST_BUY_ATTACK 30 → numAttacks = Config.ATTACKS_PACK_SIZE 50;
        # Config.COST_BUY_SPYINGS 15 → numSpyings = Config.SPYINGS_PACK_SIZE 50
        self.komut("buy_attacks_pack", "")
        self.assertEqual((self.cash, self.ps["attacksPack"]), (70, 50))
        self.komut("buy_spyings_pack", "")
        self.assertEqual((self.cash, self.ps["spyingsPack"]), (55, 50))


class SiralamaOdulu(KomutTesti):
    def test_nakit_ve_esyalar_depoya(self):
        # PopupNextIslandAttack/givePrizes: eşyalar storeItem(..., false, false) ile komutsuz depoya, nakit
        # adjustStatByType(cash); komut [seviye, nakit, JSON(eşyalar)]: depoya sunucu ekler
        self.komut("apply_rewards_ranking", 3, 15, json.dumps({"19": 2, "131": 1}))
        self.assertEqual(self.cash, 115)
        self.assertEqual((self.ps["gifts"][19], self.ps["gifts"][131]), (2, 1))
        self.komut("apply_rewards_ranking", 3, 15, json.dumps({"19": 2}))  # tekrarlanan komut: bir kez
        self.assertEqual(self.cash, 115)
        self.assertEqual(self.ps["gifts"][19], 2)


class Turnuva(KomutTesti):
    def test_kayit_bedeli_ve_iadesi(self):
        # TournamentManager$/createTournament: ['g', bedel, tür, 1]; evalRefundTournament: [tür, miktar]
        self.komut("tournament_substract_resources", "g", 2000, 1, 1)
        self.assertEqual(self.harita["coins"], 48000)
        self.komut("tournament_refund_resources", "g", 2000)
        self.assertEqual(self.harita["coins"], 50000)
        self.komut("tournament_substract_resources", "c", 7, 1, 1)
        self.assertEqual(self.cash, 93)


class RuhKaristiriciGuclendirme(KomutTesti):
    """PopupSoulMixer/onBtnPowerUp@31-106: i. tıklama POWERUPS[min(i, son)].cash_cost nakit düşer; POWERUPS =
    globals.SOUL_MIXER_POWERUPS_LEVELS (config/patch/1-mega_patch.json: 1, 2, 4, 8, 15, 20). sendPowerUps@49-76
    i. güçlendirme için [min(i, son)] gönderir. Kayıtta başka hiçbir şey değişmez (güçlendirme bellekte tutulur)."""

    def test_her_guclendirme_kendi_bedeli(self):
        once = json.dumps(self.ps, sort_keys=True)
        for sira in range(3):
            self.komut("buy_powerups", sira)
        self.assertEqual(self.cash, 100 - (1 + 2 + 4))
        self.assertEqual(json.dumps(self.ps, sort_keys=True), once)

    def test_son_seviyeden_sonrasi_son_bedel(self):
        self.komut("buy_powerups", 5)
        self.assertEqual(self.cash, 100 - 20)
        self.komut("buy_powerups", 9)
        self.assertEqual(self.cash, 100 - 40)


if __name__ == "__main__":
    unittest.main()
