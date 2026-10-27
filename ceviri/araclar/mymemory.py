# -*- coding: utf-8 -*-
"""Kalan metinleri MyMemory ile çevirir (Google kotası dolduğunda yedek)."""

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

YOL = os.path.join(KOK, "ceviri", "oto_tr.json")
UA = {"User-Agent": "Mozilla/5.0"}


def cevir(metin):
    u = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(
        {"q": metin, "langpair": "en|tr"}
    )
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    return (d.get("responseData") or {}).get("translatedText", "")


def main():
    mevcut = cevirileri_yukle()
    eksik = [(k, m) for k, _b, m, _y in _bolum_anahtarlari(get_game_config())
             if k not in mevcut and m.strip()]
    print(f"[+] {len(eksik)} eksik")
    with open(YOL, encoding="utf-8") as f:
        veri = json.load(f)
    cev = veri.setdefault("ceviriler", {})
    for i, (anahtar, metin) in enumerate(eksik, 1):
        try:
            t = cevir(metin)
        except Exception as hata:
            print(" !", anahtar, hata)
            time.sleep(3)
            continue
        t = (t or "").strip()
        if t and not dogrula(metin, t):
            cev[anahtar] = t
        if i % 10 == 0:
            print(f" * {i}/{len(eksik)}")
            with open(YOL, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=1)
        time.sleep(0.4)
    with open(YOL, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    print("[+] bitti", len(cev))


if __name__ == "__main__":
    main()
