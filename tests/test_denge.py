"""Denge kuralları: PvP saldırı hakkı ve ganimet sınırları, bot dünyası, yeni oyuncu kalkanı, turnuva, Elo (TST-04).

Beklenen değerler kodun kendi çıktısı değildir; her birinin kaynağı yanında yazılıdır:
- 1.4.07 istemcisinin bayt kodu (SocialEmpires1.4.07sec_fixed.swf, araclar/abc_okur.py ile okundu; SWF depoda yok,
  değerler buraya yazıldı). Config sabitleri: ATTACKS_MAX = 3, ATTACKS_PERIOD_HOURS = 6,
  ATTACKS_SAME_PLAYER_HOURS = 4, MAX_GOLD_FROM_ASSAULT = 200.
- config/game_config_20120826.json (globals, tournament_type).
- Değişmezler (kaynak korunur, kurban eksiye düşmez...).
Kaynağı olmayan denge değerleri (denge.GANIMET_ORANI, GANIMET_TAVANI, YENI_OYUNCU_KALKANI'nın süresi, Elo'nun K'si...)
burada sabitlenmez; sahibinin kararını bekler (BULGULAR TST-04).

Çalıştırma: python tests/test_denge.py
"""

import contextlib
import json
import os
import unittest
import unittest.mock
from datetime import datetime

from ortak import KomutTesti, bos_kayit
from test_sistemler import SahteKayitlar, botlar

SIMDI = 1_800_000_000
SAAT = 3600


# ---------------------------------------------------------------------------
# PvP: saldırı hakkı (istemci Base/processAttacks)
# ---------------------------------------------------------------------------

class SaldiriHakkiTestleri(unittest.TestCase):
    """pvp.saldiri_hakki_var = istemcinin Base/processAttacks hesabı.

    processAttacks@435-468: şimdi - son saldırı >= ATTACKS_PERIOD_HOURS (6) * 3600 ise sayaç sıfırdır.
    @532-579: sayılan saldırı (son - t) < 6 * 3600 ve t > privateState.tsAttacksReset olandır.
    @635-656: kalan hak = max(0, ATTACKS_MAX (3) - sayı); @663-694: attacksPack > 0 ise hak paketten gelir.
    """

    def hak(self, zamanlar, **ps):
        from oyun import pvp
        ps["attacksSent"] = [{"time": t, "victim_id": f"k{i}"} for i, t in enumerate(zamanlar)]
        return pvp.saldiri_hakki_var({"privateState": ps}, SIMDI)

    def test_alti_saatte_uc_saldiri(self):
        self.assertTrue(self.hak([]))
        self.assertTrue(self.hak([SIMDI - 60, SIMDI - 120]))
        self.assertFalse(self.hak([SIMDI - 60, SIMDI - 120, SIMDI - 180]))
        self.assertFalse(self.hak([SIMDI - 60, SIMDI - 120, SIMDI - 180, SIMDI - 240]))

    def test_son_saldiridan_alti_saat_sonra_sayac_sifirlanir(self):
        # şimdi - son = 6 * 3600: "< 6 saat" değil, sayılmaz (@468 ifnlt)
        self.assertTrue(self.hak([SIMDI - 6 * SAAT] * 3))
        self.assertFalse(self.hak([SIMDI - 6 * SAAT + 1] * 3))

    def test_pencere_son_saldiriya_gore(self):
        son = SIMDI - SAAT
        # son - t = 6 saat sayılmaz, 6 saat - 1 sn sayılır: 2 saldırı, hak var
        self.assertTrue(self.hak([son, son - 6 * SAAT, son - 6 * SAAT + 1]))
        self.assertFalse(self.hak([son, son - 10, son - 6 * SAAT, son - 6 * SAAT + 1]))

    def test_sifirlama_damgasindan_oncekiler_sayilmaz(self):
        zamanlar = [SIMDI - 60, SIMDI - 120, SIMDI - 180]
        # t > tsAttacksReset (@571-579): damgaya eşit olan sayılmaz
        self.assertTrue(self.hak(zamanlar, tsAttacksReset=SIMDI - 180))
        self.assertFalse(self.hak(zamanlar, tsAttacksReset=SIMDI - 181))

    def test_saldiri_paketi_hakki_acar(self):
        self.assertTrue(self.hak([SIMDI - 60, SIMDI - 120, SIMDI - 180], attacksPack=1))


# ---------------------------------------------------------------------------
# PvP: end_attack sonuçları
# ---------------------------------------------------------------------------

class PvpSonucTestleri(KomutTesti):
    """end_attack: ganimet ve savunma ödülü istemcinin Assault$/killed sınırlarıyla."""

    def setUp(self):
        super().setUp()
        self.kurban = bos_kayit("rakip")
        self.kurban["maps"][0]["level"] = 5
        self.kayitlar["rakip"] = self.kurban
        yama = unittest.mock.patch.object(self.pvp, "timestamp_now", return_value=SIMDI)
        yama.start()
        self.addCleanup(yama.stop)

    def saldir(self, gecmis=(), **ek):
        """Temiz bir başlangıçtan saldırır; saldıranın kazandığı altını döndürür."""
        self.ps["attacksSent"] = [dict(a) for a in gecmis]
        self.harita["coins"] = 50000
        veri = {"attacker": {"user_id": "test", "map": 0}, "victim": {"user_id": "rakip", "level": 5},
                "resources": {"g": 500, "x": 0}, "resources_victim": {"g": 0},
                "attacker_units": [[512, 4, 0, 0]], "victim_units": [[512, 3, 2, 0]],
                "win": 1, "duration": 30, "voluntary_end": 0, "townhall_gold": 500, "honor": 0}
        veri.update(ek)
        self.komut("end_attack", json.dumps(veri))
        return self.harita["coins"] - 50000

    def test_ayni_hedefe_dort_saat(self):
        # Base/processAttacks@278-329: şimdi - t < 3600 * ATTACKS_SAME_PLAYER_HOURS (4) ise hedef "zaten saldırıldı"
        self.assertEqual(self.saldir([{"time": SIMDI - 4 * SAAT + 1, "victim_id": "rakip"}]), 0)
        self.assertEqual(self.saldir([{"time": SIMDI - 4 * SAAT, "victim_id": "rakip"}]), 500)
        self.assertEqual(self.saldir([{"time": SIMDI - 60, "victim_id": "baska"}]), 500)

    def test_hak_bitince_ganimet_yok(self):
        uc = [{"time": SIMDI - 60 * i, "victim_id": f"k{i}"} for i in (1, 2, 3)]
        self.assertEqual(self.saldir(uc), 0)
        self.assertEqual(self.saldir(uc[:2]), 500)

    def test_ganimet_tavani_birim_ve_seviye_basina(self):
        # Assault$/killed@146-175: yıkılan her birimden en çok Config.MAX_GOLD_FROM_ASSAULT (200) altın;
        # @84-103: belediye binası kurbanın seviyesi * 100 altın. Fark alınır ki sabit pay (25) karışmasın.
        sinirsiz = {"resources": {"g": 999999, "x": 0}}
        iki = self.saldir(victim_units=[[512, 3, 2, 0]], **sinirsiz)
        self.assertEqual(self.saldir(victim_units=[[512, 4, 3, 0]], **sinirsiz) - iki, 200)
        # aynı birimin iki satırı toplanır (değişmez): 2 + 2 yıkılan
        self.assertEqual(self.saldir(victim_units=[[512, 3, 2, 0], [512, 3, 2, 0]], **sinirsiz) - iki, 400)
        self.kurban["maps"][0]["level"] = 6
        self.assertEqual(self.saldir(victim_units=[[512, 3, 2, 0]], **sinirsiz) - iki, 100)

    def test_ganimet_saldiri_basina_tavan(self):
        # game_config globals MAX_GOLD_ASSAULT = 20000; istemci Assault$/killed@625-660 iGoldGained'i buna keser
        self.assertEqual(self.saldir(victim_units=[[512, 250, 200, 0]], resources={"g": 999999, "x": 0}), 20000)

    def test_savunma_odulu_olen_birim_basina(self):
        # Assault$/killed@410-435: kurban her ölen saldıran birim için ceil(0,1 * birimin altını) alır;
        # birimin altını en çok MAX_GOLD_FROM_ASSAULT (200) → birim başına en çok 20.
        harita = self.kurban["maps"][0]
        for gelen, beklenen in ((9999, 3 * 20), (45, 45)):
            harita["coins"] = 50000
            self.saldir(win=0, resources={"g": 0, "x": 0}, attacker_units=[[512, 5, 3, 0]],
                        resources_victim={"g": gelen})
            self.assertEqual(harita["coins"] - 50000, beklenen)


class YeniOyuncuKalkaniTestleri(KomutTesti):
    """Yeni köy kalkanla başlar (KYT-03: new_village shield_until = şimdi + YENI_OYUNCU_KALKANI).

    Kalkanın süresi (24 saat) istemcide ya da config'te yok, sahibinin kararını bekler: burada sabitlenmez.
    """

    def test_yeni_koye_saldiri_ganimetsiz(self):
        from oyun import kayit
        from oyun.ekonomi import timestamp_now
        uid = kayit.new_village()
        yeni = kayit.session(uid)
        self.assertGreater(int(yeni["privateState"]["shield_until"]), timestamp_now())
        self.kayitlar["yeni"] = yeni
        veri = {"attacker": {"user_id": "test", "map": 0}, "victim": {"user_id": "yeni", "level": 1},
                "resources": {"g": 500, "x": 0}, "resources_victim": {"g": 0},
                "attacker_units": [], "victim_units": [], "win": 1, "honor": 0}
        self.komut("end_attack", json.dumps(veri))
        self.assertEqual(self.harita["coins"], 50000)
        self.assertNotIn("attacksReceived", yeni["privateState"])


# ---------------------------------------------------------------------------
# Bot dünyası: denge.SALDIRI_HAKKI / SALDIRI_PERIYODU ve ganimet
# ---------------------------------------------------------------------------

class BotDunyasiDengeTestleri(unittest.TestCase):
    def test_bot_alti_saatte_uc_akin(self):
        # Dunya._saldiri_hakki "orijinal oyunun kuralı": game_config globals ATTACKS_PERIOD_MAX = 3,
        # ATTACKS_PERIOD_HOURS = 6 (istemci Config.ATTACKS_MAX / ATTACKS_PERIOD_HOURS ile aynı)
        from oyun import dunya
        d = dunya.Dunya()

        def hak(zamanlar):
            return d._saldiri_hakki({"privateState": {"attacksSent": [{"time": t} for t in zamanlar]}}, SIMDI)

        self.assertTrue(hak([SIMDI - 60, SIMDI - 120]))
        self.assertFalse(hak([SIMDI - 60, SIMDI - 120, SIMDI - 180]))
        self.assertTrue(hak([SIMDI - 6 * SAAT] * 3))
        self.assertFalse(hak([SIMDI - 6 * SAAT + 1] * 3))

    def test_akin_ganimeti_kurbandan_saldirana_gecer(self):
        # Değişmezler: kaynak korunur (kurbanın kaybı = saldıranın kazancı), kazanılan akında ganimet alınır,
        # akın kurbanın kaynağını bitirmez (denge.py: "kurbanın kaynağının en fazla %10'u"; tam oran ve tavan
        # sahibinin kararı, burada sabitlenmez).
        from oyun import dunya
        kayitlar = botlar(2, oyuncu=False)
        saldiran, hedef = kayitlar["b0"], kayitlar["b1"]
        saldiran["maps"][0]["items"] += [[512, 5 + j, 5, 0, 0, 0] for j in range(6)]
        saldiran["privateState"]["bot_hafiza"] = {"ittifak": 0}
        hedef["privateState"]["bot_hafiza"] = {"ittifak": 1}
        once = {a: (saldiran["maps"][0][a], hedef["maps"][0][a]) for a in ("coins", "wood", "stone", "food")}
        with SahteKayitlar(dunya, kayitlar):
            d = dunya.Dunya()
            d.ayar.update(intikam_olasiligi=0)
            d._akin("b0", saldiran, d._botlar(), SIMDI, zorla=("b1", hedef))
        self.assertTrue(d._son_sonuc["kazandi"])  # savunmasız hedef: kurulum doğru mu
        for alan, (s0, h0) in once.items():
            alinan = h0 - hedef["maps"][0][alan]
            with self.subTest(alan=alan):
                self.assertEqual(saldiran["maps"][0][alan] - s0, alinan)
                self.assertGreater(alinan, 0)
                self.assertLess(alinan, h0)


# ---------------------------------------------------------------------------
# Turnuva (istemci TournamentManager / TournamentPlayerData)
# ---------------------------------------------------------------------------

class TurnuvaKuralTestleri(unittest.TestCase):
    """Kaynaklar:
    - TournamentManager$/get currentUserTournamentWinner: adaylar terk etmemiş oyuncular, sortOn(["score", "time"],
      [NUMERIC | DESCENDING, NUMERIC]): en yüksek puan, eşitlikte en kısa süre.
    - TournamentPlayerData/<kurucu>: score = biten maçların attacker_points toplamı, time = (date_finished -
      date_started) toplamı; hasAbandoned = parseInt(abandonned) == 1.
    - TournamentManager$/getRewardData: ödül tournament_type[id].prize[reward_id] ({g, c, u}).
    - TournamentIA/end@421-450: maç puanı [0, 100]'e kırpılır; shutMatch: toFixed(2).
    - PopupTournamentResults/<kurucu>@539-571: bitiş = date_ready + duration * 3600.
    - game_config tournament_type: 1 NEWBIES duration 24; 2 ADVANCED prize[3] = {c: 30, u: {861: 1}}.
    """

    def setUp(self):
        self.hazirla()

    def hazirla(self):
        """Temiz turnuva durumu, 6 bot ve oyuncu u1; saat self.saat'ten okunur."""
        from oyun import turnuva
        self.t = turnuva
        dosya = turnuva._dosya()
        # ortak.py kayıtları geçici klasöre yönlendirir; gerçek saves/turnuvalar.json'a asla dokunulmaz
        self.assertTrue(dosya.startswith(os.environ["SE_KAYIT_DIZINI"]), dosya)
        with contextlib.suppress(FileNotFoundError):  # önceki testlerin turnuvaları karışmasın
            os.remove(dosya)
        turnuva.sifirla()
        self.addCleanup(turnuva.sifirla)
        self.kayitlar = botlar(6)
        for k in self.kayitlar.values():
            k["maps"][0]["items"] += [[512, 1, 1, 0, 0, 0], [516, 2, 2, 0, 0, 0]]
        self.saat = SIMDI
        yigin = contextlib.ExitStack()
        self.addCleanup(yigin.close)
        yigin.enter_context(SahteKayitlar(turnuva, self.kayitlar))
        yigin.enter_context(unittest.mock.patch.object(turnuva, "timestamp_now", lambda: self.saat))

    @property
    def u1(self):
        return self.kayitlar["u1"]

    def kur(self, tur_id=1, bot_puanlari=(10, 10, 10)):
        """Turnuvayı kurar; botların maçlarını sabit puan ve 100 sn süreyle bitirir."""
        self.t.katil("u1", tur_id, [512] + [0] * 19)
        turnuva = self.t._kullanicinin("u1")
        for o in turnuva["players"][1:]:
            for mac, puan in zip(o["matches"], bot_puanlari):
                mac.update(finished=True, attacker_won=True, attacker_points=puan,
                           date_started=SIMDI - 100, date_finished=SIMDI)
        return turnuva

    def oyna(self, kurban_id, puan, sure):
        self.assertEqual(self.t.mac_baslat("u1", kurban_id), {"result": "OK"})
        self.saat += sure
        self.assertEqual(self.t.mac_bitir("u1", kurban_id, True, puan), {"result": "OK"})

    def test_kazanan_puan_sonra_sure(self):
        # (oyuncu puanları, maç süresi, kazanan oyuncu mu); rakip bot: 100 + 100 + 50 = 250 puan, 300 sn
        durumlar = [(("100.00", "100.00", "50.00"), 50, True),     # eşit puan, 150 sn < 300 sn
                    (("100.00", "100.00", "50.00"), 200, False),   # eşit puan, 600 sn > 300 sn
                    (("100.00", "100.00", "51.00"), 200, True)]    # puan süreden önce gelir
        for puanlar, sure, oyuncu_kazanir in durumlar:
            with self.subTest(puanlar=puanlar, sure=sure):
                self.hazirla()
                turnuva = self.kur(tur_id=2)
                rakip = turnuva["players"][1]
                for mac in rakip["matches"]:
                    mac["attacker_points"] = 100
                rakip["matches"][2]["attacker_points"] = 50
                turnuva["reward_id"] = 3
                cash, coins = self.u1["playerInfo"]["cash"], self.u1["maps"][0]["coins"]
                for mac, puan in zip(turnuva["players"][0]["matches"], puanlar):
                    self.oyna(mac["victim_id"], puan, sure)
                self.assertIsNotNone(turnuva["date_finished"])
                if oyuncu_kazanir:
                    self.assertEqual(turnuva["winner_id"], "u1")
                    self.assertEqual(self.u1["playerInfo"]["cash"], cash + 30)
                    self.assertEqual(self.u1["privateState"]["gifts"][861], 1)
                else:
                    self.assertEqual(turnuva["winner_id"], rakip["user_id"])
                    self.assertEqual(self.u1["playerInfo"]["cash"], cash)
                    self.assertEqual(sum(self.u1["privateState"].get("gifts", [])), 0)
                self.assertEqual(self.u1["maps"][0]["coins"], coins)  # ADVANCED ödülünde altın yok

    def test_terk_eden_kazanamaz(self):
        turnuva = self.kur()
        mac1, mac2, _ = turnuva["players"][0]["matches"]
        self.oyna(mac1["victim_id"], "100.00", 60)
        self.oyna(mac2["victim_id"], "100.00", 60)  # 200 puan, botlar 30'da
        coins, cash = self.u1["maps"][0]["coins"], self.u1["playerInfo"]["cash"]
        self.t.ayril("u1")
        bot_idleri = {o["user_id"] for o in turnuva["players"][1:]}
        self.assertIn(turnuva["winner_id"], bot_idleri)
        self.assertEqual((self.u1["maps"][0]["coins"], self.u1["playerInfo"]["cash"]), (coins, cash))

    def test_mac_puani_sifir_ile_yuz_arasi(self):
        turnuva = self.kur()
        maclar = turnuva["players"][0]["matches"]
        for mac, gelen, beklenen in zip(maclar, ("150", "-20", "33.456"), (100.0, 0.0, 33.46)):
            with self.subTest(gelen=gelen):
                self.oyna(mac["victim_id"], gelen, 30)
                self.assertEqual(mac["attacker_points"], beklenen)

    def test_sure_dolunca_biter(self):
        turnuva = self.kur()
        self.oyna(turnuva["players"][0]["matches"][0]["victim_id"], "80.00", 30)
        bitis = SIMDI + 24 * SAAT
        self.saat = bitis - 10
        self.assertIsNone(self.t.bilgi("u1")["tournament"]["date_finished"])
        self.saat = bitis + 10
        self.assertEqual(self.t.bilgi("u1")["tournament"]["date_finished"], bitis + 10)
        self.assertEqual(turnuva["winner_id"], "u1")  # 80 puan, botlar 30'da

    def test_bos_koltuklara_yalniz_botlar(self):
        # KAR-02: tek kişilik sunucu; boş koltuklar bot köyleriyle dolar. Gerçek oyuncu u2, seviyesi en yakın
        # aday olsa da (karıştırma kapalı) turnuvaya bot diye girmez.
        self.kayitlar["u2"] = bos_kayit("u2")
        for i in range(6):
            self.kayitlar[f"b{i}"]["maps"][0]["level"] = 30 + i
        with unittest.mock.patch.object(self.t.random, "shuffle", lambda liste: None):
            turnuva = self.kur()
        idler = [o["user_id"] for o in turnuva["players"]]
        self.assertEqual(idler[0], "u1")
        self.assertNotIn("u2", idler)
        self.assertTrue(all(self.kayitlar[i]["playerInfo"].get("bot") for i in idler[1:]))

    def test_bot_takiminda_yasakli_birim_yok(self):
        # game_config globals TOURNAMENT_UNITS_NOT_ALLOWED: 762 (Stratos Titan) yasak
        for i in range(6):
            self.kayitlar[f"b{i}"]["maps"][0]["items"] = [[19, 20, 20, 0, 0, 0], [762, 3, 3, 0, 0, 0],
                                                         [762, 4, 4, 0, 0, 0], [512, 5, 5, 0, 0, 0]]
        turnuva = self.kur()
        for o in turnuva["players"][1:]:
            self.assertEqual(o["team"], [512] + [0] * 19)

    def test_haftalik_turnuva_listesi(self):
        # game_config tournament_type: weekly_tournaments yalnızca 8 (WEEKLY GOLD) için sıfırdan büyük (7)
        self.assertEqual(set(self.t.bilgi("u1")["tournament_weekly"]), {"8"})

    def test_bot_reytingine_gercek_oyuncu_girmez(self):
        self.assertEqual(set(self.t.bot_reytingleri()), {f"b{i}" for i in range(6)})

    def test_mac_puani_sonuca_yuzde_olarak_cevrilir(self):
        # elo.py: S = puan / 100. Eşit reytingde E = 0,5 (Elo tanımı); S = 0,5 ise reyting değişmez (K ne olursa olsun).
        from oyun import elo, takvim
        self.u1["privateState"]["elo"] = {"puan": elo.BASLANGIC, "mac": 0}
        an = datetime(2026, 11, 3, 12, 0, tzinfo=takvim.TURKIYE)
        self.t._reyting_isle("u1", "yok", 50, an)
        self.assertEqual(self.u1["privateState"]["elo"], {"puan": elo.BASLANGIC, "mac": 1})
        self.t._reyting_isle("u1", "yok", 100, an)
        self.assertGreater(self.u1["privateState"]["elo"]["puan"], elo.BASLANGIC)


# ---------------------------------------------------------------------------
# Haftalık turnuvada botların puanı
# ---------------------------------------------------------------------------

class BotHaftalikPuanTestleri(unittest.TestCase):
    """elo._bot_puani: "reytingine bağlı, haftaya göre sabit" (elo.py). Maç başına puan 0-100 (istemci
    TournamentIA/end); haftada HAFTALIK_MAC maç sayılır."""

    HAFTALAR = [f"2026-{a:02d}-{g:02d}" for a in range(1, 13) for g in (5, 19)]

    def test_hafta_icinde_sabit_haftadan_haftaya_degisir_ve_sinirli(self):
        from oyun import elo
        for reyting in (800.0, 1500.0, 2400.0):
            puanlar = [elo._bot_puani(h, "bot7", reyting) for h in self.HAFTALAR]
            with self.subTest(reyting=reyting):
                self.assertEqual(puanlar, [elo._bot_puani(h, "bot7", reyting) for h in self.HAFTALAR])
                self.assertGreater(len(set(puanlar)), 1)
                self.assertTrue(all(0 <= p <= 100 * elo.HAFTALIK_MAC for p in puanlar))

    def test_guclu_bot_ortalamada_onde(self):
        from oyun import elo

        def ortalama(reyting):
            return sum(elo._bot_puani(h, "bot7", reyting) for h in self.HAFTALAR) / len(self.HAFTALAR)

        self.assertLess(ortalama(900.0), ortalama(1500.0))
        self.assertLess(ortalama(1500.0), ortalama(2200.0))


if __name__ == "__main__":
    unittest.main()
