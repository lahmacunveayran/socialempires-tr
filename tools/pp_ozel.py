# -*- coding: utf-8 -*-
"""Belirli botların profil resimlerini özel görsellerle değiştirir."""

import io
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PP = os.path.join(KOK, "templates", "img", "profile")
SAVES = os.path.join(KOK, "saves")
UA = {"User-Agent": "SocialEmperorsLocal/1.0"}

# bot adı -> (tür, kaynak)
HEDEFLER = {
    "Manas": ("commons", "mountain landscape"),
    "Bozkurt Bey": ("wiki", ("en", "Fenerbahçe S.K. (football)")),
    "Gökbörü": ("wiki", ("en", "Galatasaray S.K. (football)")),
    "Demir Yay": ("wiki", ("en", "Beşiktaş J.K.")),
    "Kür Şad": ("wiki", ("tr", "Muş 1984 Muşspor")),
    "Alp Er Tunga": ("commons", "sports car"),
    "Bilge Hatun": ("commons", "nature forest"),
    "Balamir": ("commons", "classic car"),
}


def slug(ad):
    ad = ad.replace("ı", "i").replace("İ", "I").replace("ş", "s").replace("Ş", "S")
    ad = ad.replace("ğ", "g").replace("Ğ", "G").replace("ü", "u").replace("Ü", "U")
    ad = ad.replace("ö", "o").replace("Ö", "O").replace("ç", "c").replace("Ç", "C")
    ad = unicodedata.normalize("NFKD", ad).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ad.lower()).strip("_")


def _json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def wiki_resim(lang, baslik):
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(baslik.replace(" ", "_"))
    d = _json(url)
    for anahtar in ("thumbnail", "originalimage"):
        k = d.get(anahtar) or {}
        if k.get("source"):
            return k["source"]
    return None


def commons_resim(sorgu):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": sorgu, "gsrnamespace": "6", "gsrlimit": "10",
        "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": "500",
    })
    d = _json("https://commons.wikimedia.org/w/api.php?" + q)
    for sayfa in (d.get("query", {}).get("pages", {}) or {}).values():
        for ii in sayfa.get("imageinfo", []):
            if ii.get("mime") in ("image/jpeg", "image/png"):
                return ii.get("thumburl") or ii.get("url")
    return None


def indir(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def resmi_isle(veri, ad):
    im = Image.open(io.BytesIO(veri)).convert("RGBA")
    zemin = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(zemin, im).convert("RGB")
    w, h = im.size
    olcek = max(128 / w, 128 / h)
    im = im.resize((max(1, int(w * olcek)), max(1, int(h * olcek))), Image.LANCZOS)
    sol = (im.width - 128) // 2
    ust = (im.height - 128) // 2
    im = im.crop((sol, ust, sol + 128, ust + 128))
    yol = os.path.join(PP, "pp_" + slug(ad) + ".jpg")
    im.save(yol, "JPEG", quality=88, optimize=True)
    return yol


def main():
    os.makedirs(PP, exist_ok=True)
    kaynaklar = []
    for ad, (tur, kaynak) in HEDEFLER.items():
        try:
            if tur == "wiki":
                url = wiki_resim(kaynak[0], kaynak[1])
            else:
                url = commons_resim(kaynak)
            if not url:
                print(" !", ad, "görsel bulunamadı")
                continue
            yol = resmi_isle(indir(url), ad)
            print(" *", ad, "->", os.path.basename(yol))
            kaynaklar.append((ad, url))
            for dosya in os.listdir(SAVES):
                if not dosya.endswith(".save.json"):
                    continue
                p = os.path.join(SAVES, dosya)
                with open(p, encoding="utf-8") as f:
                    k = json.load(f)
                pi = k.get("playerInfo", {})
                if pi.get("bot") and pi.get("name") == ad:
                    pi["pic"] = "/img/profile/" + os.path.basename(yol)
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump(k, f, indent=4, ensure_ascii=False)
                    break
        except Exception as hata:
            print(" !", ad, hata)
    if kaynaklar:
        with open(os.path.join(KOK, "docs", "RESIM_KAYNAKLARI.md"), "a", encoding="utf-8") as f:
            f.write("\n## Özel profil resimleri\n\n")
            for ad, url in kaynaklar:
                f.write(f"- **{ad}** — <{url}>\n")


if __name__ == "__main__":
    main()
