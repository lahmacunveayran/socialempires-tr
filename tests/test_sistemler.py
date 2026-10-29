"""Komut dışı sistemler: dünya, turnuva, ada, kayıt, çeviri, zaman, SWF yaması.

Çalıştırma: python tests/test_sistemler.py
"""

import json
import os
import shutil
import tempfile
import time
import unittest

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


class TurnuvaAdaTestleri(unittest.TestCase):
    def test_turnuva_dort_oyuncuyla_kurulur(self):
        from oyun import turnuva
        with SahteKayitlar(turnuva, botlar(6)):
            t = turnuva.turnuva_olustur("u1")
            self.assertEqual(len(t["players"]), 4)
            self.assertEqual(len(t["matches"]), 6)

    def test_turnuva_odulu_bir_kez(self):
        from oyun import turnuva
        kayitlar = botlar(7)
        with SahteKayitlar(turnuva, kayitlar):
            t = turnuva.turnuva_olustur("u1")
            for _ in range(3):
                if not turnuva.mac_baslat(t["id"], "u1"):
                    break
                turnuva.mac_bitir(t["id"], "u1", True)
            self.assertEqual(t["state"], "finished")
            turnuva.mac_bitir(t["id"], "u1", True)
            self.assertEqual(kayitlar["u1"]["privateState"]["trophies"], 30)

    def test_ada_yedi_bolge_ve_sonraki_ada(self):
        from oyun import ada
        kayitlar = botlar(8)
        with SahteKayitlar(ada, kayitlar):
            oyuncu = kayitlar["u1"]
            slotlar = ada.ada_slotlari(oyuncu)
            self.assertEqual(len(slotlar), 7)
            for slot in slotlar:
                ada.fetih_kaydet(oyuncu, slot["user_id"])
            self.assertEqual(ada.ada_durumu(oyuncu)["ada"], 100)

    def test_sezon_hafta_bicimi(self):
        from oyun import sezon
        self.assertRegex(sezon._hafta(), r"^\d{4}-W\d{2}$")


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
        self.assertEqual(sozluk.get("AUX_ACEPTAR"), "Kabul Et")
        self.assertEqual(tr["levels"][0]["name"], "Köle")
        self.assertEqual(get_game_config()["levels"][0]["name"], "Slave")
        adlar = {i["id"]: i["name"] for i in tr["items"]}
        self.assertEqual(adlar["1"], "Ev I")

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

    def test_arayuz_sozlugu_gecerli(self):
        with open(os.path.join(KOK, "ceviri", "arayuz_tr.json"), encoding="utf-8") as f:
            sozluk = json.load(f)
        self.assertGreater(len(sozluk["metin_alanlari"]), 300)
        for anahtar, ceviri in sozluk["statik_yazilar"].items():
            self.assertEqual(anahtar.count("|"), ceviri.count("|"), anahtar)


if __name__ == "__main__":
    unittest.main(verbosity=2)
