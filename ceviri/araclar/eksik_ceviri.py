# -*- coding: utf-8 -*-
"""Eksik kalan çevirileri (baş/son satır sonu yüzünden atlananlar) tamamlar."""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KOK)

from turkce import _bolum_anahtarlari, cevirileri_yukle, dogrula  # noqa: E402
from get_game_config import get_game_config  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (SocialEmperorsLocal)"}
HEDEF = os.path.join(KOK, "ceviri", "oto_tr.json")


def cevir(metin):
    veri = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": metin}).encode()
    istek = urllib.request.Request("https://translate.googleapis.com/translate_a/single", data=veri, headers=UA)
    with urllib.request.urlopen(istek, timeout=40) as cevap:
        d = json.loads(cevap.read().decode("utf-8"))
    return "".join(p[0] for p in d[0])


def main():
    mevcut = cevirileri_yukle()
    eksik = [(k, m) for k, _b, m, _y in _bolum_anahtarlari(get_game_config()) if k not in mevcut]
    print(f"[+] {len(eksik)} eksik")
    with open(HEDEF, encoding="utf-8") as f:
        veri = json.load(f)
    ceviriler = veri.setdefault("ceviriler", {})
    for i, (anahtar, metin) in enumerate(eksik, 1):
        onek = metin[:len(metin) - len(metin.lstrip("\n"))]
        son = metin[len(metin.rstrip("\n")):]
        cekirdek = metin.strip("\n")
        for deneme in range(4):
            try:
                cev = cevir(cekirdek)
                tam = onek + cev.strip() + son
                if dogrula(metin, tam):
                    tam = onek + cev + son
                if not dogrula(metin, tam):
                    ceviriler[anahtar] = tam
                break
            except Exception as hata:
                if "429" in str(hata):
                    time.sleep(8 + deneme * 5)
                else:
                    print(" !", anahtar, hata)
                    break
        if i % 10 == 0:
            print(f" * {i}/{len(eksik)}")
            with open(HEDEF, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=1)
        time.sleep(1.2)
    with open(HEDEF, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    print("[+] bitti", len(ceviriler))


if __name__ == "__main__":
    main()
