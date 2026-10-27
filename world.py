# -*- coding: utf-8 -*-
"""Yaşayan dünya: bot köyleri kendi ekonomilerini işletir, birbirine ve
oyuncuya akın düzenler.

Sunucu açılırken `dunya.baslat()` çağrılır; arka planda `tick_saniye`
aralığıyla çalışır. Tüm değişiklikler `save_lock` altında yapılır ve
normal kayıt dosyalarına yazılır; istemci tarafında ek bir şey gerekmez.

Ayar dosyası: `dunya.json`
"""

import json
import math
import os
import random
import threading
import time

from bundle import SAVES_DIR
from get_game_config import get_game_config
from sessions import all_saves_userid, save_lock, save_session, session

AYAR_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dunya.json")

VARSAYILAN_AYAR = {
    "aktif": True,
    "tick_saniye": 90,
    "saldiri_olasiligi": 0.45,
    "oyuncuya_saldiri": 0.15,
    "olay_saklama": 200,
}


def ayarlari_yukle():
    ayar = dict(VARSAYILAN_AYAR)
    if os.path.exists(AYAR_DOSYASI):
        try:
            with open(AYAR_DOSYASI, encoding="utf-8-sig") as f:
                ayar.update(json.load(f))
        except (ValueError, OSError) as hata:
            print(f" ! dunya.json okunamadi ({hata}); varsayilan ayarlar")
    return ayar


# ---------------------------------------------------------------------------
# Yardımcılar (test edilebilir saf fonksiyonlar)
# ---------------------------------------------------------------------------

def birim_sayilari(save):
    """Haritadaki birimleri {birim_id: adet} olarak döndürür."""
    sayilar = {}
    for esya in save.get("maps", [{}])[0].get("items", []):
        try:
            esya_id = int(esya[0])
        except (TypeError, ValueError, IndexError):
            continue
        item = get_game_config()["items"]
        # config'te tür bilgisi; pahalı olmasın diye önbellek kullanılır
        tur = _ITEM_TURU.get(esya_id)
        if tur is None:
            tur = _tur_bul(esya_id)
        if tur == "u":
            sayilar[esya_id] = sayilar.get(esya_id, 0) + 1
    return sayilar


_ITEM_TURU = {}
_ITEM_CACHE = {}


def _tur_bul(esya_id):
    for item in get_game_config()["items"]:
        if int(item["id"]) == int(esya_id):
            _ITEM_TURU[int(esya_id)] = item.get("type")
            return item.get("type")
    return None


def _item(esya_id):
    anahtar = int(esya_id)
    if anahtar in _ITEM_CACHE:
        return _ITEM_CACHE[anahtar]
    for item in get_game_config()["items"]:
        if int(item["id"]) == anahtar:
            _ITEM_CACHE[anahtar] = item
            return item
    _ITEM_CACHE[anahtar] = {}
    return {}


def ordu_gucu(sayilar):
    """Birim sayılarından yaklaşık savaş gücü."""
    guc = 0.0
    for esya_id, adet in sayilar.items():
        item = _item(esya_id)
        try:
            saldiri = float(item.get("attack") or 0)
            can = float(item.get("life") or 0)
        except (TypeError, ValueError):
            saldiri = can = 0
        guc += adet * (saldiri + can * 0.35)
    return guc


def kule_gucu(save):
    """Savunma binalarının (kule vb.) ek gücü."""
    guc = 0.0
    for esya in save.get("maps", [{}])[0].get("items", []):
        try:
            item = _item(int(esya[0]))
        except (TypeError, ValueError, IndexError):
            continue
        if item.get("type") == "b":
            try:
                saldiri = float(item.get("attack") or 0)
            except (TypeError, ValueError):
                saldiri = 0
            if saldiri > 0:
                guc += saldiri * 3
    return guc


def birim_sil(save, silinecek):
    """{id: adet} kadar birimi haritadan rastgele siler."""
    kalan = dict(silinecek)
    esyalar = save["maps"][0]["items"]
    for esya in list(esyalar):
        try:
            esya_id = int(esya[0])
        except (TypeError, ValueError, IndexError):
            continue
        if kalan.get(esya_id, 0) > 0 and _tur_bul(esya_id) == "u":
            esyalar.remove(esya)
            kalan[esya_id] -= 1
    return kalan


def kaynak_ekle(save, kaynak, miktar):
    harita = save["maps"][0]
    harita[kaynak] = int(harita.get(kaynak, 0)) + int(miktar)


def rapor_ekle(hedef, saldiran, veri):
    """Savunanın attacksReceived listesine rapor ekler."""
    ps = hedef.setdefault("privateState", {})
    liste = ps.get("attacksReceived")
    if not isinstance(liste, list):
        liste = []
        ps["attacksReceived"] = liste
    liste.append({
        "time": veri["time"],
        "attacker_id": str(saldiran.get("playerInfo", {}).get("pid", "")),
        "description": veri,
    })


# ---------------------------------------------------------------------------
# Dünya
# ---------------------------------------------------------------------------

class Dunya:
    def __init__(self):
        self.ayar = ayarlari_yukle()
        self.tick = 0
        self.olaylar = []
        self._duruyor = False
        self._is_parcacigi = None
        self._son_guncelleme = int(time.time())

    # -- erişim -----------------------------------------------------------
    def oyuncular(self):
        oyuncular = []
        for uid in all_saves_userid():
            kayit = session(uid)
            if not kayit:
                continue
            oyuncular.append((uid, kayit))
        return oyuncular

    def _botlar(self):
        return [(uid, k) for uid, k in self.oyuncular() if k.get("playerInfo", {}).get("bot")]

    # -- olay kaydı -------------------------------------------------------
    def olay(self, tur, metin):
        self.olaylar.append({"zaman": int(time.time()), "tur": tur, "metin": metin})
        fazla = len(self.olaylar) - int(self.ayar.get("olay_saklama", 200))
        if fazla > 0:
            del self.olaylar[:fazla]

    # -- tick -------------------------------------------------------------
    def tek_tick(self):
        if not self.ayar.get("aktif", True):
            return
        with save_lock:
            self.tick += 1
            degisen = set()
            botlar = self._botlar()
            for uid, kayit in botlar:
                if self._ekonomi(uid, kayit):
                    degisen.add(uid)
                if random.random() < float(self.ayar.get("saldiri_olasiligi", 0.45)):
                    hedef = self._akin(uid, kayit, botlar)
                    if hedef:
                        degisen.add(hedef)

            for uid in degisen:
                try:
                    save_session(uid)
                except OSError as hata:
                    print(f" ! Dunya kaydi yazilamadi ({uid}): {hata}")
            self._son_guncelleme = int(time.time())

    # -- ekonomi ----------------------------------------------------------
    def _ekonomi(self, uid, kayit):
        harita = kayit["maps"][0]
        seviye = max(1, int(harita.get("level", 1)))
        degisti = False

        for alan, taban in (("wood", 4), ("stone", 3), ("food", 4), ("coins", 3)):
            artis = int((taban + random.random() * taban) * seviye)
            harita[alan] = int(harita.get(alan, 0)) + artis
            degisti = True

        # Ara sıra yeni birim üret
        if random.random() < 0.35:
            birimler = [512, 516, 517, 518]
            secim = random.choice(birimler)
            item = _item(secim)
            maliyet = int(item.get("cost") or 0)
            if maliyet <= int(harita.get("coins", 0)) and len(kayit["maps"][0]["items"]) < 700:
                harita["coins"] = int(harita.get("coins", 0)) - maliyet
                from engine import timestamp_now
                kayit["maps"][0]["items"].append(
                    [secim, random.randint(38, 62), random.randint(38, 62), 0, timestamp_now(), 0, [], {}]
                )
                degisti = True

        # Seviye atlama
        seviyeler = get_game_config()["levels"]
        xp = int(harita.get("xp", 0))
        yeni = seviye
        while yeni + 1 < len(seviyeler) and xp >= int(seviyeler[yeni + 1]["exp_required"]):
            yeni += 1
        if yeni != seviye:
            harita["level"] = yeni
            self.olay("seviye", f"{kayit['playerInfo'].get('name', uid)} seviye {yeni} oldu")
            degisti = True
        return degisti

    # -- akın -------------------------------------------------------------
    def _akin(self, saldiran_id, saldiran, botlar):
        hedefler = [(u, k) for u, k in botlar if u != saldiran_id]
        oyuncu_hedefleri = [(u, k) for u, k in self.oyuncular() if not k.get("playerInfo", {}).get("bot")]
        if oyuncu_hedefleri and random.random() < float(self.ayar.get("oyuncuya_saldiri", 0.15)):
            hedefler += oyuncu_hedefleri
        if not hedefler:
            return None

        hedef_id, hedef = random.choice(hedefler)
        saldiran_birimler = birim_sayilari(saldiran)
        if sum(saldiran_birimler.values()) < 3:
            return None

        # Ordunun %60'ı saldırıya katılır
        giden = {i: max(1, int(n * 0.85)) for i, n in saldiran_birimler.items()}
        savunan_birimler = birim_sayilari(hedef)

        atak = ordu_gucu(giden) * random.uniform(0.9, 1.2) * 1.5
        savunan_guc = {i: max(1, int(n * 0.6)) for i, n in savunan_birimler.items()}
        savunma = ordu_gucu(savunan_guc) + kule_gucu(hedef) * 0.8 * random.uniform(0.9, 1.1)
        kazandi = atak > savunma

        # Kayıplar
        kayip_orani_saldiran = 0.2 if kazandi else 0.45
        kayip_orani_savunan = 0.45 if kazandi else 0.2
        saldiran_kayip = {i: max(0, int(n * kayip_orani_saldiran)) for i, n in giden.items()}
        savunan_kayip = {i: max(0, int(n * kayip_orani_savunan)) for i, n in savunan_birimler.items()}
        birim_sil(saldiran, saldiran_kayip)
        birim_sil(hedef, savunan_kayip)

        # Ganimet
        ganimet = {}
        if kazandi:
            for alan in ("coins", "wood", "stone", "food"):
                mevcut = int(hedef["maps"][0].get(alan, 0))
                alinacak = min(int(mevcut * 0.15), 200 * max(1, int(saldiran["maps"][0].get("level", 1))))
                if alinacak > 0:
                    hedef["maps"][0][alan] = mevcut - alinacak
                    saldiran["maps"][0][alan] = int(saldiran["maps"][0].get(alan, 0)) + alinacak
                    ganimet[alan] = alinacak

        # XP
        hedef_seviye = max(1, int(hedef["maps"][0].get("level", 1)))
        saldiran["maps"][0]["xp"] = int(saldiran["maps"][0].get("xp", 0)) + (max(1, hedef_seviye * 2) if kazandi else 1)
        if kazandi:
            hedef["maps"][0]["xp"] = int(hedef["maps"][0].get("xp", 0)) + 1

        # Raporlar (orijinal Social Empires rapor biçimi)
        from engine import timestamp_now
        simdi = timestamp_now()
        rapor = {
            "duration": random.randint(20, 90),
            "townhall_gold": 0,
            "win": 1 if kazandi else 0,
            "resources": {"x": max(1, hedef_seviye * 2) if kazandi else 0,
                          "g": ganimet.get("coins", 0)},
            "attacker_units": [[i, n, 0, 0] for i, n in giden.items()],
            "victim_units": [[i, n, 0, 0] for i, n in savunan_birimler.items()],
            "resources_victim": {k[0]: v for k, v in
                                  (("g", ganimet.get("coins", 0)), ("w", ganimet.get("wood", 0)),
                                   ("s", ganimet.get("stone", 0)), ("f", ganimet.get("food", 0))) if v},
            "voluntary_end": 0,
            "oponent": {
                "name": saldiran.get("playerInfo", {}).get("name", "Bot"),
                "user_id": str(saldiran_id),
                "world_id": 0,
                "level": int(saldiran["maps"][0].get("level", 1)),
                "pic": saldiran.get("playerInfo", {}).get("pic", ""),
            },
            "time": simdi,
        }
        rapor_ekle(hedef, saldiran, rapor)
        saldiran.setdefault("privateState", {}).setdefault("attacksSent", []).append(
            {"victim_id": str(hedef_id), "time": str(simdi)}
        )

        hedef_ad = hedef.get("playerInfo", {}).get("name", hedef_id)
        saldiran_ad = saldiran.get("playerInfo", {}).get("name", saldiran_id)
        if kazandi:
            toplam = sum(ganimet.values())
            self.olay("savas", f"{saldiran_ad} → {hedef_ad}: kazandı, {toplam} kaynak ganimet")
        else:
            self.olay("savas", f"{saldiran_ad} → {hedef_ad}: saldırı püskürtüldü")
        return hedef_id

    # -- döngü ------------------------------------------------------------
    def dongu(self):
        self._duruyor = False
        while not self._duruyor:
            try:
                time.sleep(max(5, int(self.ayar.get("tick_saniye", 90))))
                self.tek_tick()
            except Exception as hata:  # dünya döngüsü sunucuyu düşürmesin
                print(f" ! Dunya tick hatasi: {hata}")

    def baslat(self):
        if not self.ayar.get("aktif", True):
            print(" [+] Dunya simulasyonu kapali (dunya.json)")
            return
        self._is_parcacigi = threading.Thread(target=self.dongu, name="dunya", daemon=True)
        self._is_parcacigi.start()
        print(f" [+] Dunya simulasyonu basladi (tick: {self.ayar.get('tick_saniye')} sn)")

    def durdur(self):
        self._duruyor = True

    # -- panel verisi -----------------------------------------------------
    def veri(self):
        oyuncular = []
        for i, (uid, kayit) in enumerate(self.oyuncular()):
            harita = kayit["maps"][0]
            birimler = birim_sayilari(kayit)
            aci = i * 2.399963229728653
            yaricap = 40 + math.sqrt(i) * 95
            oyuncular.append({
                "id": str(uid),
                "ad": kayit.get("playerInfo", {}).get("name", "Oyuncu"),
                "bot": bool(kayit.get("playerInfo", {}).get("bot")),
                "seviye": int(harita.get("level", 1)),
                "xp": int(harita.get("xp", 0)),
                "kaynaklar": {k: int(harita.get(k, 0)) for k in ("coins", "wood", "stone", "food")},
                "birim": sum(birimler.values()),
                "konum": {
                    "x": round(400 + yaricap * math.cos(aci), 1),
                    "y": round(260 + yaricap * math.sin(aci) * 0.62, 1),
                },
            })
        return {
            "tick": self.tick,
            "guncelleme": self._son_guncelleme,
            "aktif": bool(self.ayar.get("aktif", True)),
            "oyuncular": oyuncular,
            "olaylar": list(reversed(self.olaylar[-40:])),
        }
