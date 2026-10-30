"""Etkinlik takvimi: bayram tarihleri ve tema setlerinin açıldığı günler.

Bayram tarihleri gözle değil hesapla belirlenir. Diyanet 2016 Uluslararası
Hicri Takvim Birliği Kongresi ölçütünü uygular (dünyanın herhangi bir
yerinde, 00.00 GMT'den önce gün batımında Ay'ın Güneş'ten açıklığı en az 8°
ve ufuktan yüksekliği en az 5° ise yeni ay başlar). 2030'a kadar tarihler
Diyanet'in resmî tablosundan sabit yazılır. Sonrası için kuruluysa
`hijridate` kitaplığı (Ümmü'l-Kurâ) kullanılır; ayarlar.json'daki
"bayram_duzeltme" ile elle düzeltilebilir: {"2031-ramazan": "2031-01-24"}.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone

from oyun import ayarlar
from oyun.yollar import CONFIG_DIR

TURKIYE = timezone(timedelta(hours=3))  # 2016'dan beri sürekli UTC+3

# Diyanet: bayramın ilk günü (Ramazan 3 gün, Kurban 4 gün)
RAMAZAN = {2026: (3, 20), 2027: (3, 9), 2028: (2, 26), 2029: (2, 14), 2030: (2, 4)}
KURBAN = {2026: (5, 27), 2027: (5, 16), 2028: (5, 5), 2029: (4, 24), 2030: (4, 13)}
HICRI_AY = {"ramazan": (10, 1), "kurban": (12, 10)}  # 1 Şevval, 10 Zilhicce

_takvim = None


def bugun():
    return datetime.now(TURKIYE).date()


def _hijridate_ile(yil, tur):
    try:
        from hijridate import Hijri
    except ImportError:
        return None
    ay, gun = HICRI_AY[tur]
    # Bir miladi yıl iki hicri yıla denk gelir; o yıla düşeni seç.
    tahmin = int((yil - 622) * 33 / 32)
    for hicri_yil in (tahmin, tahmin + 1, tahmin + 2):
        try:
            g = Hijri(hicri_yil, ay, gun).to_gregorian()
        except (OverflowError, ValueError):
            continue
        if g.year == yil:
            return date(g.year, g.month, g.day)
    return None


def bayram(yil, tur):
    """`tur`: "ramazan" ya da "kurban". O yılki bayramın ilk günü (bilinmiyorsa None)."""
    duzeltme = (ayarlar.oku().get("bayram_duzeltme") or {}).get(f"{yil}-{tur}")
    if duzeltme:
        return date.fromisoformat(duzeltme)
    tablo = RAMAZAN if tur == "ramazan" else KURBAN
    if yil in tablo:
        return date(yil, *tablo[yil])
    return _hijridate_ile(yil, tur)


def _yukle():
    global _takvim
    if _takvim is None:
        try:
            with open(os.path.join(CONFIG_DIR, "takvim.json"), encoding="utf-8") as f:
                _takvim = json.load(f)
        except (OSError, ValueError):
            _takvim = {"her_zaman": ["Harikalar"], "etkinlikler": []}
    return _takvim


def _aralik(etkinlik, yil):
    gun = etkinlik["gun"]
    if gun in HICRI_AY:
        merkez = bayram(yil, gun)
        if merkez is None:
            return None
    else:
        ay, g = (int(x) for x in gun.split("-"))
        merkez = date(yil, ay, g)
    baslangic = merkez - timedelta(days=int(etkinlik.get("once", 0)))
    return baslangic, baslangic + timedelta(days=int(etkinlik.get("sure", 1)))


def etkinlikler(gun=None, ileri=60):
    """`gun`de süren ve `ileri` gün içinde başlayacak etkinlikler."""
    gun = gun or bugun()
    sonuc = []
    for etkinlik in _yukle()["etkinlikler"]:
        for yil in (gun.year - 1, gun.year, gun.year + 1):
            aralik = _aralik(etkinlik, yil)
            if aralik is None:
                continue
            baslangic, bitis = aralik  # bitis dahil değil
            if bitis <= gun or (baslangic - gun).days > ileri:
                continue
            sonuc.append({"ad": etkinlik["ad"], "simge": etkinlik.get("simge", "📜"), "setler": list(etkinlik.get("setler", [])),
                          "baslangic": baslangic.isoformat(), "bitis": bitis.isoformat(),
                          "son_gun": (bitis - timedelta(days=1)).isoformat(),
                          "aktif": baslangic <= gun < bitis})
    sonuc.sort(key=lambda e: e["baslangic"])
    return sonuc


def acik_setler(gun=None):
    """Mağazada açık olacak tema setlerinin adları."""
    acik = set(_yukle().get("her_zaman", []))
    for e in etkinlikler(gun, ileri=0):
        if e["aktif"]:
            acik.update(e["setler"])
    return sorted(acik)
