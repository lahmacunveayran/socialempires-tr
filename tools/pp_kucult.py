# -*- coding: utf-8 -*-
"""Bot profil resimlerini 128x128 JPEG'e küçültür ve kayıtları günceller."""
import glob
import json
import math
import os

from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PP = os.path.join(KOK, "templates", "img", "profile")
SAVES = os.path.join(KOK, "saves")

for yol in glob.glob(os.path.join(PP, "bot_*")):
    if not os.path.isfile(yol):
        continue
    taban, uzanti = os.path.splitext(os.path.basename(yol))
    hedef = os.path.join(PP, taban + ".jpg")
    try:
        im = Image.open(yol).convert("RGB")
    except Exception as hata:
        print(" ! açılamadı:", yol, hata)
        continue
    w, h = im.size
    olcek = max(128 / w, 128 / h)
    im = im.resize((math.ceil(w * olcek), math.ceil(h * olcek)), Image.LANCZOS)
    sol = (im.width - 128) // 2
    ust = (im.height - 128) // 2
    im = im.crop((sol, ust, sol + 128, ust + 128))
    im.save(hedef, "JPEG", quality=85, optimize=True)
    if os.path.abspath(hedef) != os.path.abspath(yol):
        os.remove(yol)

for dosya in glob.glob(os.path.join(SAVES, "*.save.json")):
    with open(dosya, encoding="utf-8") as f:
        kayit = json.load(f)
    pi = kayit.get("playerInfo", {})
    if not pi.get("bot"):
        continue
    pic = pi.get("pic", "")
    if pic.startswith("/img/profile/bot_"):
        pi["pic"] = os.path.splitext(pic)[0] + ".jpg"
        with open(dosya, "w", encoding="utf-8") as f:
            json.dump(kayit, f, indent=4, ensure_ascii=False)

print("bitti")
