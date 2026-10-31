# -*- coding: utf-8 -*-
"""Sayfa süslerini oyunun kendi SWF'lerinden çıkarır (templates/img/oyun/).

Sayfadaki çerçeve, gökyüzü, düğme ve çubuklar elle çizilmez: oyunun ana SWF'sine gömülü
resimlerdir (DefineBits* etiketleri). Bu araç onları hiç değiştirmeden PNG'ye yazar; yalnızca
SWF'nin önceden çarpılmış alfası düz alfaya çevrilir (Flash ekrana böyle basar).

Kullanım:
    python araclar/swf_resimleri.py            seçili resimleri templates/img/oyun/ altına yazar
    python araclar/swf_resimleri.py --hepsi D  SWF'deki bütün resimleri D klasörüne döker (göz atmak için)
"""

import io
import os
import struct
import sys
import zlib

from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from oyun.kaynaklar import ISTEMCI_YOLU  # noqa: E402
from oyun.yollar import INDIRILEN_DIR  # noqa: E402

ANA_SWF = os.path.join(INDIRILEN_DIR, "assets", *ISTEMCI_YOLU.split("/"))
BAYRAK_SWF = os.path.join(INDIRILEN_DIR, "assets", "buildingsprites", "flagtr.swf")
HEDEF = os.path.join(KOK, "templates", "img", "oyun")

# (SWF, karakter no, dosya adı): oyunda nerede göründüğü yanında
SECILENLER = [
    (ANA_SWF, 1338, "pencere.png"),        # oyunun düz açılır penceresi: ahşap kenar, parşömen iç
    (ANA_SWF, 458, "gokyuzu.png"),         # oyunun gökyüzü (harita arkası)
    (ANA_SWF, 163, "altin-kutu.png"),      # altın kutu (pencere başlıkları, sayaçlar)
    (ANA_SWF, 1955, "kahve-dugme.png"),    # kahverengi düğme zemini (ATTACKING / SPYING düğmeleri)
    (ANA_SWF, 1354, "beyaz-hap.png"),      # altın kenarlı beyaz hap (bilgi kutucukları)
    (ANA_SWF, 203, "cubuk-bos.png"),       # ilerleme çubuğu yuvası
    (ANA_SWF, 207, "cubuk-dolu.png"),      # ilerleme çubuğu dolgusu
    (ANA_SWF, 2286, "altin-cerceve.png"),  # altın süslü resim çerçevesi
    (ANA_SWF, 2369, "bronz-cerceve.png"),  # bronz resim çerçevesi
    (ANA_SWF, 1280, "kirmizi-hap.png"),    # kırmızı hap (oyunun "yeni" işaretleri)
    (BAYRAK_SWF, 1, "bayrak-tr.png"),      # Türk bayrağı süsü (Turkey Flag, öğe 174)
]


def swf_ac(yol):
    with open(yol, "rb") as f:
        v = f.read()
    if v[:3] == b"CWS":
        return v[:8] + zlib.decompress(v[8:])
    if v[:3] == b"FWS":
        return v
    raise ValueError("SWF değil ya da desteklenmeyen sıkıştırma: %s" % yol)


def etiketler(v):
    bit = v[8] >> 3
    i = 8 + (5 + 4 * bit + 7) // 8 + 4  # başlık: çerçeve dikdörtgeni, kare hızı, kare sayısı
    while i < len(v):
        kod = struct.unpack_from("<H", v, i)[0]
        i += 2
        tip, uzunluk = kod >> 6, kod & 0x3F
        if uzunluk == 0x3F:
            uzunluk = struct.unpack_from("<I", v, i)[0]
            i += 4
        yield tip, v[i:i + uzunluk]
        i += uzunluk
        if tip == 0:
            return


def _kayipsiz(veri, alfali):
    no, bicim, g, y = struct.unpack_from("<HBHH", veri)
    if bicim == 3:  # paletli
        renk = veri[7] + 1
        ham = zlib.decompress(veri[8:])
        boy = 4 if alfali else 3
        palet, piksel = ham[:renk * boy], ham[renk * boy:]
        satir = (g + 3) & ~3
        cikti = bytearray()
        for yy in range(y):
            for xx in range(g):
                k = piksel[yy * satir + xx] * boy
                cikti += palet[k:k + boy] if alfali else palet[k:k + 3] + b"\xff"
        return no, Image.frombytes("RGBA", (g, y), bytes(cikti))
    if bicim == 5:  # 32 bit ARGB
        ham = zlib.decompress(veri[7:])
        cikti = bytearray(len(ham))
        for i in range(0, len(ham), 4):
            a, r, gg, b = ham[i:i + 4]
            if not alfali:
                a = 255
            elif 0 < a < 255:  # önceden çarpılmış alfa
                r, gg, b = min(255, r * 255 // a), min(255, gg * 255 // a), min(255, b * 255 // a)
            cikti[i:i + 4] = bytes((r, gg, b, a))
        return no, Image.frombytes("RGBA", (g, y), bytes(cikti))
    return no, None


def _jpeg(veri, tip, tablolar):
    no = struct.unpack_from("<H", veri)[0]
    alfa = b""
    if tip in (6, 21):
        ham = veri[2:]
    else:  # 35 / 90: JPEG + ayrı alfa
        bas = 6 if tip == 35 else 8
        uzunluk = struct.unpack_from("<I", veri, 2)[0]
        ham, alfa = veri[bas:bas + uzunluk], veri[bas + uzunluk:]
    if ham[:4] == b"\xff\xd9\xff\xd8":
        ham = ham[4:]
    if tip == 6 and tablolar:
        ham = tablolar[:-2] + ham[2:]
    resim = Image.open(io.BytesIO(ham))
    resim.load()
    if alfa and ham[:4] != b"\x89PNG":
        resim = resim.convert("RGB")
        resim.putalpha(Image.frombytes("L", resim.size, zlib.decompress(alfa)))
    return no, resim


def resimler(yol):
    """SWF'deki gömülü resimler: {karakter no: PIL resmi}."""
    bulunan, tablolar = {}, b""
    for tip, veri in etiketler(swf_ac(yol)):
        if tip == 8:
            tablolar = veri
        elif tip in (6, 21, 35, 90):
            no, resim = _jpeg(veri, tip, tablolar)
            bulunan[no] = resim
        elif tip in (20, 36):
            no, resim = _kayipsiz(veri, tip == 36)
            if resim is not None:
                bulunan[no] = resim
    return bulunan


def main(argv):
    if argv[:1] == ["--hepsi"]:
        hedef = argv[1]
        os.makedirs(hedef, exist_ok=True)
        for no, resim in sorted(resimler(argv[2] if len(argv) > 2 else ANA_SWF).items()):
            resim.save(os.path.join(hedef, "%05d_%dx%d.png" % (no, resim.size[0], resim.size[1])))
        return
    os.makedirs(HEDEF, exist_ok=True)
    onbellek = {}
    for swf, no, ad in SECILENLER:
        if swf not in onbellek:
            if not os.path.exists(swf):
                raise SystemExit("Önce oyunu bir kez açın ya da varlıkları indirin: %s yok" % swf)
            onbellek[swf] = resimler(swf)
        onbellek[swf][no].save(os.path.join(HEDEF, ad), optimize=True)
        print("yazıldı:", ad)


if __name__ == "__main__":
    main(sys.argv[1:])
