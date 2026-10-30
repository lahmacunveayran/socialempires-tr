"""Eksik efektin oyunun kendi efektinden türetilmesi (oyun.fx_yama)."""

import struct
import unittest
import zlib

from ortak import KOK  # noqa: F401

from oyun import fx_yama


def _etiket(kod, govde):
    return struct.pack("<HI", kod << 6 | 63, len(govde)) + govde


def kucuk_swf(sinif="p.fireBall", sikistir=True):
    """Bir DoABC ve bir SymbolClass etiketi olan en küçük SWF."""
    paket, _, ad = sinif.rpartition(".")
    dizeler = [paket.encode(), ad.encode(), b"flash.display"]
    abc = struct.pack("<HH", 16, 46) + b"\x00\x00\x00" + bytes([len(dizeler) + 1])
    abc += b"".join(bytes([len(d)]) + d for d in dizeler) + b"\x07\x08\x09"
    govde = b"\x00" + struct.pack("<HH", 30 << 8, 1)  # boş dikdörtgen, 30 kare/sn, 1 kare
    govde += _etiket(82, struct.pack("<I", 1) + b"\0" + abc)
    govde += _etiket(76, struct.pack("<HH", 1, 0) + sinif.encode() + b"\0")
    govde += struct.pack("<H", 0)
    imza = b"CWS" if sikistir else b"FWS"
    return imza + b"\x0a" + struct.pack("<I", len(govde) + 8) + (zlib.compress(govde) if sikistir else govde)


class FxYamaTestleri(unittest.TestCase):
    def test_sinif_yeniden_adlandirilir(self):
        for sikistir in (True, False):
            yeni = fx_yama.sinifi_yeniden_adlandir(kucuk_swf(sikistir=sikistir), "p.fireBall", "p.miniFireball2")
            govde = zlib.decompress(yeni[8:]) if sikistir else yeni[8:]
            self.assertEqual(struct.unpack("<I", yeni[4:8])[0], len(govde) + 8)
            self.assertIn(b"\x0dminiFireball2", govde)       # ABC dize havuzu
            self.assertIn(b"p.miniFireball2\0", govde)        # SymbolClass
            self.assertNotIn(b"fireBall", govde)
            self.assertIn(b"\rflash.display\x07\x08\x09", govde)  # geri kalan bayt aynı

    def test_turetilen_efektler_oyunun_kendi_efektleri(self):
        for istenen, kaynak in fx_yama.TURETILEN.items():
            self.assertTrue(istenen.startswith("fx/") and kaynak.startswith("fx/"))
            self.assertEqual(fx_yama.sinif_adi(istenen).split(".")[0], fx_yama.sinif_adi(kaynak).split(".")[0])

    def test_paket_degisemez(self):
        with self.assertRaises(ValueError):
            fx_yama.sinifi_yeniden_adlandir(kucuk_swf(), "p.fireBall", "b.fireBall")


if __name__ == "__main__":
    unittest.main()
