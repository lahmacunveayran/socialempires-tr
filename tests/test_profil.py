"""Profil resmi: oyuncu kendi fotoğrafını koyar; kayıtla birlikte yedeklenir (OYN-05)."""

import io
import json
import unittest

from ortak import KOK  # noqa: F401

from oyun import kayit, kayit_yedek, profil
from oyun import sunucu as server
from oyun.diyar import portre
from oyun.oyuncu import get_player_info

# Geçerli, küçük bir JPEG (2×2)
JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb00430006040506050406060506070706080a100a0a09090a140e0f0c1017141818"
    "171416161a1d251f1a1b231c1616202c20232627292a29191f2d302d283025282928ffdb0043010707070a080a130a0a13281a161a2828"
    "282828282828282828282828282828282828282828282828282828282828282828282828282828282828282828282828ffc00011080002"
    "000203012200021101031101ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303"
    "020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a"
    "25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a9293"
    "9495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2"
    "f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708090a0bffc400b511000201020404030407"
    "05040400010277000102031104052131061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a26"
    "2728292a35363738393a434445464748494a535455565758595a636465666768696a737475767778797a82838485868788898a92939495"
    "969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6"
    "f7f8f9faffda000c03010002110311003f00b3451457c11f6c7fffd9")


class ProfilResmi(unittest.TestCase):
    def setUp(self):
        self.uid = kayit.new_village()
        self.istemci = server.app.test_client()
        with self.istemci.session_transaction() as oturum:
            oturum["USERID"] = self.uid

    def yukle(self, veri, ad="profil.jpg"):
        return self.istemci.post("/profil/resim", data={"resim": (io.BytesIO(veri), ad)},
                                 content_type="multipart/form-data")

    def test_yuklenen_resim_kayitta_ve_sunuluyor(self):
        yanit = self.yukle(JPEG)
        self.assertEqual(yanit.status_code, 200, yanit.get_json())
        pic = yanit.get_json()["pic"]
        k = kayit.session(self.uid)
        self.assertEqual(k["playerInfo"]["pic"], pic)
        self.assertTrue(pic.startswith(f"/profil/resim/{self.uid}.jpg?v="))
        self.assertEqual(portre(k), pic)  # Şeref Kürsüsü ve günlük de kullanır
        resim = self.istemci.get(pic)
        self.assertEqual((resim.status_code, resim.mimetype, resim.data), (200, "image/jpeg", JPEG))
        # Resim oyuna giden bilgide değil, yalnızca kayıtta
        self.assertNotIn("profil_resmi", json.dumps(get_player_info(self.uid)))
        with open(kayit_yedek._yol(self.uid), encoding="utf-8") as f:
            self.assertIn("profil_resmi", json.load(f))

    def test_yedek_zarfi_resmi_tasir_ve_geri_acilir(self):
        self.yukle(JPEG)
        zarf = kayit_yedek.zarf(self.uid)
        self.assertIn("profil_resmi", json.loads(zarf["kayit"]))
        kimlik, _ = kayit_yedek.zarfi_ac(json.dumps(zarf), self.uid)
        self.assertEqual(kimlik, self.uid)

    def test_jpeg_olmayan_ve_buyuk_dosya_reddedilir(self):
        for veri in (b"<svg/>", b"\x89PNG\r\n\x1a\n" + b"0" * 20, b""):
            self.assertEqual(self.yukle(veri).status_code, 400)
        buyuk = JPEG[:-2] + b"\x00" * profil.EN_BUYUK + JPEG[-2:]
        self.assertEqual(self.yukle(buyuk).status_code, 400)
        self.assertEqual(kayit.session(self.uid)["playerInfo"]["pic"], "")

    def test_kaldirinca_varsayilan_portre(self):
        self.yukle(JPEG)
        yanit = self.istemci.post("/profil/resim/sil")
        self.assertEqual(yanit.get_json()["pic"], "/img/profile/1025.png")
        self.assertNotIn("profil_resmi", kayit.session(self.uid))
        self.assertEqual(self.istemci.get(f"/profil/resim/{self.uid}.jpg").status_code, 404)

    def test_girissiz_yuklenmez_ve_gecersiz_kimlik(self):
        bos = server.app.test_client()
        self.assertEqual(bos.post("/profil/resim").status_code, 403)
        self.assertEqual(bos.get("/profil").status_code, 302)
        self.assertEqual(bos.get("/profil/resim/..%2Fayarlar.jpg").status_code, 404)

    def test_sayfa_aciliyor(self):
        sayfa = self.istemci.get("/profil").get_data(as_text=True)
        self.assertIn('accept="image/*"', sayfa)
        self.assertIn("/img/profile/1025.png", sayfa)


if __name__ == "__main__":
    unittest.main()
