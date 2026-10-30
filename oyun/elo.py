"""Haftalık turnuva: Elo reytingi ve hafta sonu ödülleri.

Orijinal oyunda haftalık turnuva pazartesiden pazara sürer; haftanın
sonunda ilk 10 ödül alır, büyük ödül Yanardağ Ejderhası'dır. Ödül hafta
bitince ödenir, her odayı kapatınca değil; yoksa haftanın ilk oyuncusu
birinciliği kapar. Hafta Türkiye saatiyle pazartesi 00.00'da kapanır ve ödül
bir sonraki istekte yazılır.

Sıralama Elo ile: haftada 3 maç Glicko-2'nin istediği 10-15 maç için az.
E_A = 1 / (1 + 10^((R_B - R_A)/400)),  R_A' = R_A + K (S_A - E_A)
K ilk 20 maçta 32, sonra 16. Botların reytingi ordu gücünden sabit hesaplanır
ve hiç değişmez; bot maçları yarım K ile sayılır, yoksa oyuncular botları
sömürerek reyting kasabilir. Maç puanı (0-100) sonuca çevrilir: S = puan / 100.
"""

import hashlib
import json
import math
import os
import threading
from datetime import datetime, timedelta

from oyun.yollar import SAVES_DIR

BASLANGIC = 1500.0
HAFTALIK_MAC = 3
ODULLU_SIRA = 10
# Sıra -> (eşya, adet): Yanardağ Ejderhası, Ejder Yavrusu, Süper Şövalye
ODULLER = {1: (847, 1), 2: (849, 1), 3: (849, 1)}
KALAN_ODUL = (9101, 1)

KILIT = threading.RLock()


def beklenen(ra, rb):
    return 1 / (1 + 10 ** ((rb - ra) / 400))


def k_katsayisi(mac_sayisi, bot):
    k = 32 if mac_sayisi < 20 else 16
    return k / 2 if bot else k


def guncelle(ra, rb, s, mac_sayisi, bot=False):
    """Oyuncunun yeni reytingi."""
    return ra + k_katsayisi(mac_sayisi, bot) * (s - beklenen(ra, rb))


def bot_reytingi(ordu_gucu):
    """Ordu gücünden sabit reyting (800-2400)."""
    return max(800.0, min(2400.0, 1000 + 120 * math.log2(1 + max(0.0, ordu_gucu) / 50)))


def hafta(simdi):
    """`simdi` (Türkiye saati) hangi haftada: o haftanın pazartesisi (ISO tarih)."""
    gun = simdi.date()
    return (gun - timedelta(days=gun.weekday())).isoformat()


# ---------------------------------------------------------------------------
# Haftalık tablo (saves/haftalik_turnuva.json)
# ---------------------------------------------------------------------------

def _dosya():
    return os.path.join(SAVES_DIR, "haftalik_turnuva.json")


def _oku():
    try:
        with open(_dosya(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"hafta": None, "oyuncular": {}, "gecmis": []}


def _yaz(veri):
    os.makedirs(SAVES_DIR, exist_ok=True)
    gecici = _dosya() + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    os.replace(gecici, _dosya())


def _bot_puani(hafta_id, uid, reyting):
    """Botun o haftaki 3 maçlık puanı: reytingine bağlı, haftaya göre sabit."""
    toplam = 0.0
    for mac in range(HAFTALIK_MAC):
        h = hashlib.sha256(f"{hafta_id}:{uid}:{mac}".encode()).digest()
        sans = int.from_bytes(h[:4], "big") / 2 ** 32
        toplam += 100 * min(1.0, max(0.0, beklenen(reyting, BASLANGIC) * 0.8 + sans * 0.4))
    return round(toplam, 2)


def siralama(veri, botlar):
    """Haftanın sırası: gerçek oyuncular ve botlar. `botlar`: {uid: (ad, reyting)}."""
    tablo = [{"id": uid, "ad": o["ad"], "puan": round(o["puan"], 2), "mac": o["mac"], "bot": False}
             for uid, o in veri["oyuncular"].items()]
    tablo += [{"id": uid, "ad": ad, "puan": _bot_puani(veri["hafta"], uid, r), "mac": HAFTALIK_MAC, "bot": True}
              for uid, (ad, r) in botlar.items()]
    tablo.sort(key=lambda o: (-o["puan"], o["bot"], o["id"]))
    for i, o in enumerate(tablo, 1):
        o["sira"] = i
    return tablo


def haftayi_kapat(simdi, botlar, odul_ver):
    """Hafta değiştiyse geçen haftayı kapatır ve ilk 10'daki oyunculara ödül verir.

    `odul_ver(uid, esya, adet)`. Kapanan haftanın sırası döner (yoksa None).
    """
    with KILIT:
        veri = _oku()
        simdiki = hafta(simdi)
        if veri["hafta"] == simdiki:
            return None
        kapanan = None
        if veri["hafta"] and veri["oyuncular"]:
            kapanan = siralama(veri, botlar)
            for o in kapanan[:ODULLU_SIRA]:
                if not o["bot"]:
                    odul_ver(o["id"], *ODULLER.get(o["sira"], KALAN_ODUL))
            veri["gecmis"] = (veri.get("gecmis", []) + [{"hafta": veri["hafta"], "ilk": kapanan[:ODULLU_SIRA]}])[-8:]
        veri["hafta"] = simdiki
        veri["oyuncular"] = {}
        _yaz(veri)
        return kapanan


def mac_kaydet(uid, ad, puan, simdi):
    """Oyuncunun haftalık tablosuna bir maç ekler (haftada ilk 3 maç sayılır)."""
    with KILIT:
        veri = _oku()
        if veri["hafta"] != hafta(simdi):
            return False
        o = veri["oyuncular"].setdefault(uid, {"ad": ad, "puan": 0.0, "mac": 0})
        if o["mac"] >= HAFTALIK_MAC:
            return False
        o["puan"] += max(0.0, min(100.0, float(puan)))
        o["mac"] += 1
        o["ad"] = ad
        _yaz(veri)
        return True


def tablo(botlar):
    with KILIT:
        return siralama(_oku(), botlar)


def turkiye_saati():
    from oyun.takvim import TURKIYE
    return datetime.now(TURKIYE)
