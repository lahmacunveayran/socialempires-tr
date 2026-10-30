"""AS3 bayt kodu okuyucusu (araclar/abc_okur.py) ve komut imzaları (araclar/komut_imzalari.py).

Okuyucu elle kurulmuş küçük bir ABC ile sınanır: SWF'si olmayan CI'da da çalışır. Gerçek istemcilerin
komut listeleri depoda JSON olarak durur (`docs/inceleme/*-komutlar.json`); kapsama ve imza kapıları
onlara karşı sınanır (GEC-01, `docs/YOL_HARITASI_1407.md` §2.1).
"""

import os
import re
import struct
import sys
import tempfile
import unittest
import zlib

import ortak  # noqa: F401  (yol ve geçici kayıt klasörü)

KOK = ortak.KOK
sys.path.insert(0, os.path.join(KOK, "araclar"))
import abc_okur  # noqa: E402
import komut_imzalari  # noqa: E402

INCELEME = os.path.join(KOK, "docs", "inceleme")


def _u30(n):
    cikti = bytearray()
    while True:
        x, n = n & 0x7F, n >> 7
        cikti.append(x | 0x80 if n else x)
        if not n:
            return bytes(cikti)


def _dize(s):
    b = s.encode("utf-8")
    return _u30(len(b)) + b


DIZELER = ["addCommand", "cmd", "args", "buy", "Base", "Commands", "", "Oyun", "gonder", "Object"]
D = {s: i + 1 for i, s in enumerate(DIZELER)}
# Çok adlılar: QName(paket, ad); sıra 1'den
ADLAR = ["addCommand", "Base", "Commands", "cmd", "args", "Oyun", "gonder", "Object"]
M = {s: i + 1 for i, s in enumerate(ADLAR)}

# gonder(x): Base.Commands.addCommand({cmd: "buy", args: [x, 7, -1]}); arada atlanan anlamsız baytlar
KOD_NESNE = bytes([
    0xD0, 0x30,                    # getlocal_0, pushscope
    0x10, 0x03, 0x00, 0x00,        # jump +3
    0xFF, 0xFF, 0xFF,              # anlamsız (geçersiz işlem kodu): akış izlenince hiç okunmaz
    0x60, M["Base"], 0x66, M["Commands"],
    0x2C, D["cmd"], 0x2C, D["buy"], 0x2C, D["args"],
    0xD1, 0x24, 0x07, 0x24, 0xFF, 0x56, 0x03,   # getlocal_1, pushbyte 7, pushbyte -1, newarray 3
    0x55, 0x02,                    # newobject 2
    0x4F, M["addCommand"], 0x01,   # callpropvoid addCommand 1
    0x47,                          # returnvoid
])

# var o = new Object(); o.cmd = "buy"; o.args = [x]; Base.Commands.addCommand(o)
KOD_YEREL = bytes([
    0xD0, 0x30,
    0x5D, M["Object"], 0x4A, M["Object"], 0x00,   # findpropstrict Object, constructprop Object 0
    0x80, M["Object"], 0xD6,                      # coerce Object, setlocal_2
    0xD2, 0x2C, D["buy"], 0x61, M["cmd"],         # o.cmd = "buy"
    0xD2, 0xD1, 0x56, 0x01, 0x61, M["args"],      # o.args = [x]
    0x60, M["Base"], 0x66, M["Commands"], 0xD2,
    0x4F, M["addCommand"], 0x01,
    0x47,
])


def _govde(yontem, kod):
    return (_u30(yontem) + _u30(4) + _u30(3) + _u30(0) + _u30(1) + _u30(len(kod)) + kod
            + _u30(0) + _u30(0))


def abc_kur():
    b = struct.pack("<HH", 16, 46)
    b += _u30(0) + _u30(0) + _u30(0)                       # int, uint, double
    b += _u30(len(DIZELER) + 1) + b"".join(_dize(s) for s in DIZELER)
    b += _u30(2) + bytes([0x16]) + _u30(D[""])             # bir paket ad alanı
    b += _u30(0)                                           # ad kümeleri
    b += _u30(len(ADLAR) + 1) + b"".join(bytes([0x07]) + _u30(1) + _u30(D[s]) for s in ADLAR)
    yontem = _u30(1) + _u30(0) + _u30(0) + _u30(0) + bytes([0])   # 1 parametre
    b += _u30(4) + yontem * 4
    b += _u30(0)                                           # üst veri
    b += _u30(1)                                           # bir sınıf
    b += _u30(M["Oyun"]) + _u30(0) + bytes([0]) + _u30(0) + _u30(1)
    b += _u30(1) + _u30(M["gonder"]) + bytes([1]) + _u30(0) + _u30(0)   # yöntem özelliği -> 0
    b += _u30(2) + _u30(0)                                 # sınıf: cinit 2, özellik yok
    b += _u30(1) + _u30(3) + _u30(0)                       # betik: init 3
    b += _u30(2) + _govde(0, KOD_NESNE) + _govde(3, KOD_YEREL)
    return b


def swf_kur(abc, sikistir=False):
    etiket = struct.pack("<HI", (abc_okur.DO_ABC << 6) | 0x3F, 4 + 2 + len(abc)) + b"\0\0\0\0t\0" + abc
    govde = b"\x00" + struct.pack("<HH", 24 << 8, 1) + etiket + b"\0\0"
    if sikistir:
        return b"CWS" + bytes([10]) + struct.pack("<I", 8 + len(govde)) + zlib.compress(govde)
    return b"FWS" + bytes([10]) + struct.pack("<I", 8 + len(govde)) + govde


class AbcOkur(unittest.TestCase):
    def setUp(self):
        self.abc = abc_okur.Abc(abc_kur())

    def test_sabit_havuzu_ve_adlar(self):
        self.assertEqual((self.abc.buyuk, self.abc.kucuk), (46, 16))
        self.assertEqual(self.abc.dize(D["buy"]), "buy")
        self.assertEqual(self.abc.ad(M["addCommand"]), "addCommand")
        self.assertEqual(self.abc.yontem_adlari()[0], "Oyun/gonder")
        self.assertEqual(self.abc.yontem_adlari()[1], "Oyun/<kurucu>")

    def test_dogrusal_okuma_anlamsiz_baytta_bozulur(self):
        with self.assertRaises(abc_okur.OkumaHatasi):
            p = 0
            while p < len(KOD_NESNE):
                p = abc_okur.Abc._islem(KOD_NESNE, p).sonraki

    def test_akis_izleme_anlamsiz_baytlari_atlar(self):
        islemler = self.abc.coz(self.abc.govdeler[0])
        self.assertNotIn(6, islemler)
        self.assertEqual(islemler[2].ad, "jump")
        self.assertEqual(islemler[2].hedefler, (9,))
        self.assertEqual(islemler[9].ad, "getlex")

    def test_cagri_argumanlari_nesne_icinden(self):
        cagrilar = self.abc.cagrilar("addCommand", 0)
        self.assertEqual(len(cagrilar), 1)
        nesne = cagrilar[0].argumanlar[0]
        self.assertIsInstance(nesne, abc_okur.Nesne)
        self.assertEqual(abc_okur.yaz(nesne), "{'cmd': 'buy', 'args': [yerel1, 7, -1]}")

    def test_cagri_argumanlari_yereldeki_nesneden(self):
        cagrilar = self.abc.cagrilar("addCommand", 3)
        self.assertEqual(abc_okur.yaz(cagrilar[0].argumanlar[0]), "{'cmd': 'buy', 'args': [yerel1]}")

    def test_swf_icinden(self):
        for sikistir in (False, True):
            etiketler = abc_okur.abc_etiketleri(swf_kur(abc_kur(), sikistir))
            self.assertEqual([ad for ad, _ in etiketler], ["t"])
            self.assertEqual(etiketler[0][1], abc_kur())

    def test_lookupswitch_hedefleri_islem_basina_gore(self):
        kod = bytes([0x24, 0x00, 0x1B, 0x07, 0x00, 0x00, 0x01, 0x07, 0x00, 0x00, 0x08, 0x00, 0x00,
                     0x47, 0x47])
        isl = abc_okur.Abc._islem(kod, 2)
        self.assertEqual(isl.hedefler, (9, 9, 10))
        self.assertEqual(isl.sonraki, 13)


class SunucuOkuma(unittest.TestCase):
    def test_ast_ile_bulunan_isleyiciler_calisandakiyle_ayni(self):
        from oyun import komutlar
        self.assertEqual(set(komut_imzalari.sunucu_komutlari()), set(komutlar.KOMUTLAR))

    def test_buy_okumalari(self):
        buy = komut_imzalari.sunucu_komutlari()["buy"]
        self.assertEqual(buy["en_buyuk_sira"], 6)
        self.assertEqual(buy["belge_args"], (8, 8))

    def test_yardimciya_gecen_argumanlar_izlenir(self):
        kaynak = (
            "@komut('x')\n"
            "def x(save, a):\n"
            "    '''[p, q, (r)]'''\n"
            "    a.tam(0)\n"
            "    yardimci(save, a)\n"
            "def yardimci(save, b):\n"
            "    b.metin(4)\n"
            "@komut('y')\n"
            "def y(save, a):\n"
            "    a.tam(i)\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(kaynak)
        try:
            h = komut_imzalari.sunucu_komutlari(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(h["x"]["en_buyuk_sira"], 4)
        self.assertEqual(h["x"]["belge_args"], (2, 3))
        self.assertIsNone(h["y"]["en_buyuk_sira"])


# 1.4.07'nin sunucuda henüz işleyicisi olmayan komutları. GEC-03 ve GEC-05 bu listeyi boşaltır;
# liste yalnızca küçülür (yeni bir eksik çıkarsa test kırılır).
EKSIK_1407 = {
    "begin_attack_new", "buy_first_purchase", "buy_graveyard_capacity", "buy_powerups", "buy_shield",
    "buy_time_packet", "buy_unit_pack", "buy_viral_offer_all", "buy_viral_offer_friend",
    "clean_attack_log", "collect_game_add_item", "collect_game_buy_all", "collect_game_reward_given",
    "collect_game_speed_up", "collect_game_update_timestamp", "end_attack_new", "end_tournament_match",
    "finish_si_recruitment", "get_enemy_new", "pop_queue_unit", "push_queue_unit", "reply_attack",
    "reset_dragon", "reset_potions_received", "reset_shield", "reward_viral_offer",
    "set_first_purchase_timestamp", "speed_up_queue", "start_quest_new", "time_ff", "unqueue_unit",
}
# Bugünkü 0926 istemcisinin işleyicisi olmayan komutları (KMT-01)
EKSIK_0926 = {"buy_time_packet", "reset_dragon", "time_ff"}


class Kapilar(unittest.TestCase):
    def kiyas(self, ad):
        veri, istemci = komut_imzalari.json_oku(os.path.join(INCELEME, ad))
        return veri, komut_imzalari.karsilastir(istemci, komut_imzalari.sunucu_komutlari())

    def test_1407_listesi_sabit_istemciden(self):
        veri, _ = self.kiyas("1407-komutlar.json")
        self.assertEqual(veri["istemci"], "SocialEmpires1.4.07sec_fixed.swf")
        self.assertEqual(veri["sha256"], "0e4cc17893b1f266b920213d75b0c943f32c3c0d4cf9b994f6a88cab25c76a15")
        # 183 farklı CMD_ değeri = 158 gönderilen + 25 kodda hiç okunmayan
        gonderilmeyen = set(veri["kullanilmayan_sabitler"].values()) - set(veri["komutlar"])
        self.assertEqual((len(veri["komutlar"]), len(gonderilmeyen)), (158, 25))

    def test_1407_imza_uyumsuzlugu_yok(self):
        _, sonuc = self.kiyas("1407-komutlar.json")
        self.assertEqual(sonuc["uyumsuz"], [])

    def test_1407_eksikler_yalnizca_azalir(self):
        _, sonuc = self.kiyas("1407-komutlar.json")
        self.assertLessEqual(set(sonuc["eksik"]), EKSIK_1407)
        bitenler = EKSIK_1407 - set(sonuc["eksik"])
        self.assertFalse(bitenler, "işleyicisi yazılan komutları EKSIK_1407'den çıkar: %s" % sorted(bitenler))

    def test_0926(self):
        veri, sonuc = self.kiyas("0926-komutlar.json")
        self.assertEqual(sonuc["uyumsuz"], [])
        self.assertLessEqual(set(sonuc["eksik"]), EKSIK_0926)

    def test_elle_cikarilan_0926_listesi_aracin_bulduklarinin_alt_kumesi(self):
        """tests/test_komutlar.py'deki elle çıkarılmış liste (128), araçla bulunan 131'in alt kümesi."""
        with open(os.path.join(KOK, "tests", "test_komutlar.py"), encoding="utf-8") as f:
            kaynak = f.read()
        bas = kaynak.index("def test_istemcinin_tum_komutlari_karsilaniyor")
        kume = kaynak[kaynak.index("istemci = {", bas):kaynak.index("}", kaynak.index("istemci = {", bas))]
        elle = set(re.findall(r'"([a-z0-9_]+)"', kume))
        veri, _ = self.kiyas("0926-komutlar.json")
        G = set(veri["komutlar"])
        self.assertEqual((len(elle), len(G)), (128, 131))
        self.assertLessEqual(elle, G)
        self.assertEqual(G - elle, EKSIK_0926)


if __name__ == "__main__":
    unittest.main()
