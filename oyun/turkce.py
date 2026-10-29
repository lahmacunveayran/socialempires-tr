# -*- coding: utf-8 -*-
"""
Social Emperors Türkçe çeviri motoru.

Oyunun arayüz metinleri sunucunun gönderdiği `config/game_config_*.json`
dosyasındaki `localization_strings` listesinden ve eşya/görev/seviye
kayıtlarından geliyor. Bu modül, oyun dosyalarına dokunmadan, sunucunun
gönderdiği config'i kopyalayıp Türkçe metinlerle değiştirir.

Kullanım:
    from oyun.turkce import turkce_uygula
    config = turkce_uygula(get_game_config())
"""

import copy
import json
import os
import re

from oyun.yollar import CEVIRI_DIR

TR_DOSYASI = os.path.join(CEVIRI_DIR, "tr.json")

# Çeviri sırasında korunması gereken yer tutucular: #0#, #1# ...
YER_TUTUCU = re.compile(r"#\d+#")
ETIKET = re.compile(r"<[^>]+>")


def cevirileri_yukle(yol=TR_DOSYASI):
    """Otomatik çevirileri ve elle yazılan tr.json'u birleştirir.

    Elle yazılan çeviri her zaman otomatiği ezer.
    """
    sonuc = {}
    oto = os.path.join(os.path.dirname(yol), "oto_tr.json")
    for dosya in (oto, yol):
        if not os.path.exists(dosya):
            continue
        with open(dosya, "r", encoding="utf-8") as f:
            veri = json.load(f)
        sonuc.update(veri.get("ceviriler", veri))
    return sonuc


def _bolum_anahtarlari(config):
    """Config içindeki tüm çevrilebilir metinleri (anahtar, bölüm, metin, yol) olarak üretir."""
    kayitlar = []

    # 1) Arayüz / görev / ipucu metinleri
    # Patch'ler bazı kayıtları liste içine liste olarak ekliyor; düzleştir.
    duz = []
    for i, ham in enumerate(config.get("localization_strings", [])):
        if isinstance(ham, dict):
            duz.append((i, None, ham))
        elif isinstance(ham, list):
            for j, alt in enumerate(ham):
                if isinstance(alt, dict):
                    duz.append((i, j, alt))

    adet = {}
    for _i, _j, e in duz:
        adet[e.get("name", "")] = adet.get(e.get("name", ""), 0) + 1
    gorulen = {}
    for i, j, e in duz:
        ad = e.get("name", "")
        anahtar = "loc:" + ad
        if adet.get(ad, 0) > 1:  # aynı isim birden fazla kez geçiyorsa ayırt et
            gorulen[ad] = gorulen.get(ad, 0) + 1
            anahtar = f"loc:{ad}#{gorulen[ad]}"
        yol = ("localization_strings", i, "text") if j is None else ("localization_strings", i, j, "text")
        kayitlar.append((anahtar, "arayuz", e.get("text", ""), yol))

    # 2) Eşyalar (binalar, birimler, büyüler...)
    for i, e in enumerate(config.get("items", [])):
        if not isinstance(e, dict):
            continue
        if e.get("name"):
            kayitlar.append((f"item:{e.get('id')}", "esya", e["name"],
                             ("items", i, "name")))
        if e.get("achievement_desc"):
            kayitlar.append((f"item:{e.get('id')}:basarim", "esya",
                             e["achievement_desc"], ("items", i, "achievement_desc")))

    # 3) Görevler
    for i, m in enumerate(config.get("missions", [])):
        if not isinstance(m, dict):
            continue
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
            for j, s in enumerate(c.get("sub", [])):
                if isinstance(s, dict) and s.get("name"):
                    kayitlar.append((f"subcategory:{s.get('id')}", "kategori",
                                     s["name"], ("categories", cid, "sub", j, "name")))

    # 5) Seviye adları
    for i, l in enumerate(config.get("levels", [])):
        if isinstance(l, dict) and l.get("name"):
            kayitlar.append((f"level:{i}", "seviye", l["name"],
                             ("levels", i, "name")))

    # 6) Komşu yardımı metinleri
    for i, a in enumerate(config.get("neighbor_assists", [])):
        if not isinstance(a, dict):
            continue
        for alan in ("task", "action", "notification"):
            if a.get(alan):
                kayitlar.append((f"assist:{i}:{alan}", "komsu", a[alan],
                                 ("neighbor_assists", i, alan)))

    # 7) Keşfedilebilir eşyalar
    for i, f in enumerate(config.get("findable_items", [])):
        if not isinstance(f, dict):
            continue
        for alan, etiket in (("title", "baslik"), ("description", "aciklama")):
            if f.get(alan):
                kayitlar.append((f"findable:{f.get('id')}:{etiket}", "kesif",
                                 f[alan], ("findable_items", i, alan)))

    # 8) Seviye atlama ipuçları
    for i, t in enumerate(config.get("level_up_tips", [])):
        if isinstance(t, dict) and t.get("text"):
            kayitlar.append((f"tip:{i}", "ipucu", t["text"],
                             ("level_up_tips", i, "text")))

    # 9) Sosyal bina işçi adları
    for i, s in enumerate(config.get("social_items", [])):
        if isinstance(s, dict) and s.get("workers"):
            kayitlar.append((f"social:{s.get('id')}:workers", "sosyal",
                             s["workers"], ("social_items", i, "workers")))

    return kayitlar


def _yola_yaz(veri, yol, deger):
    hedef = veri
    for parca in yol[:-1]:
        hedef = hedef[parca]
    hedef[yol[-1]] = deger


TR_ASCII = str.maketrans({
    "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "İ": "I", "ı": "i",
    "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
})


def ascii_uygula(config):
    """Flash istemcisinin fontunda Türkçe harfler yoksa okunabilir ASCII üretir."""
    yeni = copy.deepcopy(config)
    for _anahtar, _bolum, metin, yol in _bolum_anahtarlari(yeni):
        if isinstance(metin, str):
            _yola_yaz(yeni, yol, metin.translate(TR_ASCII))
    return yeni


def dogrula(kaynak, ceviri):
    """Çeviride yer tutucu / HTML etiketi kaybı var mı diye bakar."""
    sorunlar = []
    if sorted(YER_TUTUCU.findall(kaynak)) != sorted(YER_TUTUCU.findall(ceviri)):
        sorunlar.append("yer tutucular birebir korunmamış (#0# gibi)")
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
            ceviri = ceviriler[anahtar]
            if dogrula(metin, ceviri):
                continue  # bozuk çeviriyi gönderme; İngilizce kalsın
            _yola_yaz(yeni, yol, ceviri)
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
