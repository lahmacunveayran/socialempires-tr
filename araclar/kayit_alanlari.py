"""İstemcinin kayıttan (`privateState`) okuduğu alanlar: 1.4.07 ile 0926 arasındaki fark (GEC-04).

Bir alan, bayt kodunda `privateState` adının okunmasından hemen sonra gelen `getproperty/setproperty <ad>` ile
bulunur. 1.4.07'nin kodu karıştırılmıştır: iki işlemin arasına anlamsız `jump`lar ve hata ayıklama satırları
konmuştur; bu yüzden "sonraki işlem" atlamalar izlenerek bulunur (S-30). `privateState` bir yerel değişkene
alınmışsa o yerelin okunmasından sonraki ad da sayılır.

Sınır (◐): `privateState` bir yönteme argüman olarak geçip orada parametreden okunan alanlar (ör.
`DailyBonusManager/initPlayerData` içindeki `lastDayRewarded`) bulunmaz.

Komut satırı:
    python araclar/kayit_alanlari.py 1.4.07.swf --eski 0926.swf [--json docs/inceleme/1407-kayit-alanlari.json]
"""

import argparse
import bisect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abc_okur  # noqa: E402

KOK_AD = "privateState"
ERISIM = {"getproperty", "setproperty", "initproperty", "deleteproperty"}
GECILEN = {"debugline", "debugfile", "debug", "label", "kill", "nop", "coerce", "coerce_a", "convert_o", "dup"}
YEREL_YAZ = {"setlocal": None, "setlocal_1": 1, "setlocal_2": 2, "setlocal_3": 3}
YEREL_OKU = {"getlocal": None, "getlocal_1": 1, "getlocal_2": 2, "getlocal_3": 3}


def _yerel(islem, tablo):
    sira = tablo[islem.ad]
    return islem.isl[0] if sira is None else sira


def okunan_alanlar(islemler: dict, ad) -> set:
    """Bir yöntem gövdesinde `privateState`'ten okunan ya da yazılan adlar.

    `islemler`: ofset -> Islem (abc_okur.Abc.coz); `ad(i)`: çok adlının okunur adı."""
    ofsetler = sorted(islemler)

    def sonraki(ofset):
        for _ in range(64):
            k = bisect.bisect_right(ofsetler, ofset)
            if k >= len(ofsetler):
                return None
            ofset = ofsetler[k]
            i = islemler[ofset]
            while i.ad == "jump" and i.hedefler:
                ofset = i.hedefler[0]
                if ofset not in islemler:
                    return None
                i = islemler[ofset]
            if i.ad not in GECILEN:
                return i
        return None

    def kok(i):
        return i.ad in ("getproperty", "getlex") and ad(i.isl[0]) == KOK_AD

    yereller = set()
    for o in ofsetler:
        if kok(islemler[o]):
            s = sonraki(o)
            if s is not None and s.ad in YEREL_YAZ:
                yereller.add(_yerel(s, YEREL_YAZ))
    alanlar = set()
    for o in ofsetler:
        i = islemler[o]
        if kok(i) or (i.ad in YEREL_OKU and _yerel(i, YEREL_OKU) in yereller):
            s = sonraki(o)
            if s is not None and s.ad in ERISIM:
                isim = ad(s.isl[0])
                if isim and isim not in ("[]", "*"):
                    alanlar.add(isim)
    return alanlar


def istemci_alanlari(veri: bytes) -> dict:
    """ad -> onu okuyan yöntemlerin sıralı listesi."""
    sonuc = {}
    for abc in abc_okur.swf_abc(veri):
        adlar = abc.yontem_adlari()
        for govde in abc.govdeler.values():
            try:
                islemler = abc.coz(govde)
            except abc_okur.OkumaHatasi:
                continue
            for isim in okunan_alanlar(islemler, abc.ad):
                sonuc.setdefault(isim, set()).add(adlar.get(govde.yontem, str(govde.yontem)))
    return {k: sorted(v) for k, v in sorted(sonuc.items())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("istemci")
    ap.add_argument("--eski", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    with open(a.istemci, "rb") as f:
        yeni = istemci_alanlari(f.read())
    with open(a.eski, "rb") as f:
        eski = istemci_alanlari(f.read())
    sonuc = {"istemci": os.path.basename(a.istemci), "eski": os.path.basename(a.eski),
             "okunan": len(yeni), "eskide_okunan": len(eski),
             "yeni": {k: v for k, v in yeni.items() if k not in eski},
             "kalkan": sorted(set(eski) - set(yeni))}
    print(f"{len(yeni)} alan ({len(eski)} eskide); yeni {len(sonuc['yeni'])}: {', '.join(sonuc['yeni'])}")
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump(sonuc, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
