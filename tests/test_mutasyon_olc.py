"""Mutasyon ölçüm aracının "kapsam dışı" kuralı (araclar/mutasyon_olc.py, docs/TEST_OLCUMU.md).

Beklenen değerlerin kaynağı coverage.py 7.17.2'nin gerçek çıktısıdır (5.11.2026'da çalıştırıldı). Örnek dosya:

    1 def f(a, b):
    2     x = max(a,
    3             b + 1)
    4     if a > 100:
    5         y = (a *
    6              2)
    7         return y
    8     return x
    9 f(1, 2)

`coverage run --branch` + `coverage json` → executed_lines [1, 2, 4, 8, 9], missing_lines [5, 7]. Devam satırları
(3 ve 6) iki listede de yok. Eski kural mutantın satırlarını executed_lines'la kesiştiriyordu; 3. satırdaki mutant
çalıştığı hâlde kapsam dışı sayılıyordu (PR #36 incelemesi).
"""

import importlib.util
import os
import unittest
from types import SimpleNamespace

from ortak import KOK

_spec = importlib.util.spec_from_file_location("mutasyon_olc", os.path.join(KOK, "araclar", "mutasyon_olc.py"))
mutasyon_olc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mutasyon_olc)

KAPSAM = {"oyun/ornek.py": ({1, 2, 4, 8, 9}, {5, 7})}


def mutant(bas, son=None, yol="oyun/ornek.py"):
    return SimpleNamespace(module_path=yol, start_pos=(bas, 0), end_pos=(son or bas, 1))


class KapsamDisiKurali(unittest.TestCase):
    def test_calisan_deyimin_devam_satiri_kosulur(self):
        self.assertFalse(mutasyon_olc.kapsam_disi(mutant(3), KAPSAM))  # b + 1: f(1, 2) bunu çalıştırır

    def test_calismayan_deyim_atlanir(self):
        self.assertTrue(mutasyon_olc.kapsam_disi(mutant(5), KAPSAM))
        self.assertTrue(mutasyon_olc.kapsam_disi(mutant(7), KAPSAM))

    def test_calisan_satir_kosulur(self):
        self.assertFalse(mutasyon_olc.kapsam_disi(mutant(4), KAPSAM))

    def test_kuskulu_durum_kosulur(self):
        # 6. satır çalışmayan deyimin devamı, ama coverage bunu söylemiyor: atlamak yerine koşmak doğru sonuç verir
        self.assertFalse(mutasyon_olc.kapsam_disi(mutant(6), KAPSAM))
        # çalışan satıra da değen çok satırlı mutant atlanmaz
        self.assertFalse(mutasyon_olc.kapsam_disi(mutant(7, 8), KAPSAM))

    def test_kapsam_verisi_olmayan_dosya_kosulur(self):
        self.assertFalse(mutasyon_olc.kapsam_disi(mutant(5, yol="oyun/baska.py"), KAPSAM))

    def test_windows_yolu(self):
        self.assertTrue(mutasyon_olc.kapsam_disi(mutant(5, yol="oyun\\ornek.py"), KAPSAM))


if __name__ == "__main__":
    unittest.main()
