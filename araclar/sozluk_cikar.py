# -*- coding: utf-8 -*-
"""
Oyun metinlerini çeviri tablosuna (CSV) çıkarır.

Kullanım:
    python araclar/sozluk_cikar.py

Çıktı:
    ceviri/sozluk.csv  ->  anahtar, bolum, ingilizce, turkce
    ceviri/sozluk.json ->  aynı veri, araçlar için

Not: Metinler, config yamaları (config/patch) ve modlar uygulandıktan
sonraki nihai oyundan alınır; böylece yamaların eklediği eşyalar da
çeviri listesine girer.
"""

import csv
import json
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)


def config_yukle():
    try:
        from oyun.config import get_game_config
        return get_game_config(), "yamalar uygulanmış config"
    except Exception as hata:  # jsonpatch kurulu değilse ham dosyaya düş
        print(f" ! get_game_config yüklenemedi ({hata}); ham JSON kullanılıyor")
        import glob
        adaylar = sorted(glob.glob(os.path.join(KOK, "config", "game_config_*.json")))
        # Sunucunun kullandığı sürüm: 20120826 (4399 = Çince varyant)
        tercih = [a for a in adaylar if "20120826" in a]
        secilen = tercih[0] if tercih else adaylar[-1]
        with open(secilen, "r", encoding="utf-8") as f:
            return json.load(f), "ham config: " + os.path.basename(secilen)


def main():
    from oyun.turkce import _bolum_anahtarlari, cevirileri_yukle, TR_DOSYASI

    config, kaynak = config_yukle()
    print(f" [+] Config: {kaynak}")

    ceviriler = cevirileri_yukle()
    kayitlar = _bolum_anahtarlari(config)

    csv_yolu = os.path.join(KOK, "ceviri", "sozluk.csv")
    json_yolu = os.path.join(KOK, "ceviri", "sozluk.json")

    satirlar = []
    for anahtar, bolum, metin, _yol in kayitlar:
        satirlar.append({
            "anahtar": anahtar,
            "bolum": bolum,
            "ingilizce": metin,
            "turkce": ceviriler.get(anahtar, ""),
        })

    with open(csv_yolu, "w", encoding="utf-8-sig", newline="") as f:
        y = csv.DictWriter(f, fieldnames=["anahtar", "bolum", "ingilizce", "turkce"])
        y.writeheader()
        y.writerows(satirlar)

    with open(json_yolu, "w", encoding="utf-8") as f:
        json.dump(satirlar, f, ensure_ascii=False, indent=1)

    # Özet
    bolumler = {}
    for s in satirlar:
        b = bolumler.setdefault(s["bolum"], [0, 0])
        b[0] += 1
        if s["turkce"]:
            b[1] += 1

    print(f" [+] {len(satirlar)} metin -> {csv_yolu}")
    for b, (toplam, cevrilen) in sorted(bolumler.items()):
        print(f"     {b:<10} {cevrilen:>5} / {toplam:<5} çevrildi")


if __name__ == "__main__":
    main()
