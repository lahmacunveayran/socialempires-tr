# -*- coding: utf-8 -*-
"""Bot köyleri için gerçek (AI üretilmemiş) portre/resim indirir.

Kaynak: Wikipedia / Wikimedia Commons (kamuya açık veya özgür lisanslı
görseller). İndirilen dosyalar `templates/img/profile/bot_<ad>.<uzantı>`
olarak kaydedilir ve ilgili bot kaydının `playerInfo.pic` alanı güncellenir.

Kullanım:
    python tools\\bot_pp_uret.py
"""

import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from bundle import SAVES_DIR  # noqa: E402

PP_KLASOR = os.path.join(KOK, "templates", "img", "profile")
UA = {"User-Agent": "SocialEmperorsLocal/1.0 (single-player preservation; contact: local)"}

# Bot adı -> Wikipedia başlığı
WIKI = {
    "Kara Han": "Kara-Khanid Khanate",
    "Bozkurt Bey": None,
    "Demir Yay": None,
    "Gökbörü": None,
    "Alp Er Tunga": "Alp Er Tunga",
    "Kül Tigin": "Kul Tigin",
    "Bilge Kağan": "Bilge Khagan",
    "Tomris Hatun": "Tomyris",
    "Modu Han": "Modu Chanyu",
    "Attila": "Attila",
    "Balamir": "Balamber",
    "İlteriş": "Ilterish Qaghan",
    "Kapgan": "Qapaghan Qaghan",
    "Suyab": "Suyab",
    "Tardu": "Tardu",
    "Bayan Kağan": "Bayan I",
    "İstemi Yabgu": "Istämi",
    "Bilge Hatun": None,
    "Kür Şad": None,
    "Tonyukuk": "Tonyukuk",
    "Vezir Nizam": "Nizam al-Mulk",
    "Şahin Bey": None,
    "Korkut Ata": "Korkut Ata",
    "Dede Korkut": "Book of Dede Korkut",
    "Manas": "Manas (epic)",
    "Cengiz Han": "Genghis Khan",
    "Kubilay": "Kublai Khan",
    "Timur": "Timur",
    "Babür": "Babur",
    "Alparslan": "Alp Arslan",
    "Tuğrul Bey": "Tughril",
    "Melikşah": "Malik-Shah I",
    "Sultan Sencer": "Ahmad Sanjar",
    "Harzemşah": "Muhammad II of Khwarazm",
    "Celaleddin": "Jalal ad-Din Mingburnu",
    "Ertuğrul": "Ertuğrul",
    "Osman Bey": "Osman I",
    "Orhan Bey": "Orhan",
    "Murat Bey": "Murad I",
    "Yıldırım": "Bayezid I",
    "Fatih": "Mehmed the Conqueror",
    "Yavuz": "Selim I",
    "Kanuni": "Suleiman the Magnificent",
    "Sokullu": "Sokollu Mehmed Pasha",
    "Kılıç Arslan": "Kilij Arslan II",
    "Nurettin": "Nur ad-Din Zengi",
    "Selahaddin": "Saladin",
    "Baybars": "Baibars",
    "Kutuz": "Qutuz",
    "Berke Han": "Berke",
}

# Özel Commons aramaları (portre bulunamayanlar için)
OZEL = {
    "Alp Er Tunga": "Scythian warrior gold",
    "Kapgan": "Göktürk khagan",
    "Tomris Hatun": "Tomyris",
    "Kül Tigin": "Kul Tigin inscription",
    "Tonyukuk": "Tonyukuk inscription",
    "Şahin Bey": "Şahin Bey Antep",
    "Balamir": "Balamber",
    "Korkut Ata": "Korkut Ata statue",
}

# Wikipedia'da resim yoksa Commons araması için temalar
TEMALAR = [
    "Turkic warrior painting",
    "Ottoman miniature soldier",
    "Mongol horseman painting",
    "Seljuk warrior miniature",
    "Hun warrior painting",
    "Central Asian horseman painting",
]


def slug(ad: str) -> str:
    ad = ad.replace("ı", "i").replace("İ", "I").replace("ş", "s").replace("Ş", "S")
    ad = ad.replace("ğ", "g").replace("Ğ", "G").replace("ü", "u").replace("Ü", "U")
    ad = ad.replace("ö", "o").replace("Ö", "O").replace("ç", "c").replace("Ç", "C")
    ad = unicodedata.normalize("NFKD", ad).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ad.lower()).strip("_")


def _json(url):
    istek = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(istek, timeout=25) as cevap:
        return json.loads(cevap.read().decode("utf-8"))


def wiki_resim(baslik):
    if not baslik:
        return None
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(baslik.replace(" ", "_"))
    try:
        d = _json(url)
    except Exception:
        return None
    for anahtar in ("originalimage", "thumbnail"):
        kaynak = d.get(anahtar) or {}
        if kaynak.get("source"):
            return kaynak["source"]
    return None


def commons_resim(sorgu, kullanilan):
    parametreler = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": sorgu, "gsrnamespace": "6", "gsrlimit": "10",
        "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": "400",
    })
    try:
        d = _json("https://commons.wikimedia.org/w/api.php?" + parametreler)
    except Exception:
        return None
    for sayfa in (d.get("query", {}).get("pages", {}) or {}).values():
        for ii in sayfa.get("imageinfo", []):
            mime = ii.get("mime", "")
            if mime not in ("image/jpeg", "image/png"):
                continue
            kaynak = ii.get("thumburl") or ii.get("url")
            if kaynak and kaynak not in kullanilan:
                return kaynak
    return None


def indir(ad, kullanilan):
    adaylar = []
    w = WIKI.get(ad)
    if w:
        adaylar.append(wiki_resim(w))
    if ad in OZEL:
        adaylar.append(commons_resim(OZEL[ad], kullanilan))
    adaylar.append(commons_resim(f"{ad} portrait", kullanilan))
    for tema in TEMALAR:
        adaylar.append(commons_resim(tema, kullanilan))
    for url in adaylar:
        if not url or url in kullanilan:
            continue
        try:
            istek = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(istek, timeout=30) as cevap:
                veri = cevap.read()
        except Exception:
            continue
        if veri.startswith(b"\xff\xd8"):
            uzanti = ".jpg"
        elif veri.startswith(b"\x89PNG"):
            uzanti = ".png"
        else:
            continue
        if len(veri) < 2000:
            continue
        hedef = os.path.join(PP_KLASOR, f"bot_{slug(ad)}{uzanti}")
        with open(hedef, "wb") as f:
            f.write(veri)
        kullanilan.add(url)
        return hedef, url
    return None, None


def mevcut_pp(ad):
    for uzanti in (".jpg", ".png"):
        yol = os.path.join(PP_KLASOR, f"bot_{slug(ad)}{uzanti}")
        if os.path.exists(yol):
            return f"/img/profile/bot_{slug(ad)}{uzanti}"
    return None


def main():
    os.makedirs(PP_KLASOR, exist_ok=True)
    kullanilan = set()
    kaynaklar = []
    botlar = []
    for dosya in os.listdir(SAVES_DIR):
        if not dosya.endswith(".save.json"):
            continue
        yol = os.path.join(SAVES_DIR, dosya)
        try:
            with open(yol, encoding="utf-8") as f:
                kayit = json.load(f)
        except (ValueError, OSError):
            continue
        pi = kayit.get("playerInfo", {})
        if pi.get("bot"):
            botlar.append((yol, kayit))

    print(f"[+] {len(botlar)} bot için profil resmi hazırlanıyor")
    for yol, kayit in botlar:
        ad = kayit["playerInfo"].get("name", "Bot")
        mevcut = mevcut_pp(ad)
        if mevcut:
            kayit["playerInfo"]["pic"] = mevcut
            print(f" * {ad:<15} mevcut -> {mevcut}")
        else:
            hedef, kaynak = indir(ad, kullanilan)
            if hedef:
                kayit["playerInfo"]["pic"] = f"/img/profile/{os.path.basename(hedef)}"
                kaynaklar.append((ad, kaynak))
                print(f" * {ad:<15} indirildi -> {os.path.basename(hedef)}")
            else:
                print(f" ! {ad:<15} resim bulunamadi (varsayilan kalacak)")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(kayit, f, indent=4, ensure_ascii=False)

    if kaynaklar:
        satirlar = ["# Bot profil resimleri", "",
                    "Kaynak: Wikimedia Commons / Wikipedia (özgür lisanslı görseller).", ""]
        for ad, url in kaynaklar:
            satirlar.append(f"- **{ad}** — <{url}>")
        with open(os.path.join(KOK, "docs", "RESIM_KAYNAKLARI.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar) + "\n")
        print(f"[+] {len(kaynaklar)} kaynak docs/RESIM_KAYNAKLARI.md dosyasina yazildi")


if __name__ == "__main__":
    main()
