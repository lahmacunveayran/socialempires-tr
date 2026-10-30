"""İki ekran görüntüsünün ne kadar farklı olduğunu ve en iyi kaydırmayı yazar.

Harita deneyinde "sürükleme haritayı kaydırdı mı?" sorusunu görüntüye bakmadan
yanıtlar: görüntü (dx, dy) kadar kaydırıldığında fark en aza iniyorsa harita
o kadar kaymıştır.

Kullanım: python araclar/goruntu_farki.py once.png sonra.png
"""

import sys

from PIL import Image, ImageChops, ImageStat


def fark(a, b):
    """0 (aynı) ile 1 arası ortalama piksel farkı."""
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / (3 * 255)


def en_iyi_kayma(a, b, adim=4, sinir=200):
    """b, a'nın (dx, dy) kaydırılmış hâliyse o kaymayı bulur (kaba arama)."""
    kucuk = 4
    a2 = a.resize((a.width // kucuk, a.height // kucuk))
    b2 = b.resize((b.width // kucuk, b.height // kucuk))
    en = (fark(a2, b2), 0, 0)
    r = sinir // kucuk
    for dy in range(-r, r + 1, max(1, adim // kucuk)):
        for dx in range(-r, r + 1, max(1, adim // kucuk)):
            g, y = a2.width - abs(dx), a2.height - abs(dy)
            ka = a2.crop((max(0, -dx), max(0, -dy), max(0, -dx) + g, max(0, -dy) + y))
            kb = b2.crop((max(0, dx), max(0, dy), max(0, dx) + g, max(0, dy) + y))
            d = fark(ka, kb)
            if d < en[0]:
                en = (d, dx * kucuk, dy * kucuk)
    return en


# Oyun arayüzünün (üst kaynak çubuğu, alt panel, yan düğmeler) dışındaki
# harita bölgesi; kayma yalnızca burada aranır.
HARITA = (60, 100, 640, 440)

if __name__ == "__main__":
    once, sonra = (Image.open(p).convert("RGB").crop(HARITA) for p in sys.argv[1:3])
    print(f"fark: {fark(once, sonra):.4f}")
    d, dx, dy = en_iyi_kayma(once, sonra)
    print(f"en iyi kayma: dx={dx} dy={dy} (kalan fark {d:.4f})")
