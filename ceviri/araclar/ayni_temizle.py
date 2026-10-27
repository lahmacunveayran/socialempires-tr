# -*- coding: utf-8 -*-
"""Kaynak metinle birebir aynı kalan çevirileri yeniden çevirir."""

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
    return ((d.get("responseData") or {}).get("translatedText") or "").strip()


def main():
    mevcut = cevirileri_yukle()
    hedef = []
    for k, _b, m, _y in _bolum_anahtarlari(get_game_config()):
        if k in mevcut and m.strip() and mevcut[k].strip() == m.strip() and " " in m.strip():
            hedef.append((k, m))
    print(f"[+] {len(hedef)} aynı metin")
    with open(YOL, encoding="utf-8") as f:
        veri = json.load(f)
    cev = veri.setdefault("ceviriler", {})
    for i, (k, m) in enumerate(hedef, 1):
        try:
            t = cevir(m)
        except Exception as hata:
            print(" !", k, hata)
            time.sleep(3)
            continue
        if t and t != m and not dogrula(m, t):
            cev[k] = t
        if i % 10 == 0:
            print(f" * {i}/{len(hedef)}")
            with open(YOL, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=1)
        time.sleep(0.35)
    with open(YOL, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    print("[+] bitti")


if __name__ == "__main__":
    main()
