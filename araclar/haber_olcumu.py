"""Diyar Haberleri yoğunluğunu ölçer: dakikada ortalama olay (Λ).

Kayıtların geçici bir kopyası üzerinde dünya simülasyonunu art arda çalıştırır
(bir tur = `tick_saniye`, varsayılan 60 sn) ve tur başına olay sayısını yazar.
Gerçek kayıtlara dokunmaz.

Kullanım: python araclar/haber_olcumu.py [tur_sayisi]
"""

import math
import os
import shutil
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

if __name__ == "__main__":
    tur = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    gecici = tempfile.mkdtemp(prefix="se-haber-")
    kaynak = os.path.join(KOK, "saves")
    if os.path.isdir(kaynak):
        for ad in os.listdir(kaynak):
            if ad.endswith(".save.json"):
                shutil.copy2(os.path.join(kaynak, ad), gecici)
    os.environ["SE_KAYIT_DIZINI"] = gecici
    try:
        from oyun import sunucu  # noqa: F401  (bot yoksa üretir)
        from oyun.dunya import Dunya

        dunya = Dunya()
        dakika = dunya.ayar.get("tick_saniye", 60) / 60
        saat = time.time()
        for i in range(tur):
            # Akın sınırları gerçek saate bağlı: her turu bir tur sonrasına taşı.
            gercek = time.time
            time.time = lambda kayma=i * dakika * 60: gercek() + kayma
            try:
                dunya.tek_tick()
            finally:
                time.time = gercek
        sayilar = {}
        for olay in dunya.olaylar:
            sayilar[olay["tur"]] = sayilar.get(olay["tur"], 0) + 1
        lam = len(dunya.olaylar) / (tur * dakika)
        print(f"{tur} tur ({tur * dakika:.0f} dk): {len(dunya.olaylar)} olay, turlere gore {sayilar}")
        print(f"Lambda = {lam:.2f} olay/dk, bos dakika olasiligi e^-L = {math.exp(-lam):.0%}")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
