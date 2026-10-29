# -*- coding: utf-8 -*-
"""Oyun SWF'sindeki sabit arayüz yazılarını Türkçeleştirir.

İstemcideki bazı yazılar (ör. "Cancel", "Next", "Share") config'teki
yerelleştirme metinlerinden değil, SWF içindeki metin alanlarının
(DefineEditText) başlangıç değerlerinden gelir. Bu modül o alanları
`ceviri/arayuz_tr.json` sözlüğüne göre değiştirip yeni bir SWF üretir.

Yalnızca eşleşen metin alanları değişir; geri kalan etiketler bayt bayt
korunur. Gömülü yazı tiplerine eksik Türkçe harfler eklenir (swf_font).
Yazı tipine gömülü sabit yazılar (DefineText) çevrilemez.
"""

import hashlib
import html
import json
import os
import re
import struct
import tempfile
import threading
import zlib

from oyun import swf_font
from oyun.yollar import ASSETS_DIR, CEVIRI_DIR
TR_FONTLARI = ("tr_ArialRoundedBold.swf", "tr_ErasBold.swf")
_URETIM_KILIDI = threading.Lock()
YAMA_SURUMU = b"6"  # yama mantığı değişince artırın (önbellek yenilensin)
SOZLUK = os.path.join(CEVIRI_DIR, "arayuz_tr.json")

_ETIKET = re.compile(r"<[^>]+>")


def anahtar(metin: str) -> str:
    """Metin alanının içeriğini sözlük anahtarına çevirir (HTML'siz)."""
    return html.unescape(_ETIKET.sub("", metin)).strip()


def _sozluk():
    with open(SOZLUK, encoding="utf-8") as f:
        return json.load(f)


def _govde(veri: bytes):
    imza = veri[:3]
    if imza == b"FWS":
        return veri[8:]
    if imza == b"CWS":
        return zlib.decompress(veri[8:])
    raise ValueError("desteklenmeyen SWF bicimi: %r" % imza)


def _etiketler(govde: bytes):
    """(kod, içerik_başı, içerik_sonu, başlık_başı) dörtlülerini üretir."""
    nbit = govde[0] >> 3
    p = (5 + nbit * 4 + 7) // 8 + 4  # RECT + kare hızı + kare sayısı
    yield None, 0, p, 0
    while p < len(govde):
        bas = p
        kod_uzunluk = struct.unpack_from("<H", govde, p)[0]
        p += 2
        kod, uzunluk = kod_uzunluk >> 6, kod_uzunluk & 0x3F
        if uzunluk == 0x3F:
            uzunluk = struct.unpack_from("<I", govde, p)[0]
            p += 4
        yield kod, p, p + uzunluk, bas
        p += uzunluk
        if kod == 0:
            break


def _baslik(kod: int, uzunluk: int) -> bytes:
    return struct.pack("<HI", (kod << 6) | 0x3F, uzunluk)


def _font_konumu(t: bytes):
    """DefineEditText'teki FontID'nin konumu (yoksa None)."""
    nbit = t[2] >> 3
    p = 2 + (5 + nbit * 4 + 7) // 8
    return p + 2 if t[p] & 0x01 else None


def _metin_konumu(t: bytes):
    """DefineEditText içindeki InitialText'in (başlangıç, bitiş, html) konumu."""
    nbit = t[2] >> 3
    p = 2 + (5 + nbit * 4 + 7) // 8
    b1, b2 = t[p], t[p + 1]
    p += 2
    metin_var, renk_var, uzunluk_var, font_var = b1 & 0x80, b1 & 0x04, b1 & 0x02, b1 & 0x01
    font_sinifi_var, yerlesim_var, html_mi = b2 & 0x80, b2 & 0x20, b2 & 0x02
    if not metin_var:
        return None
    if font_var:
        p += 2
    if font_sinifi_var:
        p = t.index(b"\0", p) + 1
    if font_var or font_sinifi_var:
        p += 2
    if renk_var:
        p += 4
    if uzunluk_var:
        p += 2
    if yerlesim_var:
        p += 9
    p = t.index(b"\0", p) + 1  # değişken adı
    son = t.index(b"\0", p)
    return p, son, bool(html_mi)


def _html_degistir(kaynak: str, ceviri: str) -> str:
    """HTML metnin ilk yazı düğümüne çeviriyi koyar, diğerlerini boşaltır."""
    parcalar = re.split(r"(<[^>]+>)", kaynak)
    yeni = html.escape(ceviri, quote=False).replace("\r", "<br>")
    yazildi = False
    for i, parca in enumerate(parcalar):
        if parca.startswith("<") or not parca.strip():
            continue
        parcalar[i] = "" if yazildi else yeni
        yazildi = True
    return "".join(parcalar)


def _turkce_fontlar():
    """assets/fonts/tr_*.swf içindeki yazı tiplerini {ad: (Font3, bölge)} olarak yükler."""
    fontlar = {}
    klasor = os.path.join(ASSETS_DIR, "fonts")
    for ad in TR_FONTLARI:
        yol = os.path.join(klasor, ad)
        if not os.path.exists(yol):
            continue
        with open(yol, "rb") as f:
            govde = _govde(f.read())
        font, bolge = None, None
        for kod, bas, son, _ in _etiketler(govde):
            if kod == swf_font.DEFINE_FONT3:
                font = swf_font.Font3(govde[bas:son])
            elif kod == swf_font.ALIGN_ZONES:
                bolge = govde[bas:son]
        if font:
            fontlar[font.adi()] = (font, bolge)
    return fontlar


def _fontlari_tamamla(govde, etiketler):
    """Gömülü yazı tiplerine eksik Türkçe harfleri ekler.

    Dönüş: {başlık_başı: yeni_etiket_baytları}, glif eşlemeleri ve
    yazı tipleri (önceki/sonraki hâlleriyle, kimliğe göre).
    """
    kaynaklar = _turkce_fontlar()
    bolgeler = {}
    for kod, bas, son, _ in etiketler:
        if kod == swf_font.ALIGN_ZONES:
            bolgeler[struct.unpack_from("<H", govde, bas)[0]] = (bas, son)
    degisim, eslemeler, eski_fontlar, yeni_fontlar = {}, {}, {}, {}
    for kod, bas, son, baslik_bas in etiketler:
        if kod != swf_font.DEFINE_FONT3:
            continue
        font = swf_font.Font3(govde[bas:son])
        eski_fontlar[font.kimlik] = swf_font.Font3(govde[bas:son])
        yeni_fontlar[font.kimlik] = font
        if font.adi() not in kaynaklar:
            continue
        kaynak, kaynak_bolge = kaynaklar[font.adi()]
        b = bolgeler.get(font.kimlik)
        eslem, yeni_bolge = swf_font.harf_ekle(font, kaynak, govde[b[0]:b[1]] if b else None, kaynak_bolge)
        if eslem is None:
            continue
        eslemeler[font.kimlik] = eslem
        t = font.yaz()
        degisim[baslik_bas] = _baslik(kod, len(t)) + t
        if b and yeni_bolge:
            degisim[("bolge", b[0])] = yeni_bolge
    return degisim, eslemeler, eski_fontlar, yeni_fontlar


def _yazi_tipini_uydur(t, metin, fontlar):
    """Alanın yazı tipinde çevirinin bir harfi yoksa (ör. yalnızca 13 harfli
    Arial Narrow sayaç etiketleri), harflerin hepsini içeren bir yazı tipine geçer."""
    konum = _font_konumu(t)
    if konum is None:
        return t
    gerekli = {ord(h) for h in metin if not h.isspace()}
    mevcut = fontlar.get(struct.unpack_from("<H", t, konum)[0])
    if mevcut is None or gerekli <= set(mevcut.kodlar):
        return t
    for kimlik, font in fontlar.items():
        if font.adi() == "Arial Rounded MT Bold" and gerekli <= set(font.kodlar):
            return t[:konum] + struct.pack("<H", kimlik) + t[konum + 2:]
    return t


def turkcelestir(veri: bytes, sozluk=None):
    """SWF baytlarını alır, (yeni_swf_baytları, değişen_alan_sayısı) döndürür."""
    sozluk = _sozluk() if sozluk is None else sozluk
    govde = _govde(veri)
    etiketler = list(_etiketler(govde))
    degisim, eslemeler, eski_fontlar, yeni_fontlar = _fontlari_tamamla(govde, etiketler)
    statik = sozluk.get("statik_yazilar", {})
    sozluk = sozluk.get("metin_alanlari", sozluk)
    cikti = []
    degisen = 0
    for kod, bas, son, baslik_bas in etiketler:
        if kod is None:
            cikti.append(govde[bas:son])
            continue
        if baslik_bas in degisim:
            cikti.append(degisim[baslik_bas])
            continue
        if ("bolge", bas) in degisim:
            t = degisim[("bolge", bas)]
            cikti.append(_baslik(kod, len(t)) + t)
            continue
        if kod in (swf_font.DEFINE_TEXT, swf_font.DEFINE_TEXT2):
            t = govde[bas:son]
            onek, kayitlar = swf_font.metin_kayitlari(t, kod)
            satirlar = swf_font.metni_coz(kayitlar, eski_fontlar)
            ceviri = statik.get("|".join(satirlar)) if satirlar else None
            yeni = swf_font.metni_degistir(kayitlar, eski_fontlar, yeni_fontlar, ceviri.split("|")) if ceviri else None
            if yeni:
                t = swf_font.metin_yaz(onek, yeni)
                degisen += 1
            elif eslemeler:
                t = swf_font.metin_yaz(onek, swf_font.glifleri_esle(kayitlar, eslemeler))
            cikti.append(_baslik(kod, len(t)) + t)
            continue
        if kod == 37:
            t = govde[bas:son]
            konum = _metin_konumu(t)
            if konum:
                m_bas, m_son, html_mi = konum
                metin = t[m_bas:m_son].decode("utf-8", "replace")
                ceviri = sozluk.get(anahtar(metin))
                if ceviri:
                    yeni_metin = _html_degistir(metin, ceviri) if html_mi else ceviri
                    t = t[:m_bas] + yeni_metin.encode("utf-8") + t[m_son:]
                    t = _yazi_tipini_uydur(t, ceviri, yeni_fontlar)
                    cikti.append(_baslik(kod, len(t)) + t)
                    degisen += 1
                    continue
        cikti.append(govde[baslik_bas:son])
    yeni_govde = b"".join(cikti)
    basluk = b"CWS" + veri[3:4] + struct.pack("<I", len(yeni_govde) + 8)
    return basluk + zlib.compress(yeni_govde, 6), degisen


def onbellekli_turkcelestir(kaynak_yol: str, onbellek_klasoru: str) -> str:
    """Yamalanmış SWF'yi önbellekte üretir ve yolunu döndürür.

    Kaynak dosya veya sözlük değişince yeniden üretilir.
    """
    with open(kaynak_yol, "rb") as f:
        veri = f.read()
    ozet = hashlib.sha1(veri + YAMA_SURUMU)
    for yol in [SOZLUK] + [os.path.join(ASSETS_DIR, "fonts", ad) for ad in TR_FONTLARI]:
        if os.path.exists(yol):
            with open(yol, "rb") as f:
                ozet.update(f.read())
    ad = os.path.splitext(os.path.basename(kaynak_yol))[0]
    hedef = os.path.join(onbellek_klasoru, f"{ad}.tr-{ozet.hexdigest()[:12]}.swf")
    with _URETIM_KILIDI:  # aynı anda gelen istekler dosyayı iki kez üretmesin
        if not os.path.exists(hedef):
            os.makedirs(onbellek_klasoru, exist_ok=True)
            yeni, degisen = turkcelestir(veri)
            fd, gecici = tempfile.mkstemp(dir=onbellek_klasoru, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(yeni)
            os.replace(gecici, hedef)
            print(f" [+] {ad}.swf Turkcelestirildi ({degisen} metin alani)")
    return hedef
