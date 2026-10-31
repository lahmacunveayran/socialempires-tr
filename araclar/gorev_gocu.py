"""Eski görev numaralarından 1.4.07 hedef numaralarına göç tablosu (GOR-01, GEC-04).

0926 istemcisi görevleri kendi içinde numarayla tanıyordu; config'teki `missions` (228) yalnızca başlık, açıklama ve
ödül tutar. 1.4.07'nin hedefleri `goals.json`'dadır (206). İki liste 113'ten sonra aynı numarada başka görevler
taşır, bu yüzden kayıttaki `completedMissions` ve `rewardedMissions` numaraları çevrilmelidir.

Eşleşme kuralı:

1. Başlık (büyük-küçük harf, boşluk ve noktalama dışında) aynı **ve** ödül numarası aynı: eşleşir.
   Ödül numarası, aynı başlığı taşıyan farklı görevleri ayırır: eski 110 "Train 2 villagers" (ödül 220, Town Hall II)
   eğitimdeki 11 "Train 2 villagers" (ödül 20) değildir.
2. Adı değişmiş görevler: `YENIDEN_ADLANDIRILAN`. Her biri elle karşılaştırıldı; ödül numarası aynı, açıklama aynı
   ya da yalnızca adı değişmiş. Sayısı ya da işi değişen görev (3 yerine 5 okçu gibi) buraya alınmaz.
3. Geri kalan eski görevin 1.4.07'de karşılığı yoktur; göçte düşer. Oyuncu o numaralı yeni hedefi kendisi yapar.

Komut satırı:
    python araclar/gorev_gocu.py            # tabloyu config/gorev_gocu.json'a yazar
    python araclar/gorev_gocu.py --denetle  # dosya güncel değilse 1 ile çıkar
"""

import argparse
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABAN = os.path.join(KOK, "config", "game_config_20120826.json")
HEDEFLER = os.path.join(KOK, "config", "goals.json")
TABLO = os.path.join(KOK, "config", "gorev_gocu.json")

# eski numara: (1.4.07 numarası, gerekçe)
YENIDEN_ADLANDIRILAN = {
    94: (94, "Defeat 3 players → Defeat three players; açıklama aynı"),
    105: (105, "Traning → Training (yazım); açıklama aynı"),
    136: (148, "Big Church → Great Church; açıklamada yalnızca ad değişti"),
    153: (165, "Build Archery II → Build Archery III; açıklama zaten Archery III, aynı"),
    167: (180, "eggplant farms → eggplant fields; açıklamada yalnızca ad değişti"),
    187: (200, "Update … Town Hall III → Updgrade to Town Hall III; açıklamada yalnızca fiil değişti"),
    189: (202, "Update the Market to Market III → Upgrade to Market III; açıklama aynı"),
    201: (214, "carrot farms → Carrot Fields; açıklamada yalnızca ad değişti"),
    221: (234, "watermelon Farms → Watermelon Fields; açıklamada yalnızca ad değişti"),
    222: (235, "Update Town Hall IV → Upgrade to Town Hall IV; açıklamada yalnızca fiil değişti"),
}
# Ödülü aynı olduğu hâlde alınmayanlar (kanıt için): 30 (3 okçu → 5), 184 (2 Archer Knight → 3),
# 60 (Defensive Strategy → Attack 2 players), 115 (500 odun → 3 kez kaynak), 157 (House I→II → House II→III).


def _ad(baslik):
    return re.sub(r"[^a-z0-9]", "", str(baslik).lower())


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def tablo(eski_gorevler, hedefler):
    """{eski numara: yeni numara}. Karşılığı olmayan eski numara tabloda yoktur."""
    yeni = {int(h["id"]): h for h in hedefler}
    adla = {}
    for numara, h in yeni.items():
        adla.setdefault((_ad(h["title"]), h["reward"]), []).append(numara)
    sonuc = {}
    for g in eski_gorevler:
        eski = int(g["id"])
        if eski in YENIDEN_ADLANDIRILAN:
            hedef = YENIDEN_ADLANDIRILAN[eski][0]
            if yeni[hedef]["reward"] != g["reward"]:
                raise ValueError(f"{eski} → {hedef}: ödül numarası farklı")
            sonuc[eski] = hedef
            continue
        adaylar = adla.get((_ad(g["title"]), g["reward"]), [])
        if len(adaylar) == 1:
            sonuc[eski] = adaylar[0]
        elif len(adaylar) > 1:
            raise ValueError(f"{eski}: birden çok aday {adaylar}")
    return sonuc


def uret():
    eski = _oku(TABAN)["missions"]
    t = tablo(eski, _oku(HEDEFLER))
    return {
        "aciklama": "Eski görev numarası → 1.4.07 hedef numarası (araclar/gorev_gocu.py üretir; elle değiştirilmez).",
        "eski_sayisi": len(eski),
        "tablo": {str(k): v for k, v in sorted(t.items())},
    }


def _yaz_metni(veri):
    return json.dumps(veri, ensure_ascii=False, indent=1) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--denetle", action="store_true")
    secenek = ap.parse_args(argv)
    metin = _yaz_metni(uret())
    if secenek.denetle:
        with open(TABLO, encoding="utf-8") as f:
            guncel = f.read() == metin
        print("güncel" if guncel else "güncel değil: python araclar/gorev_gocu.py")
        return 0 if guncel else 1
    with open(TABLO, "w", encoding="utf-8", newline="\n") as f:
        f.write(metin)
    t = json.loads(metin)["tablo"]
    print(f"{len(t)} eşleşme, {sum(1 for k, v in t.items() if int(k) != v)} numarası değişen; {TABLO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
