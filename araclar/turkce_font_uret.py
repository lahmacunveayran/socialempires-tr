# -*- coding: utf-8 -*-
"""assets/fonts/tr_*.swf yazı tiplerini orijinal oyun yazı tiplerinden üretir.

Oyun, dil Türkçe olduğunda fonts/tr_ErasBold.swf ve tr_ArialRoundedBold.swf
dosyalarını yükler. Bu dosyalar orijinal en_*.swf yazı tiplerinin (Eras Bold
ITC, Arial Rounded MT Bold) aynısıdır; tek fark, yazı tipinde olmayan
ğ Ğ İ ş Ş harflerinin aynı yazı tipindeki harf + aksandan (g + ˘, I + ˙,
s + ¸) üretilmesidir. Sınıf adları (fonts.tr_*) mevcut tr_*.swf'den alınır.

Ayrıca en_*.swf dosyaları orijinal hâline döndürülür.

Kullanım:
    python araclar/turkce_font_uret.py
"""

import os
import struct
import sys
import urllib.request
import zlib

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from oyun import kaynaklar, swf_font, swf_yama  # noqa: E402

KAYNAK = kaynaklar.HAM_KOK + "assets/fonts/{ad}"
FONTLAR = ("ErasBold", "ArialRoundedBold")


def _etiketler(veri):
    govde = swf_yama._govde(veri)
    return govde, list(swf_yama._etiketler(govde))


def _swf(surum, govde_parcalari):
    govde = b"".join(govde_parcalari)
    return b"CWS" + bytes([surum]) + struct.pack("<I", len(govde) + 8) + zlib.compress(govde, 9)


def uret(ad):
    klasor = os.path.join(KOK, "assets", "fonts")
    with urllib.request.urlopen(KAYNAK.format(ad=f"en_{ad}.swf"), timeout=60) as yanit:
        orijinal = yanit.read()
    with open(os.path.join(klasor, f"tr_{ad}.swf"), "rb") as f:
        kap = f.read()

    o_govde, o_etiketler = _etiketler(orijinal)
    font = bolge = ad_etiketi = None
    for kod, bas, son, _ in o_etiketler:
        if kod == swf_font.DEFINE_FONT3:
            font = swf_font.Font3(o_govde[bas:son])
        elif kod == swf_font.ALIGN_ZONES:
            bolge = o_govde[bas:son]
        elif kod == 88:  # DefineFontName
            ad_etiketi = o_govde[bas:son]
    yeni_bolge = swf_font.turkce_harfleri_uret(font, bolge)
    font.ad = font.ad.replace(b"__Embedded__EN", b"__Embedded__TR")
    eksik = [h for h in "çÇğĞıİöÖşŞüÜ" if ord(h) not in font.kodlar]
    if eksik:
        raise SystemExit(f"{ad}: harf üretilemedi: {eksik}")

    k_govde, k_etiketler = _etiketler(kap)
    parcalar = []
    for kod, bas, son, baslik_bas in k_etiketler:
        if kod is None:
            parcalar.append(k_govde[bas:son])
        elif kod == swf_font.DEFINE_FONT3:
            t = font.yaz()
            parcalar.append(swf_yama._baslik(kod, len(t)) + t)
        elif kod == swf_font.ALIGN_ZONES and yeni_bolge:
            parcalar.append(swf_yama._baslik(kod, len(yeni_bolge)) + yeni_bolge)
        elif kod == 88 and ad_etiketi:
            parcalar.append(swf_yama._baslik(kod, len(ad_etiketi)) + ad_etiketi)
        else:
            parcalar.append(k_govde[baslik_bas:son])
    with open(os.path.join(klasor, f"tr_{ad}.swf"), "wb") as f:
        f.write(_swf(kap[3], parcalar))
    with open(os.path.join(klasor, f"en_{ad}.swf"), "wb") as f:
        f.write(orijinal)
    print(f"[+] tr_{ad}.swf: {len(font.kodlar)} glif; en_{ad}.swf orijinaline döndü")


if __name__ == "__main__":
    for ad in FONTLAR:
        uret(ad)
