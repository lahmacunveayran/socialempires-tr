"""Arşivde eksik efektleri oyunun kendi efektlerinden türetir.

İstemci bir efekti `fx/<ad>.swf` dosyasından yükler ve içinden `<ad>` adlı
sınıfı ister (ör. `p.miniFireball2`). Arşivde dosya yoksa benzer bir efektin
(ör. `p.fireBall`) sınıf adı değiştirilip o ad altında sunulur. Yeni görsel
üretilmez; yalnızca oyunun kendi efekti yeniden adlandırılır.
"""

import struct
import zlib

# İstenen efekt -> kullanılacak oyun efekti
TURETILEN = {
    "fx/p.miniFireball2.swf": "fx/p.fireBall.swf",
}


def _u30_oku(b, p):
    deger = kaydirma = 0
    while True:
        bayt = b[p]
        p += 1
        deger |= (bayt & 0x7F) << kaydirma
        if not bayt & 0x80 or kaydirma >= 28:
            return deger, p
        kaydirma += 7


def _u30_yaz(deger):
    cikti = bytearray()
    while True:
        bayt = deger & 0x7F
        deger >>= 7
        cikti.append(bayt | (0x80 if deger else 0))
        if not deger:
            return bytes(cikti)


def _abc_dizelerini_degistir(abc, eslemeler):
    """ABC dize havuzunda tam eşleşen dizeleri değiştirir; kalan bayt aynen kalır."""
    p = 4  # minor, major sürüm
    for genislik in (None, None, 8):  # int, uint (u30 dizileri), double (8 bayt)
        sayi, p = _u30_oku(abc, p)
        for _ in range(max(0, sayi - 1)):
            if genislik:
                p += genislik
            else:
                _, p = _u30_oku(abc, p)
    bas = p
    sayi, p = _u30_oku(abc, p)
    havuz = [_u30_yaz(sayi)]
    for _ in range(max(0, sayi - 1)):
        uzunluk, p = _u30_oku(abc, p)
        dize = abc[p:p + uzunluk]
        p += uzunluk
        dize = eslemeler.get(dize, dize)
        havuz.append(_u30_yaz(len(dize)) + dize)
    return abc[:bas] + b"".join(havuz) + abc[p:]


def _etiket(kod, govde):
    if len(govde) < 63:
        return struct.pack("<H", kod << 6 | len(govde)) + govde
    return struct.pack("<HI", kod << 6 | 63, len(govde)) + govde


def sinifi_yeniden_adlandir(veri, eski, yeni):
    """SWF'deki `eski` sınıfını (ör. "p.fireBall") `yeni` adıyla dışa aktarır."""
    imza = veri[:3]
    govde = zlib.decompress(veri[8:]) if imza == b"CWS" else veri[8:]
    if imza not in (b"CWS", b"FWS"):
        raise ValueError("desteklenmeyen SWF")
    e_paket, _, e_sinif = eski.rpartition(".")
    y_paket, _, y_sinif = yeni.rpartition(".")
    if e_paket != y_paket:
        raise ValueError("paket adı aynı kalmalı")
    eslemeler = {e_sinif.encode(): y_sinif.encode(), eski.encode(): yeni.encode(),
                 f"{e_paket}:{e_sinif}".encode(): f"{y_paket}:{y_sinif}".encode()}

    bitler = govde[0] >> 3
    p = (5 + bitler * 4 + 7) // 8 + 4  # çerçeve dikdörtgeni, kare hızı ve sayısı
    cikti = [govde[:p]]
    while p < len(govde):
        kh = struct.unpack("<H", govde[p:p + 2])[0]
        kod, uzunluk = kh >> 6, kh & 63
        p += 2
        if uzunluk == 63:
            uzunluk = struct.unpack("<I", govde[p:p + 4])[0]
            p += 4
        t = govde[p:p + uzunluk]
        p += uzunluk
        if kod == 82:  # DoABC: bayraklar, ad, ABC
            ad_sonu = t.index(b"\0", 4) + 1
            t = t[:ad_sonu] + _abc_dizelerini_degistir(t[ad_sonu:], eslemeler)
        elif kod == 76:  # SymbolClass
            sayi = struct.unpack("<H", t[:2])[0]
            q, yeni_t = 2, [t[:2]]
            for _ in range(sayi):
                karakter = t[q:q + 2]
                son = t.index(b"\0", q + 2)
                ad = t[q + 2:son]
                yeni_t.append(karakter + eslemeler.get(ad, ad) + b"\0")
                q = son + 1
            t = b"".join(yeni_t)
        cikti.append(_etiket(kod, t))
        if kod == 0:
            break
    yeni_govde = b"".join(cikti)
    baslik = imza + veri[3:4] + struct.pack("<I", len(yeni_govde) + 8)
    return baslik + (zlib.compress(yeni_govde) if imza == b"CWS" else yeni_govde)


def sinif_adi(yol):
    """"fx/p.fireBall.swf" -> "p.fireBall"."""
    return yol.rsplit("/", 1)[-1][:-len(".swf")]
