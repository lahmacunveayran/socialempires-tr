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


class ZamanMakinesi(KomutTesti):
    """PopupSelectTime: paket no = globals.TIME_MACHINE sırası (bindData@46-210). game_config_20120826:
    [{0.5 sa, 2}, {1, 4}, {4, 12}, {8, 25}, {12, 40}, {24, 75}]. onBuy@98-193: canAfford(price) ise nakit düşer,
    countTimePacket[no] + 1. onUse@102-137: amountInStock > 0 ise bir azalır ve time_ff gider; ardından istemci
    haritayı sunucudan yeniden yükler (@272), zamanı kendisi kaydırmaz."""

    def test_paket_alma(self):
        self.komut("buy_time_packet", 2)
        self.komut("buy_time_packet", 2)
        self.komut("buy_time_packet", 0)
        self.assertEqual(self.cash, 100 - 12 - 12 - 2)
        self.assertEqual(self.ps["countTimePacket"], [1, 0, 2])

    def test_nakit_yetmezse_alinmaz(self):
        self.ps["countTimePacket"] = []
        self.komut("buy_time_packet", 5)  # 75
        self.assertEqual(self.cash, 25)
        self.komut("buy_time_packet", 5)
        self.assertEqual(self.cash, 25)
        self.assertEqual(self.ps["countTimePacket"], [0, 0, 0, 0, 0, 1])

    def test_kullanma_paketi_harcar_ve_zamani_ilerletir(self):
        # 1 saatlik paket (sıra 1): her gerçek zaman damgası 3600 sn geri çekilir; 0 ve -1 gibi işaretler kalır
        simdi = self.komutlar.timestamp_now()
        self.ps["countTimePacket"] = [0, 1]
        self.ps.update(timestampLastBonus=simdi - 10, riderTimeStamp=-1, timeStampTakeCare=0,
                       shield_until=simdi + 999)
        self.ps["barracksQueues"] = {"q1": {"ts": simdi + 500, "amount": 1}}
        self.ps["attacksSent"] = [{"time": simdi - 60, "victim_id": "k"}]
        self.harita["items"] = [[19, 20, 20, 0, simdi - 5, 0], [512, 3, 4, 0, 0, 0]]
        self.komut("time_ff", 1)
        self.assertEqual(self.ps["countTimePacket"], [0, 0])
        self.assertEqual(self.ps["timestampLastBonus"], simdi - 10 - 3600)
        self.assertEqual((self.ps["riderTimeStamp"], self.ps["timeStampTakeCare"]), (-1, 0))
        self.assertEqual(self.ps["barracksQueues"]["q1"]["ts"], simdi + 500 - 3600)
        self.assertEqual(self.ps["attacksSent"][0]["time"], simdi - 60 - 3600)
        self.assertEqual(self.harita["items"][0][4], simdi - 5 - 3600)
        self.assertEqual(self.harita["items"][1][4], 0)
        self.assertEqual(self.ps["shield_until"], simdi + 999)  # kalkan ilerlemez (oyunun metninde yok)

    def test_yarim_saatlik_paket(self):
        self.ps["countTimePacket"] = [1]
        simdi = self.komutlar.timestamp_now()
        self.ps["timestampLastBonus"] = simdi
        self.komut("time_ff", 0)
        self.assertEqual(self.ps["timestampLastBonus"], simdi - 1800)

    def test_elde_paket_yoksa_zaman_ilerlemez(self):
        simdi = self.komutlar.timestamp_now()
        self.ps["countTimePacket"] = [0, 0, 0]
        self.ps["timestampLastBonus"] = simdi
        self.komut("time_ff", 2)
        self.komut("time_ff", 9)
        self.assertEqual(self.ps["timestampLastBonus"], simdi)
        self.assertEqual(self.ps["countTimePacket"], [0, 0, 0])


class AskerToplama(KomutTesti):
    """PopupRecruitment/onOpenBuilding: [x, y, kasaba, 387, ödül]. Ödül game_config recruitment_prices
    (config/patch/1-mega_patch.json): id 4 = units "569,569", num_recruitments 2; id 1 = "556", 1. Birimler
    storeItem(..., false, false, false) ile komutsuz depoya (@213); attrs.si = si.slice(0, min(len, 4) - num)
    (@250-318); ödül recruitmentPrices'a (@340). Bedel yok."""

    def bina(self, si):
        self.harita["items"].append([387, 30, 31, 0, 0, 0, [], {"si": list(si)}])
        return self.harita["items"][-1][7]

    def test_iki_birimlik_odul(self):
        oz = self.bina(["a", "b", "c", "d"])
        self.ps["gifts"] = []
        self.komut("finish_si_recruitment", 30, 31, 0, 387, 4)
        self.assertEqual(self.ps["gifts"][569], 2)
        self.assertEqual(sum(self.ps["gifts"]), 2)
        self.assertEqual(oz["si"], ["a", "b"])
        self.assertEqual(self.ps["recruitmentPrices"], [4])
        self.assertEqual(self.cash, 100)

    def test_dortten_fazla_yardim_kirpilir(self):
        oz = self.bina(["a", "b", "c", "d", "e", "f"])
        self.komut("finish_si_recruitment", 30, 31, 0, 387, 1)
        self.assertEqual(oz["si"], ["a", "b", "c"])  # min(6, 4) - 1 = 3

    def test_alinmis_ya_da_olmayan_odul(self):
        self.bina(["a"])
        self.ps["gifts"] = []
        self.ps["recruitmentPrices"] = [1]
        self.komut("finish_si_recruitment", 30, 31, 0, 387, 1)
        self.komut("finish_si_recruitment", 30, 31, 0, 387, 99)
        self.assertEqual(self.ps["gifts"], [])
        self.assertEqual(self.ps["recruitmentPrices"], [1])


if __name__ == "__main__":
    unittest.main()
