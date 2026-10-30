"""İmparatorluk günlüğü: savaş geçmişi, özet ve seviye ilerlemesi (OYN-02)."""

import json
import os
import tempfile
import unittest

from ortak import KOK, bos_kayit  # noqa: F401

from oyun import gunluk, kayit
from oyun import sunucu as server


def ornek_kayit():
    k = bos_kayit("ben")
    k["privateState"]["honor"] = 12
    k["privateState"]["attacksSent"] = [
        {"time": 1793300000, "victim_id": "x1",
         "description": {"win": 1, "resources": {"g": 1500, "x": 40},
                         "oponent": {"name": "Cengiz Han", "level": 31, "pic": "/img/profile/1.png"}}},
        {"time": 1793300100, "victim_id": "x2",
         "description": {"win": 0, "resources": {"g": 0, "x": 0}, "oponent": {"name": "Timur", "level": 20}}},
        {"time": 1793300200, "victim_id": "yok"},  # bot akınlarının eski kaydı: açıklama yok
    ]
    k["privateState"]["attacksReceived"] = [
        {"time": 1793300300, "attacker_id": "x3",
         "description": {"win": 1, "resources": {"g": 700}, "oponent": {"name": "Tardu", "level": 19}}},
        {"time": 1793300400, "attacker_id": "x4",
         "description": {"win": 0, "resources_victim": {"g": 90}, "oponent": {"name": "Modu Han"}}},
    ]
    return k


class Gunluk(unittest.TestCase):
    def test_savaslar_yeniden_eskiye_ve_yonler(self):
        liste = gunluk.savaslar(ornek_kayit())
        self.assertEqual([s["zaman"] for s in liste], sorted((s["zaman"] for s in liste), reverse=True))
        savunma = [s for s in liste if s["yon"] == "savunma"]
        self.assertEqual([(s["rakip"]["ad"], s["zafer"], s["altin"]) for s in savunma],
                         [("Modu Han", True, 90), ("Tardu", False, 700)])
        aciklamasiz = [s for s in liste if s["zaman"] == 1793300200][0]
        self.assertIsNone(aciklamasiz["zafer"])
        self.assertEqual(aciklamasiz["rakip"]["ad"], "Bilinmeyen köy")
        self.assertEqual(liste[0]["tarih"], "29.10.2026 22:00")  # 1793300400, Türkiye saatiyle (UTC+3)

    def test_ozet(self):
        k = ornek_kayit()
        o = gunluk.ozet(k, gunluk.savaslar(k))
        self.assertEqual((o["saldiri"], o["saldiri_zafer"], o["ganimet"], o["xp"]), (3, 1, 1500, 40))
        self.assertEqual((o["savunma"], o["savunma_zafer"], o["kayip"], o["onur"]), (2, 1, 700, 12))

    def test_ilerleme_gunluk_yedeklerden(self):
        k = ornek_kayit()
        with tempfile.TemporaryDirectory() as kok:
            for gun, xp, seviye in (("2026-10-28", 100, 3), ("2026-10-29", 250, 4)):
                os.makedirs(os.path.join(kok, gun))
                eski = bos_kayit("ben")
                eski["maps"][0].update(xp=xp, level=seviye)
                with open(os.path.join(kok, gun, "ben.save.json"), "w", encoding="utf-8") as f:
                    json.dump(eski, f)
            os.makedirs(os.path.join(kok, "2026-10-27"))  # bu kayıt o gün yok
            satirlar = gunluk.ilerleme("ben", k, kok)
        self.assertEqual([s["gun"] for s in satirlar][:2], ["2026-10-28", "2026-10-29"])
        self.assertIsNone(satirlar[0]["xp_artis"])
        self.assertEqual(satirlar[1]["xp_artis"], 150)
        self.assertEqual(satirlar[-1]["seviye"], k["maps"][0]["level"])

    def test_sayfa(self):
        istemci = server.app.test_client()
        self.assertEqual(istemci.get("/gunluk").status_code, 302)  # giriş yapılmadan
        uid = kayit.new_village()
        with istemci.session_transaction() as oturum:
            oturum["USERID"] = uid
        yanit = istemci.get("/gunluk")
        self.assertEqual(yanit.status_code, 200)
        govde = yanit.get_data(as_text=True)
        self.assertIn("İmparatorluk Günlüğü", govde)
        self.assertIn(server.STATIK_YOL + "images_new/b_4.png", govde)  # yalnızca oyunun kendi armaları


if __name__ == "__main__":
    unittest.main()
