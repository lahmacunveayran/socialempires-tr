"""Kullanıcı ayarları (`ayarlar.json`)."""

import json
import os

from oyun.yollar import AYARLAR


def oku() -> dict:
    """ayarlar.json'u okur; dosya yoksa veya bozuksa boş sözlük döner."""
    if not os.path.exists(AYARLAR):
        return {}
    try:
        with open(AYARLAR, encoding="utf-8-sig") as f:
            return json.load(f)
    except (ValueError, OSError) as hata:
        print(f" ! {AYARLAR} okunamadi ({hata}); varsayilan ayarlar kullanilacak")
        return {}
