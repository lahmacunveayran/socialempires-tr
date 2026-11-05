"""Bütün komutlar için değişmezler: rastgele (bozuk dahil) argümanlarla özellik tabanlı test (Hypothesis).

Beklenen değerler uygulamadan çıkarılmaz; her değişmezin kaynağı ayrıdır (sınama kâhini sorunu, Barr vd. 2015):
  D1 kaynaklar ve nakit eksiye düşmez, tamsayı kalır: komutlar.py'nin belge dizesi ("Kaynaklar eksiye düşmez").
  D2 kayıt standart JSON'a yazılıp geri okununca aynıdır: kayıt diske JSON olarak yazılır (kayit.save_session).
  D3 göçün güvencesindeki alanlar istemcinin beklediği türde kalır: kayit_semasi.guvence_hatalari.
  D4 hata veren komut kaydı değiştirmez: yarım iş kalmaz (komutlar.command).
  D5 depo (gifts) oyundaki en büyük eşya id'sinden uzun olmaz: kayıt şişmez (komutlar.depo_ekle).

Örnekler `derandomize` ile sabittir: her koşu aynı girdileri dener, test ara sıra düşüp kalkmaz. Daha geniş
arama için: HYPOTHESIS_PROFILE=kesif python -m unittest test_degismezler (her koşuda yeni rastgele girdiler).
"""

import contextlib
import copy
import io
import json
import os
import unittest

import ortak
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

settings.register_profile("ci", max_examples=25, deadline=None, derandomize=True, database=None,
                          suppress_health_check=[HealthCheck.too_slow])
settings.register_profile("kesif", max_examples=1000, deadline=None,
                          suppress_health_check=[HealthCheck.too_slow])
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

# Kayıttaki eşyaların koordinat ve id'leri (bos_kayit: (10,10) id 1, (20,20) id 19) ile sınır değerler: komutlar
# yalnızca var olan bir eşyaya denk gelince dallarına girer.
SAYI = st.sampled_from([0, 1, 2, 3, -1, -5, 10, 13, 19, 20, 31, 99, 1000, 50031, 10**8, 2**31, -(2**31)])
DEGER = st.one_of(
    SAYI, st.integers(), st.floats(allow_nan=True, allow_infinity=True), SAYI.map(str),
    st.text(max_size=6), st.none(), st.booleans(),
    st.sampled_from(["g", "w", "s", "f", "c", "m", "u", "n", "gold", "cash", "1,2,3", "{}", "[]", "nan", "inf",
                     '{"1": 2}', '{"100000000": 1}', '{"map": 0, "resources": {"g": -99999, "x": 5}}', "[1, 19]"]),
    st.lists(SAYI, max_size=3), st.dictionaries(SAYI.map(str), SAYI, max_size=2),
)
ARGUMANLAR = st.lists(DEGER, max_size=8)
KAYNAKLAR = ("coins", "wood", "stone", "food")


def kaynak_ihlalleri(kayit):
    sorun = []
    nakit = kayit["playerInfo"].get("cash")
    if type(nakit) is not int or nakit < 0:
        sorun.append(f"cash={nakit!r}")
    mana = kayit["privateState"].get("mana", 0)
    if type(mana) is not int or mana < 0:
        sorun.append(f"mana={mana!r}")
    for i, h in enumerate(kayit["maps"]):
        for alan in KAYNAKLAR:
            deger = h.get(alan, 0)
            if type(deger) is not int or deger < 0:
                sorun.append(f"maps[{i}].{alan}={deger!r}")
    return sorun


class Degismezler(ortak.KomutTesti):
    def setUp(self):
        super().setUp()
        from oyun import kayit_semasi
        from oyun.config import get_game_config
        self.sema = kayit_semasi
        self.en_buyuk_id = max(int(e["id"]) for e in get_game_config()["items"])
        # Komut günlüğü (yalnızca hata ayıklama) binlerce örnekte diske yazıp testi yavaşlatmasın
        self._gunluk = self.komutlar._gunluge_yaz
        self.komutlar._gunluge_yaz = lambda uid, komutlar: None

    def tearDown(self):
        self.komutlar._gunluge_yaz = self._gunluk
        super().tearDown()

    def _yeni_kayit(self):
        kayit = ortak.bos_kayit()
        self.sema.eksikleri_tamamla(kayit["privateState"])
        self.kayitlar["test"] = kayit
        return kayit

    def _degismezleri_denetle(self, ad):
        @given(ARGUMANLAR)
        def ozellik(args):
            kayit = self._yeni_kayit()
            once = copy.deepcopy(kayit)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.komutlar.command("test", {"commands": [{"cmd": ad, "args": args}]})
            self.assertEqual(kaynak_ihlalleri(kayit), [], "D1")
            self.assertEqual(json.loads(json.dumps(kayit, allow_nan=False)), kayit, "D2")
            self.assertEqual(self.sema.guvence_hatalari(kayit["privateState"]), [], "D3")
            self.assertLessEqual(len(kayit["privateState"].get("gifts", [])), self.en_buyuk_id + 1, "D5")
            # D4: işleyici doğrudan çağrılır; hata verirse command'in geri aldığı kayıt öncekiyle aynı olmalı
            dogrudan = copy.deepcopy(once)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.komutlar.KOMUTLAR[ad](dogrudan, self.komutlar.Arg(args))
            except Exception:  # noqa: BLE001 - hatanın kendisi değil, kayda etkisi sınanıyor
                self.assertEqual(kayit, once, "D4")
        ozellik()

    def test_her_komut_degismezleri_korur(self):
        for ad in sorted(self.komutlar.KOMUTLAR):
            with self.subTest(komut=ad):
                self._degismezleri_denetle(ad)

    def test_hata_veren_komut_kaydi_degistirmez(self):
        # Bilinen örnek: nakit düşer, sonra bozuk id listesi hata verir (add_items_store [liste, nakit]).
        nakit = self.kayit["playerInfo"]["cash"]
        once = copy.deepcopy(self.kayit)
        self.komutlar.command("test", {"commands": [
            {"cmd": "add_items_store", "args": ['{"map": 0}', 7]},
            {"cmd": "add_items_store", "args": ["[19]", 3]},
        ]})
        self.assertEqual(self.kayit["playerInfo"]["cash"], nakit - 3)  # yalnızca ikinci (sağlam) komut
        once["playerInfo"]["cash"] = nakit - 3
        once["privateState"]["gifts"] = [0] * 19 + [1]
        self.assertEqual(self.kayit, once)

    def test_oyunda_olmayan_esya_depoya_girmez(self):
        self.komut("store_add_items", "[100000000, 19]")
        self.assertEqual(self.kayit["privateState"]["gifts"], [0] * 19 + [1])


if __name__ == "__main__":
    unittest.main()
