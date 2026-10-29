# -*- coding: utf-8 -*-
"""SWF yazı tiplerine (DefineFont3) eksik Türkçe harfleri ekler.

Oyun SWF'sine gömülü "Arial Rounded MT Bold" ve "Eras Bold ITC" yazı
tiplerinde ğ, Ğ, İ, ş, Ş yoktur. Bu harflerin çizimleri aynı yazı tipinin
Türkçe sürümünden (assets/fonts/tr_*.swf) alınıp eklenir.

DefineFont3 kod tablosu sıralı olmak zorunda olduğundan yeni harfler araya
girer ve sonraki glif numaraları kayar. Bu yüzden yazı tipini kullanan
statik yazılar (DefineText/DefineText2) ve hizalama bölgeleri
(DefineFontAlignZones) da yeni numaralara göre güncellenir.
"""

import struct

TURKCE_HARFLER = "çÇğĞıİöÖşŞüÜ"

DEFINE_FONT3, ALIGN_ZONES, DEFINE_TEXT, DEFINE_TEXT2 = 75, 73, 11, 33


class _Bitler:
    def __init__(self, veri, p):
        self.veri, self.bit = veri, p * 8

    def oku(self, n, isaretli=False):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.veri[self.bit >> 3] >> (7 - (self.bit & 7))) & 1)
            self.bit += 1
        if isaretli and n and v & (1 << (n - 1)):
            v -= 1 << n
        return v

    def bayt_hizala(self):
        return (self.bit + 7) // 8


def _rect_sonu(veri, p):
    nbit = veri[p] >> 3
    return p + (5 + nbit * 4 + 7) // 8


def _matrix_sonu(veri, p):
    b = _Bitler(veri, p)
    if b.oku(1):
        n = b.oku(5)
        b.oku(n)
        b.oku(n)
    if b.oku(1):
        n = b.oku(5)
        b.oku(n)
        b.oku(n)
    n = b.oku(5)
    b.oku(n)
    b.oku(n)
    return b.bayt_hizala()


class Font3:
    """DefineFont3 etiketinin ayrıştırılmış hâli."""

    def __init__(self, t: bytes):
        self.kimlik, self.bayrak, self.dil, ad_uz = struct.unpack_from("<HBBB", t, 0)
        p = 5
        self.ad = t[p:p + ad_uz]
        p += ad_uz
        n = struct.unpack_from("<H", t, p)[0]
        p += 2
        genis = self.bayrak & 0x08
        tablo = struct.unpack_from(("<%dI" if genis else "<%dH") % (n + 1), t, p)
        taban = p
        self.sekiller = [t[taban + tablo[i]:taban + tablo[i + 1]] for i in range(n)]
        p = taban + tablo[n]
        self.kodlar = list(struct.unpack_from("<%dH" % n, t, p))
        p += 2 * n
        self.duzen = None
        if self.bayrak & 0x80:
            yukselti = t[p:p + 6]
            p += 6
            ilerleme = list(struct.unpack_from("<%dh" % n, t, p))
            p += 2 * n
            sinirlar = []
            for _ in range(n):
                son = _rect_sonu(t, p)
                sinirlar.append(t[p:son])
                p = son
            self.duzen = (yukselti, ilerleme, sinirlar, t[p:])

    def adi(self):
        return self.ad.rstrip(b"\0").decode("latin1").split(" __")[0]

    def yaz(self) -> bytes:
        n = len(self.kodlar)
        sekil_baytlari = b"".join(self.sekiller)
        tablo_uz = 4 * (n + 1)
        ofsetler, o = [], tablo_uz
        for s in self.sekiller:
            ofsetler.append(o)
            o += len(s)
        ofsetler.append(o)
        bayrak = self.bayrak | 0x08 | 0x04  # geniş ofset + geniş kod
        cikti = struct.pack("<HBBB", self.kimlik, bayrak, self.dil, len(self.ad)) + self.ad
        cikti += struct.pack("<H", n) + struct.pack("<%dI" % (n + 1), *ofsetler)
        cikti += sekil_baytlari + struct.pack("<%dH" % n, *self.kodlar)
        if self.duzen:
            yukselti, ilerleme, sinirlar, kerning = self.duzen
            cikti += yukselti + struct.pack("<%dh" % n, *ilerleme) + b"".join(sinirlar) + kerning
        return cikti


def _bolgeler(t: bytes, n: int):
    """DefineFontAlignZones -> (başlık, [glif başına bölge baytları])."""
    p = 3
    kayitlar = []
    for _ in range(n):
        bas = p
        sayi = t[p]
        p += 1 + sayi * 4 + 1
        kayitlar.append(t[bas:p])
    return t[:3], kayitlar


def harf_ekle(hedef: Font3, kaynak: Font3, hedef_bolge=None, kaynak_bolge=None, harfler=TURKCE_HARFLER):
    """Kaynak yazı tipinden eksik harfleri hedefe ekler.

    Dönüş: (eski_glif_no -> yeni_glif_no eşlemesi, yeni bölge etiketi veya None).
    Eklenecek harf yoksa (None, None).
    """
    eksik = [ord(h) for h in harfler if ord(h) not in hedef.kodlar and ord(h) in kaynak.kodlar]
    if not eksik or not hedef.duzen or not kaynak.duzen:
        return None, None
    n = len(hedef.kodlar)
    girdiler = [(hedef.kodlar[i], "h", i) for i in range(n)]
    girdiler += [(k, "k", kaynak.kodlar.index(k)) for k in eksik]
    girdiler.sort()

    bolge_h = _bolgeler(hedef_bolge, n) if hedef_bolge else None
    bolge_k = _bolgeler(kaynak_bolge, len(kaynak.kodlar)) if kaynak_bolge else None

    yukselti, ilerleme, sinirlar, kerning = hedef.duzen
    _, k_ilerleme, k_sinirlar, _ = kaynak.duzen
    sekiller, kodlar, y_ilerleme, y_sinirlar, y_bolgeler, eslem = [], [], [], [], [], {}
    for yeni, (kod, nereden, i) in enumerate(girdiler):
        kodlar.append(kod)
        if nereden == "h":
            eslem[i] = yeni
            sekiller.append(hedef.sekiller[i])
            y_ilerleme.append(ilerleme[i])
            y_sinirlar.append(sinirlar[i])
            if bolge_h:
                y_bolgeler.append(bolge_h[1][i])
        else:
            sekiller.append(kaynak.sekiller[i])
            y_ilerleme.append(k_ilerleme[i])
            y_sinirlar.append(k_sinirlar[i])
            if bolge_h:
                y_bolgeler.append(bolge_k[1][i] if bolge_k else b"\x00\x00")
    hedef.sekiller, hedef.kodlar = sekiller, kodlar
    hedef.duzen = (yukselti, y_ilerleme, y_sinirlar, kerning)
    yeni_bolge = bolge_h[0] + b"".join(y_bolgeler) if bolge_h else None
    return eslem, yeni_bolge


def metin_glifleri_esle(t: bytes, kod: int, eslemeler: dict) -> bytes:
    """DefineText/DefineText2 içindeki glif numaralarını yeniden yazar.

    eslemeler: {font_kimliği: {eski_no: yeni_no}}. Bit genişliği yetmezse
    ValueError fırlatır.
    """
    veri = bytearray(t)
    p = _matrix_sonu(veri, _rect_sonu(veri, 2))
    glif_bit, ilerleme_bit = veri[p], veri[p + 1]
    p += 2
    renk = 4 if kod == DEFINE_TEXT2 else 3
    font = None
    while veri[p] != 0:
        b = veri[p]
        p += 1
        if b & 0x08:
            font = struct.unpack_from("<H", veri, p)[0]
            p += 2
        if b & 0x04:
            p += renk
        if b & 0x01:
            p += 2
        if b & 0x02:
            p += 2
        if b & 0x08:
            p += 2
        sayi = veri[p]
        p += 1
        eslem = eslemeler.get(font)
        bit = p * 8
        for _ in range(sayi):
            if eslem:
                eski = _Bitler(veri, 0)
                eski.bit = bit
                no = eski.oku(glif_bit)
                yeni = eslem.get(no, no)
                if yeni >= (1 << glif_bit):
                    raise ValueError("glif bit genisligi yetersiz")
                for j in range(glif_bit):
                    konum = bit + j
                    maske = 1 << (7 - (konum & 7))
                    if (yeni >> (glif_bit - 1 - j)) & 1:
                        veri[konum >> 3] |= maske
                    else:
                        veri[konum >> 3] &= ~maske & 0xFF
            bit += glif_bit + ilerleme_bit
        p = (bit + 7) // 8
    return bytes(veri)


def _bit_genisligi(degerler, isaretli):
    gerek = 1
    for v in degerler:
        while True:
            if isaretli and -(1 << (gerek - 1)) <= v < (1 << (gerek - 1)):
                break
            if not isaretli and 0 <= v < (1 << gerek):
                break
            gerek += 1
    return gerek


def metin_kayitlari(t: bytes, kod: int):
    """DefineText'i (önek_baytları, [kayıt]) olarak ayrıştırır.

    Kayıt: {"bayrak", "font", "renk", "x", "y", "yukseklik", "glifler": [(no, ilerleme)]}
    """
    p = _matrix_sonu(t, _rect_sonu(t, 2))
    onek = t[:p]
    glif_bit, ilerleme_bit = t[p], t[p + 1]
    p += 2
    renk_uz = 4 if kod == DEFINE_TEXT2 else 3
    kayitlar = []
    while t[p] != 0:
        k = {"bayrak": t[p], "font": None, "renk": None, "x": None, "y": None, "yukseklik": None}
        p += 1
        if k["bayrak"] & 0x08:
            k["font"] = struct.unpack_from("<H", t, p)[0]
            p += 2
        if k["bayrak"] & 0x04:
            k["renk"] = t[p:p + renk_uz]
            p += renk_uz
        if k["bayrak"] & 0x01:
            k["x"] = struct.unpack_from("<h", t, p)[0]
            p += 2
        if k["bayrak"] & 0x02:
            k["y"] = struct.unpack_from("<h", t, p)[0]
            p += 2
        if k["bayrak"] & 0x08:
            k["yukseklik"] = struct.unpack_from("<H", t, p)[0]
            p += 2
        sayi = t[p]
        p += 1
        b = _Bitler(t, p)
        k["glifler"] = [(b.oku(glif_bit), b.oku(ilerleme_bit, True)) for _ in range(sayi)]
        p = b.bayt_hizala()
        kayitlar.append(k)
    return onek, kayitlar


def metin_yaz(onek: bytes, kayitlar) -> bytes:
    glifler = [g for k in kayitlar for g in k["glifler"]]
    glif_bit = _bit_genisligi([g[0] for g in glifler] or [0], False)
    ilerleme_bit = _bit_genisligi([g[1] for g in glifler] or [0], True)
    cikti = bytearray(onek) + bytes([glif_bit, ilerleme_bit])
    for k in kayitlar:
        cikti.append(k["bayrak"])
        if k["font"] is not None:
            cikti += struct.pack("<H", k["font"])
        if k["renk"] is not None:
            cikti += k["renk"]
        if k["x"] is not None:
            cikti += struct.pack("<h", k["x"])
        if k["y"] is not None:
            cikti += struct.pack("<h", k["y"])
        if k["yukseklik"] is not None:
            cikti += struct.pack("<H", k["yukseklik"])
        cikti.append(len(k["glifler"]))
        bitler, uzunluk = 0, 0
        for no, ilerleme in k["glifler"]:
            bitler = (bitler << glif_bit) | no
            bitler = (bitler << ilerleme_bit) | (ilerleme & ((1 << ilerleme_bit) - 1))
            uzunluk += glif_bit + ilerleme_bit
        dolgu = (-uzunluk) % 8
        cikti += (bitler << dolgu).to_bytes((uzunluk + dolgu) // 8, "big")
    cikti.append(0)
    return bytes(cikti)


def metni_coz(kayitlar, fontlar):
    """Kayıtları satır listesine çevirir. fontlar: {kimlik: Font3}."""
    satirlar, font = [], None
    for k in kayitlar:
        font = k["font"] if k["font"] is not None else font
        f = fontlar.get(font)
        if f is None:
            return None
        satirlar.append("".join(chr(f.kodlar[no]) if no < len(f.kodlar) else "?" for no, _ in k["glifler"]))
    return satirlar


def metni_degistir(kayitlar, eski_fontlar, yeni_fontlar, yeni_satirlar):
    """Kayıtların glif dizilerini yeni satırlarla değiştirir.

    Satır genişliği değişince eski orta noktayı korumak için x kaydırılır.
    Eksik harf varsa None döner (metin değiştirilmez).
    """
    if len(yeni_satirlar) != len(kayitlar):
        return None
    font, sonuc = None, []
    for k, satir in zip(kayitlar, yeni_satirlar):
        font = k["font"] if k["font"] is not None else font
        eski, yeni = eski_fontlar.get(font), yeni_fontlar.get(font)
        if not eski or not yeni or not yeni.duzen:
            return None
        ilerlemeler = yeni.duzen[1]
        # Ölçek: orijinal kayıttaki ilerlemelerin yazı tipi ilerlemelerine oranı
        toplam_font = sum(eski.duzen[1][no] for no, _ in k["glifler"]) if eski.duzen else 0
        toplam_kayit = sum(a for _, a in k["glifler"])
        olcek = toplam_kayit / toplam_font if toplam_font else 0
        if not olcek:
            return None
        kod_no = {kod: i for i, kod in enumerate(yeni.kodlar)}
        glifler = []
        for harf in satir:
            if ord(harf) not in kod_no:
                return None
            no = kod_no[ord(harf)]
            glifler.append((no, int(round(ilerlemeler[no] * olcek))))
        yeni_k = dict(k, glifler=glifler)
        fark = toplam_kayit - sum(a for _, a in glifler)
        # Kısa (buton) yazıları ortalı varsayılır; uzun açıklamalar sola dayalı.
        if k["x"] is not None and len(kayitlar) <= 2:
            yeni_k["x"] = max(-32768, min(32767, k["x"] + fark // 2))
        sonuc.append(yeni_k)
    return sonuc
