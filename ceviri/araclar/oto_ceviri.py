# -*- coding: utf-8 -*-
"""Kalan tüm metinleri (eşya, görev, yardım) otomatik Türkçeye çevirir.

Google Translate'in herkese açık uç noktasını kullanır. Çeviriler
`ceviri/oto_tr.json` dosyasına yazılır; elle yazılan `tr.json` her zaman
önceliklidir.

Kullanım:
    python ceviri\\araclar\\oto_ceviri.py
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KOK)

from turkce import _bolum_anahtarlari, dogrula  # noqa: E402

try:
    from get_game_config import get_game_config
except ImportError as hata:
    print("Config yüklenemedi:", hata)
    raise

AYIRAC = "@@987654321@@"
UA = {"User-Agent": "Mozilla/5.0 (SocialEmperorsLocal)"}

# Oyun terimleri için küçük sözlük (makine çevirisinden sonra düzeltme)
SOZLUK = [
    ("Trol", "Troll"),
    ("Madeni Para", "Altın"),
    ("madeni para", "altın"),
]


def cevir(metinler):
    """Metin listesini tek istekte çevirir; satır sayısı korunur."""
    ham = ("\n" + AYIRAC + "\n").join(metinler)
    veri = urllib.parse.urlencode({
        "client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": ham,
    }).encode("utf-8")
    istek = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single", data=veri, headers=UA
    )
    with urllib.request.urlopen(istek, timeout=40) as cevap:
        d = json.loads(cevap.read().decode("utf-8"))
    sonuc = "".join(parca[0] for parca in d[0])
    return [p.strip("\n") for p in sonuc.split(AYIRAC)]


def duzelt(metin):
    for eski, yeni in SOZLUK:
        metin = metin.replace(eski, yeni)
    return metin


def main():
    config = get_game_config()
    anahtarlar = _bolum_anahtarlari(config)
    elle = {}
    yol = os.path.join(KOK, "ceviri", "tr.json")
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            elle = json.load(f).get("ceviriler", {})

    ceviri = {}
    bekleyen = []
    for anahtar, _bolum, metin, _yol in anahtarlar:
        if anahtar in elle or not metin.strip():
            continue
        ceviri[anahtar] = metin
        bekleyen.append((anahtar, metin))

    print(f"[+] {len(bekleyen)} metin çevrilecek ({len(elle)} elle çeviri korunuyor)")
    basarili = 0
    hatali = 0
    adim = 25
    for i in range(0, len(bekleyen), adim):
        grup = bekleyen[i:i + adim]
        metinler = [m for _, m in grup]
        try:
            sonuc = cevir(metinler)
        except Exception as hata:
            print(f" ! Grup {i} çevrilemedi: {hata}")
            time.sleep(3)
            sonuc = metinler
        if len(sonuc) != len(metinler):
            print(f" ! Grup {i}: satır sayısı uyuşmadı ({len(sonuc)}/{len(metinler)}), tek tek")
            sonuc = []
            for m in metinler:
                try:
                    parca = cevir([m])
                    sonuc.append(parca[0] if parca else m)
                except Exception:
                    sonuc.append(m)
                time.sleep(0.1)
        for (anahtar, ozgun), cev in zip(grup, sonuc):
            cev = duzelt(cev.strip())
            if not cev or dogrula(ozgun, cev):
                # Yer tutucu/HTML bozulduysa İngilizce bırak.
                ceviri.pop(anahtar, None)
                hatali += 1
                continue
            ceviri[anahtar] = cev
            basarili += 1
        print(f" * {min(i + adim, len(bekleyen))}/{len(bekleyen)} (ok: {basarili}, atlanan: {hatali})")
        time.sleep(0.2)

    hedef = os.path.join(KOK, "ceviri", "oto_tr.json")
    with open(hedef, "w", encoding="utf-8") as f:
        json.dump({"dil": "tr", "ceviriler": ceviri}, f, ensure_ascii=False, indent=1)
    print(f"[+] {len(ceviri)} çeviri {hedef} dosyasına yazıldı")


if __name__ == "__main__":
    main()
