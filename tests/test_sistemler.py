"""Komut dışı sistemler: dünya, turnuva, ada, kayıt, çeviri, zaman, SWF yaması.

Çalıştırma: python tests/test_sistemler.py
"""

import json
import os
import shutil
import tempfile
import time
import unittest
import unittest.mock

from ortak import KOK, bos_kayit


class SahteKayitlar:
    """Bir modülün all_saves_userid/session/save_session'ını geçici değiştirir."""

    def __init__(self, modul, kayitlar):
        self.modul, self.kayitlar = modul, kayitlar

    def __enter__(self):
        self.eski = {ad: getattr(self.modul, ad) for ad in ("all_saves_userid", "session", "save_session")
                     if hasattr(self.modul, ad)}
        self.modul.all_saves_userid = lambda: list(self.kayitlar)
        self.modul.session = self.kayitlar.get
        if "save_session" in self.eski:
            self.modul.save_session = lambda uid: None
        return self

    def __exit__(self, *_):
        for ad, deger in self.eski.items():
            setattr(self.modul, ad, deger)


def botlar(adet, oyuncu=True):
    kayitlar = {}
    for i in range(adet):
        k = bos_kayit(f"b{i}")
        k["playerInfo"].update(name=f"Bot {i}", bot=True)
        k["maps"][0]["level"] = 10 + i
        kayitlar[f"b{i}"] = k
    if oyuncu:
        kayitlar["u1"] = bos_kayit("u1")
    return kayitlar


class DunyaTestleri(unittest.TestCase):
    def test_birim_sayilari_ve_guc(self):
        from oyun import dunya
        kayit = bos_kayit()
        kayit["maps"][0]["items"].append([512, 30, 30, 0, 0, 0, [], {}])
        self.assertEqual(dunya.birim_sayilari(kayit).get(512), 1)
        self.assertGreater(dunya.ordu_gucu({512: 2}), 0)

    def test_tick_ekonomiyi_ilerletir(self):
        from oyun import dunya
        kayitlar = botlar(1, oyuncu=False)
        with SahteKayitlar(dunya, kayitlar):
            d = dunya.Dunya()
            d.ayar["saldiri_olasiligi"] = 0
            once = kayitlar["b0"]["maps"][0]["wood"]
            d.tek_tick()
            self.assertGreater(kayitlar["b0"]["maps"][0]["wood"], once)

    def test_ittifak_kararli_ve_olay_biter(self):
        from oyun.dunya import Dunya
        d = Dunya()
        self.assertEqual(d._ittifak("abc"), d._ittifak("abc"))
        d.aktif_olay = {"tur": "savas", "metin": "test", "bitis": int(time.time()) - 1}
        d._olay_guncelle(int(time.time()))
        self.assertIsNone(d.aktif_olay)


class IttifakSeferTestleri(unittest.TestCase):
    """Bot ittifakları ve intikam seferleri (OYN-01)."""

    def kur(self, adet=4):
        from oyun import dunya
        kayitlar = botlar(adet)
        for i in range(adet):
            k = kayitlar[f"b{i}"]
            k["maps"][0]["items"] += [[512, 5 + j, 5, 0, 0, 0] for j in range(6)]
            # b0, b1 Kızıl; b2 Mavi; b3 Yeşil
            k.setdefault("privateState", {})["bot_hafiza"] = {"ittifak": [0, 0, 1, 2][i]}
        kayitlar["u1"]["maps"][0]["level"] = 12
        kayitlar["u1"]["maps"][0]["items"] += [[512, 9, 9, 0, 0, 0]]
        d = dunya.Dunya()
        d.ayar.update(saldiri_olasiligi=0, intikam_olasiligi=1.0, oyuncuya_intikam=1.0)
        return dunya, kayitlar, d

    def test_ittifak_kayittan_okunur_ve_adi_turkce(self):
        dunya, kayitlar, d = self.kur()
        with SahteKayitlar(dunya, kayitlar):
            self.assertEqual(d.ittifak_adi("b2"), "Mavi Birlik")
            self.assertEqual(d._ittifak("b0"), d._ittifak("b1"))

    def test_kalabalik_ittifaktan_kucuge_gecis_haber_olur(self):
        dunya, kayitlar, d = self.kur()
        with SahteKayitlar(dunya, kayitlar):
            d.tick = dunya.ITTIFAK_DEGISIMI
            with unittest.mock.patch.object(dunya.random, "random", return_value=0.0):
                degisen = d._ittifak_degisimi()
            (uid,) = degisen
            self.assertIn(uid, ("b0", "b1"))
            self.assertNotEqual(d._ittifak(uid), 0)
            self.assertIn("katıldı", d.olaylar[-1]["metin"])
            self.assertEqual(d.olaylar[-1]["tur"], "ittifak")

    def test_intikam_seferi_ilan_edilir_ve_yurutulur(self):
        dunya, kayitlar, d = self.kur()
        with SahteKayitlar(dunya, kayitlar):
            sefer = d._sefer_ilan(0, "b2", "Bot 2", "Bot 1")
            self.assertIn("intikam seferi ilan etti", d.olaylar[-1]["metin"])
            self.assertIsNone(d._sefer_ilan(0, "b2", "Bot 2", "Bot 1"))  # aynı sefer iki kez açılmaz
            simdi = int(time.time())
            degisen = d._seferleri_yurut(d._botlar(), simdi)
            self.assertEqual(sefer["kalan"], dunya.SEFER_SALDIRI - 1)
            self.assertIn("b2", degisen)
            self.assertTrue(degisen & {"b0", "b1"})  # saldıran Kızıl Birlik üyesi
            self.assertTrue(any(o["tur"] == "savas" and "Bot 2" in o["metin"] for o in d.olaylar))

    def test_sefer_suresi_dolunca_dagilir(self):
        dunya, kayitlar, d = self.kur()
        with SahteKayitlar(dunya, kayitlar):
            d._sefer_ilan(0, "b2", "Bot 2", "Bot 1")
            d.tick += dunya.SEFER_SURESI + 1
            d._seferleri_yurut(d._botlar(), int(time.time()))
            self.assertEqual(d.seferler, [])
            self.assertIn("dağıldı", d.olaylar[-1]["metin"])

    def test_yenilen_botun_ittifaki_intikam_ilan_eder(self):
        dunya, kayitlar, d = self.kur()
        with SahteKayitlar(dunya, kayitlar):
            kayitlar["b2"]["maps"][0]["items"] = [it for it in kayitlar["b2"]["maps"][0]["items"] if it[0] != 512]
            d._akin("b0", kayitlar["b0"], d._botlar(), int(time.time()), zorla=("b2", kayitlar["b2"]))
            self.assertTrue(d._son_sonuc["kazandi"])
            self.assertEqual([(s["ittifak"], s["hedef"]) for s in d.seferler], [(1, "b0")])

    def test_oyuncu_saldirinca_sefer_ve_kalkana_saygi(self):
        dunya, kayitlar, d = self.kur()
        with SahteKayitlar(dunya, kayitlar):
            sefer = d.oyuncu_saldirdi("u1", "Oyuncu", "b2", kayitlar["b2"])
            self.assertTrue(sefer["oyuncu"])
            self.assertIn("senin köyüne", d.olaylar[-1]["metin"])
            kayitlar["u1"]["privateState"]["shield_until"] = int(time.time()) + 3600
            d._seferleri_yurut(d._botlar(), int(time.time()))
            self.assertEqual(sefer["kalan"], dunya.SEFER_SALDIRI)  # kalkanlıya akın yok
            self.assertIsNone(d.oyuncu_saldirdi("u1", "Oyuncu", "u1", kayitlar["u1"]))  # bot değilse yok


class TurnuvaAdaTestleri(unittest.TestCase):
    def _turnuva(self, kayitlar):
        from oyun import turnuva
        turnuva.sifirla()
        for k in kayitlar.values():  # botların savaşçı birimleri
            k["maps"][0]["items"] += [[512, 1, 1, 0, 0, 0], [516, 2, 2, 0, 0, 0]]
        return turnuva

    def test_turnuva_dort_oyuncu_ve_mac_listeleri(self):
        from oyun import turnuva
        kayitlar = botlar(6)
        with SahteKayitlar(turnuva, kayitlar):
            self._turnuva(kayitlar)
            veri = turnuva.katil("u1", 1, [512] + [0] * 19)
            t = veri["tournament"]
            self.assertEqual(len(t["players"]), 4)
            self.assertTrue(all(len(o["matches"]) == 3 for o in t["players"]))
            self.assertTrue(all(len(o["team"]) == 20 for o in t["players"]))
            self.assertIsNotNone(t["date_ready"])
            for alan in ("tournament_friends", "tournament_reward_id", "tournament_weekly"):
                self.assertIn(alan, veri)
            # botların maçları hemen biter, oyuncununkiler bekler
            botlarin = [m for o in t["players"][1:] for m in o["matches"]]
            self.assertTrue(all(m["finished"] for m in botlarin))
            self.assertFalse(any(m["finished"] for m in t["players"][0]["matches"]))

    def test_turnuvadan_ayrilinca_silinir(self):
        from oyun import turnuva
        kayitlar = botlar(6)
        with SahteKayitlar(turnuva, kayitlar):
            self._turnuva(kayitlar)
            turnuva.katil("u1", 1, [512] + [0] * 19)
            turnuva.ayril("u1")
            self.assertEqual(turnuva._hepsi(), {})
            self.assertIsNone(turnuva.bilgi("u1")["tournament"])

    def test_turnuva_takimsiz_girilemez(self):
        from oyun import turnuva
        kayitlar = botlar(6)
        with SahteKayitlar(turnuva, kayitlar):
            self._turnuva(kayitlar)
            self.assertEqual(turnuva.katil("u1", 1, [0] * 20), {"result": "NOTEAM"})

    def test_turnuva_kazanana_odul_ve_temizlik(self):
        from oyun import turnuva
        kayitlar = botlar(6)
        with SahteKayitlar(turnuva, kayitlar):
            self._turnuva(kayitlar)
            t = turnuva.katil("u1", 1, [512] + [0] * 19)["tournament"]
            for mac in t["players"][0]["matches"]:
                self.assertEqual(turnuva.mac_baslat("u1", mac["victim_id"]), {"result": "OK"})
                self.assertEqual(turnuva.mac_bitir("u1", mac["victim_id"], True, "100.00"), {"result": "OK"})
            bitmis = turnuva.bilgi("u1")["tournament"]
            self.assertIsNotNone(bitmis["date_finished"])
            self.assertFalse(bitmis["match_playing"])
            # 3 x 100 puanla birinci: NEWBIES ödülü 1500 altın + bir birim
            self.assertEqual(kayitlar["u1"]["maps"][0]["coins"], 51500)
            self.assertEqual(sum(kayitlar["u1"]["privateState"]["gifts"]), 1)
            turnuva.temizle("u1")
            self.assertIsNone(turnuva.bilgi("u1")["tournament"])

    def test_kita_sekiz_yuva_ve_fetih(self):
        from oyun import ada
        kayitlar = botlar(10)
        with SahteKayitlar(ada, kayitlar):
            oyuncu = kayitlar["u1"]
            liste = ada.kita_listesi(oyuncu)
            self.assertEqual([g["posicion"] for g in liste], list(range(8)))
            self.assertEqual(liste[0]["nivel"], 1)
            self.assertTrue(all(g["race"] for g in liste))
            self.assertEqual(liste[7]["user_id"], "u1")
            rakip = liste[2]
            self.assertEqual(ada.fetih_kaydet(oyuncu, {"user_id": rakip["user_id"]}), 2)
            self.assertEqual(oyuncu["maps"][0]["universAttackWin"], [2])
            # yuva değişse de fethedilen rakip aynı yuvada kalır
            oyuncu["privateState"]["kita_konum"] = 5
            self.assertEqual(ada.kita_listesi(oyuncu)[2]["user_id"], rakip["user_id"])

    def test_yedi_fetihle_sonraki_kita(self):
        from oyun import ada
        kayitlar = botlar(10)
        with SahteKayitlar(ada, kayitlar):
            oyuncu = kayitlar["u1"]
            ilk = {g["user_id"] for g in ada.kita_listesi(oyuncu)}
            for g in ada.kita_listesi(oyuncu)[:7]:
                ada.fetih_kaydet(oyuncu, {"user_id": g["user_id"]})
            self.assertTrue(ada.sonraki_kita(oyuncu))
            self.assertEqual(ada.kita_no(oyuncu), 2)
            self.assertEqual(oyuncu["maps"][0]["universAttackWin"], [])
            self.assertNotEqual({g["user_id"] for g in ada.kita_listesi(oyuncu)}, ilk)


class KayitTestleri(unittest.TestCase):
    def setUp(self):
        from oyun import kayit
        self.kayit = kayit
        self.gecici = tempfile.mkdtemp(prefix="se-kayit-")
        self.eski = (kayit.SAVES_DIR, kayit.BACKUP_DIR)
        kayit.SAVES_DIR = self.gecici
        kayit.BACKUP_DIR = os.path.join(self.gecici, "backups")

    def tearDown(self):
        self.kayit.SAVES_DIR, self.kayit.BACKUP_DIR = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def test_eski_kayit_migrate_edilir(self):
        from oyun.surum import migrate_loaded_save
        k = bos_kayit()
        k["version"] = "0.04a"
        del k["privateState"]["marketTimestamp"]
        del k["maps"][0]["resourcesTraded"]
        self.assertTrue(migrate_loaded_save(k))
        self.assertEqual(k["maps"][0]["resourcesTraded"], {})

    def test_bozuk_xp_seviyesi_duzeltilir(self):
        k = bos_kayit()
        k["maps"][0].update(xp=2016089205, level=0)
        self.assertTrue(self.kayit._seviyeyi_duzelt(k))
        self.assertEqual(k["maps"][0]["level"], 99)

    def test_turkce_ad_ve_atomik_kayit(self):
        uid = self.kayit.new_village()
        self.kayit.session(uid)["playerInfo"]["name"] = "Gökbörü"
        self.kayit.save_session(uid)
        yol = os.path.join(self.gecici, f"{uid}.save.json")
        self.assertTrue(os.path.exists(yol + ".bak"))
        self.assertFalse(os.path.exists(yol + ".tmp"))
        self.kayit.load_saved_villages()
        self.assertEqual(self.kayit.session(uid)["playerInfo"]["name"], "Gökbörü")


class CeviriTestleri(unittest.TestCase):
    def test_istemci_config_turkce_asil_config_degismez(self):
        from oyun.config import get_client_game_config, get_game_config
        tr = get_client_game_config("tr")
        sozluk = {e["name"]: e["text"] for e in tr["localization_strings"]}
        self.assertEqual(sozluk.get("AUX_ACEPTAR"), "Kabul et")
        self.assertEqual(tr["levels"][0]["name"], "Köle")
        self.assertEqual(get_game_config()["levels"][0]["name"], "Slave")
        adlar = {i["id"]: i["name"] for i in tr["items"]}
        self.assertEqual(adlar["1"], "Ev I")

    def test_buyu_onur_ve_turnuva_adlari_turkce(self):
        from oyun.config import get_client_game_config, get_game_config
        tr, en = get_client_game_config("tr"), get_game_config()
        for bolum, alan in (("magics", "name"), ("honor_levels", "rank")):
            self.assertTrue(tr[bolum], bolum)
            self.assertNotEqual([m.get(alan) for m in tr[bolum]], [m.get(alan) for m in en[bolum]], bolum)
        self.assertIn("ÇAYLAKLAR", {t.get("name") for t in tr["tournament_type"].values()})

    def test_yerellestirme_kayitlari_nesne(self):
        from oyun.config import get_game_config
        self.assertTrue(all(isinstance(e, dict) for e in get_game_config()["localization_strings"]))

    def test_bos_olmayan_tum_metinler_cevrilmis(self):
        from oyun.config import get_game_config
        from oyun.turkce import _bolum_anahtarlari, cevirileri_yukle
        ceviri = cevirileri_yukle()
        eksik = [k for k, _b, m, _y in _bolum_anahtarlari(get_game_config()) if m.strip() and k not in ceviri]
        self.assertEqual(eksik, [])

    def test_yer_tutucular_korunur(self):
        from oyun.turkce import dogrula
        self.assertEqual(dogrula("Hi #0#, you have #1# gold", "Merhaba #0#, #1# altının var"), [])

    def test_yeni_icerik_yuklendi(self):
        from oyun.config import get_game_config
        adlar = {i["id"]: i["name"] for i in get_game_config()["items"]}
        self.assertEqual(adlar.get("9001"), "Büyük Ev")



class BotKimlikTestleri(unittest.TestCase):
    """Bot adı ve portresi oyundaki bir birimin adı ve resmi; eski tarihî adlı kayıtlar yenilerine geçer."""

    def setUp(self):
        from oyun import bot_kimlik
        self.b = bot_kimlik

    def _bot(self, ad, seviye):
        return {"playerInfo": {"bot": True, "name": ad, "pic": "/img/profile/bot_eski.jpg",
                               "map_names": [f"{ad} Kalesi"]}, "maps": [{"level": seviye}], "privateState": {}}

    def test_elli_ayri_ad_gercek_kisi_yok(self):
        self.assertEqual(len(set(self.b.ISIMLER)), 50)
        self.assertEqual(len(self.b.ESKI_ISIMLER), 50)
        self.assertFalse(set(self.b.ESKI_ISIMLER) & set(self.b.ISIMLER))

    def test_ad_ve_resim_oyunun_kendi_birimi_temel_pakette(self):
        from oyun.config import get_client_game_config
        birimler = {i["id"]: (i["name"], i["img_name"]) for i in get_client_game_config("tr")["items"]}
        temel = set()
        with open(os.path.join(KOK, "config", "onindirme.tsv"), encoding="utf-8") as f:
            for satir in f:
                p = satir.rstrip("\n").split("\t")
                if len(p) >= 3 and not satir.startswith("#") and int(p[2]) <= 1:
                    temel.add(p[0])
        for ad, resim, kimlik in self.b.BOTLAR:
            self.assertEqual(birimler[kimlik], (ad, resim))  # oyundaki adı neyse o (ör. Thor)
            self.assertIn(f"buildingthumbs/{resim}.jpg", temel)
        self.assertIn("Thor", self.b.ISIMLER)

    def test_guclu_bota_guclu_birim(self):
        from oyun.config import get_client_game_config
        guc = {i["id"]: int(i.get("life") or 0) * int(i.get("attack") or 0)
               for i in get_client_game_config("tr")["items"]}
        sira = [guc[kimlik] for _, _, kimlik in self.b.BOTLAR]
        self.assertEqual(sira, sorted(sira))
        self.assertEqual(self.b.portre("Bilinmeyen"), self.b.VARSAYILAN_PORTRE)

    def test_eski_adli_bot_ve_raporlar_yenilenir(self):
        oyuncu = {"playerInfo": {"name": "Attila"}, "maps": [{"level": 5}], "privateState": {"attacksSent": [
            {"description": {"oponent": {"name": "Cengiz Han", "level": 31,
                                         "pic": "/img/profile/bot_cengiz_han.jpg"}}}]}}
        kayitlar = {"b": self._bot("Kara Han", 40), "o": oyuncu}
        self.assertEqual(self.b.adlari_yenile(kayitlar), {"b", "o"})
        pi = kayitlar["b"]["playerInfo"]
        self.assertEqual((pi["name"], pi["map_names"]), ("Hafif Okçu", ["Hafif Okçu Kalesi"]))
        self.assertEqual(pi["pic"], self.b.portre("Hafif Okçu"))
        rakip = oyuncu["privateState"]["attacksSent"][0]["description"]["oponent"]
        yeni = self.b.ISIMLER[self.b.ESKI_ISIMLER.index("Cengiz Han")]
        self.assertEqual((rakip["name"], rakip["pic"]), (yeni, self.b.portre(yeni)))
        self.assertEqual(oyuncu["playerInfo"]["name"], "Attila")  # bot olmayan kayıt adı değişmez
        self.assertEqual(self.b.adlari_yenile(kayitlar), set())  # ikinci açılışta yazacak bir şey yok

    def test_diyar_portresi_birim_resmini_kabul_eder(self):
        from oyun.diyar import portre
        resim = self.b.portre("Thor")
        self.assertEqual(portre({"playerInfo": {"pic": resim}}), resim)
        self.assertEqual(portre({"playerInfo": {"pic": "https://ornek.com/x.jpg"}}), self.b.VARSAYILAN_PORTRE)


class ZamanOlcegiTestleri(unittest.TestCase):
    def test_istemci_config_sureleri_bolunur(self):
        from oyun.config import get_client_game_config, get_game_config
        os.environ["TIME_SCALE"] = "2"
        try:
            ham = next(i for i in get_game_config()["items"] if i["id"] == "5")
            istemci = next(i for i in get_client_game_config()["items"] if i["id"] == "5")
            self.assertAlmostEqual(float(ham["activation"]), 21600)
            self.assertAlmostEqual(float(istemci["activation"]), 10800)
        finally:
            os.environ.pop("TIME_SCALE", None)


class SwfYamaTestleri(unittest.TestCase):
    """swf_font: depodaki Türkçe yazı tiplerinden yapay bir eksik yazı tipi üretip tamamlar."""

    def _font(self):
        from oyun import swf_font, swf_yama
        with open(os.path.join(KOK, "assets", "fonts", "tr_ErasBold.swf"), "rb") as f:
            govde = swf_yama._govde(f.read())
        for kod, bas, son, _ in swf_yama._etiketler(govde):
            if kod == swf_font.DEFINE_FONT3:
                return swf_font.Font3(govde[bas:son])

    def test_font_yaz_oku_ayni(self):
        from oyun import swf_font
        font = self._font()
        tekrar = swf_font.Font3(font.yaz())
        self.assertEqual(tekrar.kodlar, font.kodlar)
        self.assertEqual(tekrar.sekiller, font.sekiller)

    def test_eksik_turkce_harfler_eklenir(self):
        from oyun import swf_font
        kaynak = self._font()
        hedef = self._font()
        silinecek = [hedef.kodlar.index(ord(h)) for h in "ğİş"]
        for i in sorted(silinecek, reverse=True):
            del hedef.kodlar[i], hedef.sekiller[i], hedef.duzen[1][i], hedef.duzen[2][i]
        eslem, _ = swf_font.harf_ekle(hedef, kaynak)
        self.assertEqual(hedef.kodlar, sorted(hedef.kodlar))
        for h in "ğİş":
            self.assertIn(ord(h), hedef.kodlar)
        # Eski glifler doğru yeni numaraya eşlenir
        eski_a = [k for k in kaynak.kodlar if k not in (ord("ğ"), ord("İ"), ord("ş"))].index(ord("a"))
        self.assertEqual(hedef.kodlar[eslem[eski_a]], ord("a"))

    def test_glif_numarasi_buyuyunce_bit_genisligi_artar(self):
        from oyun import swf_font
        kayitlar = [{"bayrak": 0x88, "font": 7, "renk": None, "x": None, "y": None,
                     "yukseklik": 240, "glifler": [(126, 100), (127, 90)]}]
        once = swf_font.metin_yaz(b"\x01\x00\x00", kayitlar)
        sonra = swf_font.metin_yaz(b"\x01\x00\x00", swf_font.glifleri_esle(kayitlar, {7: {127: 130}}))
        self.assertEqual(once[3], 7)   # 7 bit yeterliydi
        self.assertEqual(sonra[3], 8)  # 130 için 8 bit

    def test_arayuz_sozlugu_gecerli(self):
        with open(os.path.join(KOK, "ceviri", "arayuz_tr.json"), encoding="utf-8") as f:
            sozluk = json.load(f)
        self.assertGreater(len(sozluk["metin_alanlari"]), 300)
        for anahtar, ceviri in sozluk["statik_yazilar"].items():
            self.assertEqual(anahtar.count("|"), ceviri.count("|"), anahtar)


if __name__ == "__main__":
    unittest.main(verbosity=2)
