# -*- coding: utf-8 -*-
"""
Social Emperors Türkçe çeviri motoru.

Oyunun arayüz metinleri sunucunun gönderdiği `config/game_config_*.json`
dosyasındaki `localization_strings` listesinden ve eşya/görev/seviye
kayıtlarından geliyor. Bu modül, oyun dosyalarına dokunmadan, sunucunun
gönderdiği config'i kopyalayıp Türkçe metinlerle değiştirir.

Kullanım:
    from turkce import turkce_uygula
    config = turkce_uygula(get_game_config())
"""

import copy
import json
import os
import re

KOK = os.path.dirname(os.path.abspath(__file__))
TR_DOSYASI = os.path.join(KOK, "ceviri", "tr.json")

# Çeviri sırasında korunması gereken yer tutucular: #0#, #1# ...
YER_TUTUCU = re.compile(r"#\d+#")
ETIKET = re.compile(r"<[^>]+>")


def cevirileri_yukle(yol=TR_DOSYASI):
    """tr.json dosyasını okur; dosya yoksa boş sözlük döner."""
    if not os.path.exists(yol):
        return {}
    with open(yol, "r", encoding="utf-8") as f:
        veri = json.load(f)
    return veri.get("ceviriler", veri)


def _bolum_anahtarlari(config):
    """Config içindeki tüm çevrilebilir metinleri (anahtar, bölüm, metin, yol) olarak üretir."""
    kayitlar = []

    # 1) Arayüz / görev / ipucu metinleri
    adet = {}
    for e in config.get("localization_strings", []):
        if not isinstance(e, dict):
            continue
        ad = e.get("name", "")
        adet[ad] = adet.get(ad, 0) + 1
    gorulen = {}
    for i, e in enumerate(config.get("localization_strings", [])):
        if not isinstance(e, dict):
            continue
        ad = e.get("name", "")
        anahtar = "loc:" + ad
        if adet.get(ad, 0) > 1:  # aynı isim birden fazla kez geçiyorsa ayırt et
            gorulen[ad] = gorulen.get(ad, 0) + 1
            anahtar = f"loc:{ad}#{gorulen[ad]}"
        kayitlar.append((anahtar, "arayuz", e.get("text", ""),
                         ("localization_strings", i, "text")))

    # 2) Eşyalar (binalar, birimler, büyüler...)
    for i, e in enumerate(config.get("items", [])):
        if e.get("name"):
            kayitlar.append((f"item:{e.get('id')}", "esya", e["name"],
                             ("items", i, "name")))

    # 3) Görevler
    for i, m in enumerate(config.get("missions", [])):
        for alan, etiket in (("title", "baslik"), ("description", "aciklama")):
            if m.get(alan):
                kayitlar.append((f"mission:{m.get('id')}:{etiket}", "gorev",
                                 m[alan], ("missions", i, alan)))

    # 4) Kategoriler
    for cid, c in config.get("categories", {}).items():
        if isinstance(c, dict):
            if c.get("name"):
                kayitlar.append((f"category:{cid}", "kategori", c["name"],
                                 ("categories", cid, "name")))
            for s in c.get("sub", []):
                if s.get("name"):
                    kayitlar.append((f"subcategory:{s.get('id')}", "kategori",
                                     s["name"], ("categories", cid, "sub",
                                                 c["sub"].index(s), "name")))

    # 5) Seviye adları
    for i, l in enumerate(config.get("levels", [])):
        if l.get("name"):
            kayitlar.append((f"level:{i}", "seviye", l["name"],
                             ("levels", i, "name")))

    # 6) Komşu yardımı metinleri
    for i, a in enumerate(config.get("neighbor_assists", [])):
        for alan in ("task", "action", "notification"):
            if a.get(alan):
                kayitlar.append((f"assist:{i}:{alan}", "komsu", a[alan],
                                 ("neighbor_assists", i, alan)))

    return kayitlar


def _yola_yaz(veri, yol, deger):
    hedef = veri
    for parca in yol[:-1]:
        hedef = hedef[parca]
    hedef[yol[-1]] = deger


def dogrula(kaynak, ceviri):
    """Çeviride yer tutucu / HTML etiketi kaybı var mı diye bakar."""
    sorunlar = []
    if len(YER_TUTUCU.findall(kaynak)) != len(YER_TUTUCU.findall(ceviri)):
        sorunlar.append("yer tutucu sayısı farklı (#0# gibi)")
    if sorted(ETIKET.findall(kaynak)) != sorted(ETIKET.findall(ceviri)):
        sorunlar.append("HTML etiketleri birebir korunmamış")
    if kaynak.count("\n") != ceviri.count("\n"):
        sorunlar.append("satır sonu sayısı farklı")
    return sorunlar


def turkce_uygula(config, ceviriler=None):
    """Config'in Türkçeleştirilmiş bir kopyasını döndürür; özgün config değişmez."""
    if ceviriler is None:
        ceviriler = cevirileri_yukle()
    yeni = copy.deepcopy(config)
    for anahtar, _bolum, metin, yol in _bolum_anahtarlari(yeni):
        if anahtar in ceviriler:
            _yola_yaz(yeni, yol, ceviriler[anahtar])
    return yeni


def kapsam(config, ceviriler=None):
    """Bölüm bazında çeviri kapsamını (çevrilen / toplam) hesaplar."""
    if ceviriler is None:
        ceviriler = cevirileri_yukle()
    rapor = {}
    for anahtar, bolum, metin, _yol in _bolum_anahtarlari(config):
        r = rapor.setdefault(bolum, {"toplam": 0, "cevrilen": 0})
        r["toplam"] += 1
        if anahtar in ceviriler:
            r["cevrilen"] += 1
    return rapor
