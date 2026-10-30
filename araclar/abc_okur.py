"""AS3 bayt kodu okuyucusu (ABC, AVM2): istemcinin kodunu çalıştırmadan okur.

Kendi kodumuzdur; dışarıdan indirilen araç (FFDec) çalıştırılmaz (S-11). Biçim Adobe'nin
"ActionScript Virtual Machine 2 Overview" belgesine göredir.

- `abc_etiketleri(veri)`: SWF'deki DoABC etiketlerinin baytları.
- `Abc(bayt)`: sabit havuzu, yöntemleri, sınıfları, betikleri ve yöntem gövdelerini çözer.
- `Abc.coz(govde)`: gövdenin işlem kodlarını **akışı izleyerek** çözer. Gizlenmiş istemcide hiç çalışmayan,
  atlamalarla geçilen anlamsız baytlar vardır; doğrusal okuma onlarda bozulur, akış izleme onlara hiç uğramaz.
- `Abc.cagrilar(ad)`: `ad` adlı özelliğe yapılan her çağrının argümanlarını, gövdeyi temel bloklar içinde
  simgesel bir yığınla izleyerek çıkarır (ör. `addCommand("buy", [id, x, y])`).

Komut satırı: `python araclar/abc_okur.py istemci.swf [--ozet | --cagri addCommand]`.
"""

import struct
import sys
import zlib
from collections import namedtuple

DO_ABC, DO_ABC1 = 82, 72

# Çok adlı (multiname) türleri
QNAME, QNAME_A, RTQNAME, RTQNAME_A = 0x07, 0x0D, 0x0F, 0x10
RTQNAME_L, RTQNAME_LA, MULTINAME, MULTINAME_A = 0x11, 0x12, 0x09, 0x0E
MULTINAME_L, MULTINAME_LA, TYPENAME = 0x1B, 0x1C, 0x1D

# İşlem kodları: kod -> (ad, işlenen biçimleri). u30: değişken uzunluk; u8: bir bayt;
# s24: üç baytlık işaretli dal uzaklığı; "switch": lookupswitch'in kendi biçimi.
_DAL = ("s24",)
ISLEMLER = {
    0x01: ("bkpt", ()), 0x02: ("nop", ()), 0x03: ("throw", ()),
    0x04: ("getsuper", ("u30",)), 0x05: ("setsuper", ("u30",)), 0x06: ("dxns", ("u30",)),
    0x07: ("dxnslate", ()), 0x08: ("kill", ("u30",)), 0x09: ("label", ()),
    0x0C: ("ifnlt", _DAL), 0x0D: ("ifnle", _DAL), 0x0E: ("ifngt", _DAL), 0x0F: ("ifnge", _DAL),
    0x10: ("jump", _DAL), 0x11: ("iftrue", _DAL), 0x12: ("iffalse", _DAL), 0x13: ("ifeq", _DAL),
    0x14: ("ifne", _DAL), 0x15: ("iflt", _DAL), 0x16: ("ifle", _DAL), 0x17: ("ifgt", _DAL),
    0x18: ("ifge", _DAL), 0x19: ("ifstricteq", _DAL), 0x1A: ("ifstrictne", _DAL),
    0x1B: ("lookupswitch", ("switch",)), 0x1C: ("pushwith", ()), 0x1D: ("popscope", ()),
    0x1E: ("nextname", ()), 0x1F: ("hasnext", ()), 0x20: ("pushnull", ()),
    0x21: ("pushundefined", ()), 0x23: ("nextvalue", ()), 0x24: ("pushbyte", ("u8",)),
    0x25: ("pushshort", ("u30",)), 0x26: ("pushtrue", ()), 0x27: ("pushfalse", ()),
    0x28: ("pushnan", ()), 0x29: ("pop", ()), 0x2A: ("dup", ()), 0x2B: ("swap", ()),
    0x2C: ("pushstring", ("u30",)), 0x2D: ("pushint", ("u30",)), 0x2E: ("pushuint", ("u30",)),
    0x2F: ("pushdouble", ("u30",)), 0x30: ("pushscope", ()), 0x31: ("pushnamespace", ("u30",)),
    0x32: ("hasnext2", ("u30", "u30")),
    0x35: ("li8", ()), 0x36: ("li16", ()), 0x37: ("li32", ()), 0x38: ("lf32", ()), 0x39: ("lf64", ()),
    0x3A: ("si8", ()), 0x3B: ("si16", ()), 0x3C: ("si32", ()), 0x3D: ("sf32", ()), 0x3E: ("sf64", ()),
    0x40: ("newfunction", ("u30",)), 0x41: ("call", ("u30",)), 0x42: ("construct", ("u30",)),
    0x43: ("callmethod", ("u30", "u30")), 0x44: ("callstatic", ("u30", "u30")),
    0x45: ("callsuper", ("u30", "u30")), 0x46: ("callproperty", ("u30", "u30")),
    0x47: ("returnvoid", ()), 0x48: ("returnvalue", ()), 0x49: ("constructsuper", ("u30",)),
    0x4A: ("constructprop", ("u30", "u30")), 0x4C: ("callproplex", ("u30", "u30")),
    0x4E: ("callsupervoid", ("u30", "u30")), 0x4F: ("callpropvoid", ("u30", "u30")),
    0x50: ("sxi1", ()), 0x51: ("sxi8", ()), 0x52: ("sxi16", ()), 0x53: ("applytype", ("u30",)),
    0x55: ("newobject", ("u30",)), 0x56: ("newarray", ("u30",)), 0x57: ("newactivation", ()),
    0x58: ("newclass", ("u30",)), 0x59: ("getdescendants", ("u30",)), 0x5A: ("newcatch", ("u30",)),
    0x5D: ("findpropstrict", ("u30",)), 0x5E: ("findproperty", ("u30",)), 0x5F: ("finddef", ("u30",)),
    0x60: ("getlex", ("u30",)), 0x61: ("setproperty", ("u30",)), 0x62: ("getlocal", ("u30",)),
    0x63: ("setlocal", ("u30",)), 0x64: ("getglobalscope", ()), 0x65: ("getscopeobject", ("u8",)),
    0x66: ("getproperty", ("u30",)), 0x67: ("getouterscope", ("u30",)), 0x68: ("initproperty", ("u30",)),
    0x6A: ("deleteproperty", ("u30",)), 0x6C: ("getslot", ("u30",)), 0x6D: ("setslot", ("u30",)),
    0x6E: ("getglobalslot", ("u30",)), 0x6F: ("setglobalslot", ("u30",)),
    0x70: ("convert_s", ()), 0x71: ("esc_xelem", ()), 0x72: ("esc_xattr", ()), 0x73: ("convert_i", ()),
    0x74: ("convert_u", ()), 0x75: ("convert_d", ()), 0x76: ("convert_b", ()), 0x77: ("convert_o", ()),
    0x78: ("checkfilter", ()), 0x80: ("coerce", ("u30",)), 0x81: ("coerce_b", ()), 0x82: ("coerce_a", ()),
    0x83: ("coerce_i", ()), 0x84: ("coerce_d", ()), 0x85: ("coerce_s", ()), 0x86: ("astype", ("u30",)),
    0x87: ("astypelate", ()), 0x88: ("coerce_u", ()), 0x89: ("coerce_o", ()),
    0x90: ("negate", ()), 0x91: ("increment", ()), 0x92: ("inclocal", ("u30",)), 0x93: ("decrement", ()),
    0x94: ("declocal", ("u30",)), 0x95: ("typeof", ()), 0x96: ("not", ()), 0x97: ("bitnot", ()),
    0xA0: ("add", ()), 0xA1: ("subtract", ()), 0xA2: ("multiply", ()), 0xA3: ("divide", ()),
    0xA4: ("modulo", ()), 0xA5: ("lshift", ()), 0xA6: ("rshift", ()), 0xA7: ("urshift", ()),
    0xA8: ("bitand", ()), 0xA9: ("bitor", ()), 0xAA: ("bitxor", ()), 0xAB: ("equals", ()),
    0xAC: ("strictequals", ()), 0xAD: ("lessthan", ()), 0xAE: ("lessequals", ()),
    0xAF: ("greaterthan", ()), 0xB0: ("greaterequals", ()), 0xB1: ("instanceof", ()),
    0xB2: ("istype", ("u30",)), 0xB3: ("istypelate", ()), 0xB4: ("in", ()),
    0xC0: ("increment_i", ()), 0xC1: ("decrement_i", ()), 0xC2: ("inclocal_i", ("u30",)),
    0xC3: ("declocal_i", ("u30",)), 0xC4: ("negate_i", ()), 0xC5: ("add_i", ()),
    0xC6: ("subtract_i", ()), 0xC7: ("multiply_i", ()),
    0xD0: ("getlocal_0", ()), 0xD1: ("getlocal_1", ()), 0xD2: ("getlocal_2", ()), 0xD3: ("getlocal_3", ()),
    0xD4: ("setlocal_0", ()), 0xD5: ("setlocal_1", ()), 0xD6: ("setlocal_2", ()), 0xD7: ("setlocal_3", ()),
    0xEF: ("debug", ("u8", "u30", "u8", "u30")), 0xF0: ("debugline", ("u30",)),
    0xF1: ("debugfile", ("u30",)), 0xF2: ("bkptline", ("u30",)), 0xF3: ("timestamp", ()),
}
KOSULLU = {"ifnlt", "ifnle", "ifngt", "ifnge", "iftrue", "iffalse", "ifeq", "ifne", "iflt", "ifle",
           "ifgt", "ifge", "ifstricteq", "ifstrictne"}
BITIRIR = {"returnvoid", "returnvalue", "throw"}

Islem = namedtuple("Islem", "ofset ad isl sonraki hedefler")
Govde = namedtuple("Govde", "yontem max_yigin yerel_sayisi kod istisnalar")
Cagri = namedtuple("Cagri", "yontem ofset ad argumanlar")


class OkumaHatasi(ValueError):
    pass


class _Okur:
    def __init__(self, b, p=0):
        self.b, self.p = b, p

    def u8(self):
        if self.p >= len(self.b):
            raise OkumaHatasi("beklenmeyen son @%d" % self.p)
        x = self.b[self.p]
        self.p += 1
        return x

    def u16(self):
        x = struct.unpack_from("<H", self.b, self.p)[0]
        self.p += 2
        return x

    def u30(self):
        deger = 0
        for kayma in range(0, 35, 7):
            x = self.u8()
            deger |= (x & 0x7F) << kayma
            if not x & 0x80:
                return deger & 0xFFFFFFFF
        return deger & 0xFFFFFFFF

    def s32(self):
        x = self.u30()
        return x - (1 << 32) if x & 0x80000000 else x

    def s24(self):
        x = self.b[self.p] | self.b[self.p + 1] << 8 | self.b[self.p + 2] << 16
        self.p += 3
        return x - (1 << 24) if x & 0x800000 else x

    def d64(self):
        x = struct.unpack_from("<d", self.b, self.p)[0]
        self.p += 8
        return x

    def baytlar(self, n):
        x = self.b[self.p:self.p + n]
        if len(x) != n:
            raise OkumaHatasi("beklenmeyen son @%d" % self.p)
        self.p += n
        return x


def swf_govdesi(veri: bytes) -> bytes:
    imza = veri[:3]
    if imza == b"FWS":
        return veri[8:]
    if imza == b"CWS":
        return zlib.decompress(veri[8:])
    raise OkumaHatasi("desteklenmeyen SWF biçimi: %r" % imza)


def abc_etiketleri(veri: bytes):
    """SWF'deki DoABC etiketlerinden (ad, abc_baytları) listesi."""
    g = swf_govdesi(veri)
    p = (5 + (g[0] >> 3) * 4 + 7) // 8 + 4  # RECT + kare hızı + kare sayısı
    cikti = []
    while p + 2 <= len(g):
        ku = struct.unpack_from("<H", g, p)[0]
        p += 2
        kod, uzunluk = ku >> 6, ku & 0x3F
        if uzunluk == 0x3F:
            uzunluk = struct.unpack_from("<I", g, p)[0]
            p += 4
        icerik = g[p:p + uzunluk]
        p += uzunluk
        if kod == DO_ABC:
            ad_sonu = icerik.index(b"\0", 4)
            cikti.append((icerik[4:ad_sonu].decode("utf-8", "replace"), icerik[ad_sonu + 1:]))
        elif kod == DO_ABC1:
            cikti.append(("", icerik))
        elif kod == 0:
            break
    return cikti


class Abc:
    def __init__(self, bayt: bytes):
        o = _Okur(bayt)
        self.kucuk, self.buyuk = o.u16(), o.u16()
        self.tamsayilar = [0] + [o.s32() for _ in range(max(o.u30() - 1, 0))]
        self.isaretsizler = [0] + [o.u30() for _ in range(max(o.u30() - 1, 0))]
        self.ondaliklar = [float("nan")] + [o.d64() for _ in range(max(o.u30() - 1, 0))]
        self.dizeler = [None]
        for _ in range(max(o.u30() - 1, 0)):
            self.dizeler.append(o.baytlar(o.u30()).decode("utf-8", "replace"))
        self.ad_alanlari = [(0, 0)] + [(o.u8(), o.u30()) for _ in range(max(o.u30() - 1, 0))]
        self.ad_kumeleri = [()]
        for _ in range(max(o.u30() - 1, 0)):
            self.ad_kumeleri.append(tuple(o.u30() for _ in range(o.u30())))
        self.coklu_adlar = [(0,)]
        for _ in range(max(o.u30() - 1, 0)):
            self.coklu_adlar.append(self._coklu_ad(o))
        self.yontemler = [self._yontem(o) for _ in range(o.u30())]
        self.ustveriler = []
        for _ in range(o.u30()):
            ad, n = o.u30(), o.u30()
            self.ustveriler.append((ad, [(o.u30(), o.u30()) for _ in range(n)]))
        sinif_sayisi = o.u30()
        self.ornekler = [self._ornek(o) for _ in range(sinif_sayisi)]
        self.siniflar = [(o.u30(), self._ozellikler(o)) for _ in range(sinif_sayisi)]
        self.betikler = [(o.u30(), self._ozellikler(o)) for _ in range(o.u30())]
        self.govdeler = {}
        for _ in range(o.u30()):
            g = self._govde(o)
            self.govdeler[g.yontem] = g
        self._yontem_adlari = None

    # --- sabit havuzu ---

    @staticmethod
    def _coklu_ad(o):
        tur = o.u8()
        if tur in (QNAME, QNAME_A):
            return (tur, o.u30(), o.u30())
        if tur in (RTQNAME, RTQNAME_A):
            return (tur, o.u30())
        if tur in (RTQNAME_L, RTQNAME_LA):
            return (tur,)
        if tur in (MULTINAME, MULTINAME_A):
            return (tur, o.u30(), o.u30())
        if tur in (MULTINAME_L, MULTINAME_LA):
            return (tur, o.u30())
        if tur == TYPENAME:
            ad, n = o.u30(), o.u30()
            return (tur, ad, tuple(o.u30() for _ in range(n)))
        raise OkumaHatasi("bilinmeyen çok adlı türü 0x%02x @%d" % (tur, o.p - 1))

    def dize(self, i):
        return self.dizeler[i] if 0 < i < len(self.dizeler) else None

    def ad(self, i) -> str:
        """Çok adlının okunur adı (ad alanı olmadan); bilinmiyorsa '*'."""
        if not 0 < i < len(self.coklu_adlar):
            return "*"
        m = self.coklu_adlar[i]
        tur = m[0]
        if tur in (QNAME, QNAME_A, MULTINAME, MULTINAME_A):
            ad = self.dize(m[2] if tur in (QNAME, QNAME_A) else m[1])
            return ad if ad is not None else "*"
        if tur in (RTQNAME, RTQNAME_A):
            return self.dize(m[1]) or "*"
        if tur == TYPENAME:
            return "%s.<%s>" % (self.ad(m[1]), ",".join(self.ad(x) for x in m[2]))
        return "[]"  # çalışma anında belirlenen ad (ör. a[i])

    def calisma_anli(self, i) -> int:
        """Çok adlının yığından kaç değer aldığı (RTQName: ad alanı, ...L: ad)."""
        if not 0 < i < len(self.coklu_adlar):
            return 0
        tur = self.coklu_adlar[i][0]
        return {RTQNAME: 1, RTQNAME_A: 1, RTQNAME_L: 2, RTQNAME_LA: 2,
                MULTINAME_L: 1, MULTINAME_LA: 1}.get(tur, 0)

    # --- yöntemler, sınıflar ---

    @staticmethod
    def _yontem(o):
        n = o.u30()
        donus = o.u30()
        turler = [o.u30() for _ in range(n)]
        ad = o.u30()
        bayrak = o.u8()
        if bayrak & 0x08:
            for _ in range(o.u30()):
                o.u30()
                o.u8()
        adlar = [o.u30() for _ in range(n)] if bayrak & 0x80 else []
        return {"param": n, "donus": donus, "turler": turler, "ad": ad, "bayrak": bayrak, "adlar": adlar}

    def _ozellikler(self, o):
        cikti = []
        for _ in range(o.u30()):
            ad, tur = o.u30(), o.u8()
            cesit = tur & 0x0F
            if cesit in (0, 6):  # Slot, Const: (tür, ad, yuva, tip, değer sırası, değer türü)
                kayit = (cesit, ad, o.u30(), o.u30())
                vindex = o.u30()
                kayit += (vindex, o.u8() if vindex else 0)
            elif cesit in (1, 2, 3, 4, 5):  # Method, Getter, Setter, Class, Function
                kayit = (cesit, ad, o.u30(), o.u30())
            else:
                raise OkumaHatasi("bilinmeyen özellik türü %d @%d" % (cesit, o.p - 1))
            if tur & 0x40:
                for _ in range(o.u30()):
                    o.u30()
            cikti.append(kayit)
        return cikti

    def _ornek(self, o):
        ad, ust = o.u30(), o.u30()
        bayrak = o.u8()
        if bayrak & 0x08:
            o.u30()
        arayuzler = [o.u30() for _ in range(o.u30())]
        iinit = o.u30()
        return {"ad": ad, "ust": ust, "arayuzler": arayuzler, "iinit": iinit,
                "ozellikler": self._ozellikler(o)}

    def _govde(self, o):
        yontem, max_yigin, yerel = o.u30(), o.u30(), o.u30()
        o.u30()
        o.u30()
        kod = o.baytlar(o.u30())
        istisnalar = [tuple(o.u30() for _ in range(5)) for _ in range(o.u30())]
        self._ozellikler(o)
        return Govde(yontem, max_yigin, yerel, kod, istisnalar)

    def yontem_adlari(self) -> dict:
        """Yöntem sırası -> 'Sınıf/yöntem' (sınıfın yöntemleri, kurucular, betik işlevleri)."""
        if self._yontem_adlari is not None:
            return self._yontem_adlari
        adlar = {}

        def ekle(sahip, ozellikler):
            for cesit, ad, _, yontem, *_ in ozellikler:
                if cesit in (1, 2, 3, 5):
                    on = {2: "get ", 3: "set "}.get(cesit, "")
                    adlar.setdefault(yontem, "%s/%s%s" % (sahip, on, self.ad(ad)))

        for i, ornek in enumerate(self.ornekler):
            sinif = self.ad(ornek["ad"])
            adlar.setdefault(ornek["iinit"], sinif + "/<kurucu>")
            adlar.setdefault(self.siniflar[i][0], sinif + "/<sınıf>")
            ekle(sinif, ornek["ozellikler"])
            ekle(sinif + "$", self.siniflar[i][1])
        for i, (init, ozellikler) in enumerate(self.betikler):
            adlar.setdefault(init, "betik%d/<init>" % i)
            ekle("betik%d" % i, ozellikler)
        self._yontem_adlari = adlar
        return adlar

    # --- işlem kodları ---

    @staticmethod
    def _islem(kod: bytes, p: int):
        o = _Okur(kod, p)
        k = o.u8()
        if k not in ISLEMLER:
            raise OkumaHatasi("bilinmeyen işlem kodu 0x%02x @%d" % (k, p))
        ad, bicim = ISLEMLER[k]
        isl, hedefler = [], []
        for b in bicim:
            if b == "u30":
                isl.append(o.u30())
            elif b == "u8":
                isl.append(o.u8())
            elif b == "s24":
                hedefler.append(o.s24())
            else:  # lookupswitch: varsayılan, durum sayısı, durum+1 uzaklık; hepsi işlemin başına göre
                varsayilan = o.s24()
                n = o.u30()
                hedefler = [p + varsayilan] + [p + o.s24() for _ in range(n + 1)]
                isl.append(n)
        if ad != "lookupswitch":
            hedefler = [o.p + h for h in hedefler]
        return Islem(p, ad, tuple(isl), o.p, tuple(hedefler))

    def coz(self, govde: Govde) -> dict:
        """Akışı izleyerek erişilebilen işlemler: ofset -> Islem.

        Başlangıç ofset 0 ve istisna yakalayıcılarıdır. Koşullu dallarda iki yol, lookupswitch'te bütün
        durumlar izlenir; jump ve bitiren işlemlerden sonra okuma durur. Böylece gizlenmiş koddaki
        atlanan anlamsız baytlar hiç çözülmez.
        """
        kod = govde.kod
        islemler = {}
        bekleyen = [0] + [x[2] for x in govde.istisnalar]
        while bekleyen:
            p = bekleyen.pop()
            while 0 <= p < len(kod) and p not in islemler:
                isl = self._islem(kod, p)
                islemler[p] = isl
                if isl.ad == "jump":
                    bekleyen.extend(isl.hedefler)
                    break
                if isl.ad == "lookupswitch":
                    bekleyen.extend(isl.hedefler)
                    break
                if isl.ad in BITIRIR:
                    break
                bekleyen.extend(isl.hedefler)
                p = isl.sonraki
        return islemler

    def deger(self, isl: Islem):
        """Sabit itiş işleminin değeri (değilse None)."""
        if isl.ad == "pushstring":
            return self.dize(isl.isl[0])
        if isl.ad in ("pushbyte",):
            x = isl.isl[0]
            return x - 256 if x > 127 else x
        if isl.ad == "pushshort":
            x = isl.isl[0] & 0xFFFF
            return x - 65536 if x > 32767 else x
        if isl.ad == "pushint":
            return self.tamsayilar[isl.isl[0]]
        if isl.ad == "pushuint":
            return self.isaretsizler[isl.isl[0]]
        if isl.ad == "pushdouble":
            return self.ondaliklar[isl.isl[0]]
        return {"pushtrue": True, "pushfalse": False, "pushnull": None}.get(isl.ad, None)

    # --- simgesel yığın ---

    def _yigin_etkisi(self, isl: Islem, yigin: list, yereller: dict = None):
        """İşlemi simgesel yığına uygular. Değerler okunur ifadelerdir (str) ya da sabitlerdir
        (Sabit), diziler Dizi'dir, nesneler Nesne'dir. Etkisi bilinmeyen işlemde yığın boşaltılır.

        `yereller` verilirse yerel değişkene yazılan dizi ve nesne değerleri tutulur ve okununca yerine
        konur (`var o = {cmd: ..., args: [...]}; addCommand(o)`). Akıştan bağımsızdır: son yazılan geçer.
        """
        a, x = isl.ad, isl.isl
        if yereller is None:
            yereller = {}

        def al(n):
            if n <= 0:
                return []
            if len(yigin) < n:
                eksik = n - len(yigin)
                cikan = ["?"] * eksik + yigin[:]
                del yigin[:]
                return cikan
            cikan = yigin[-n:]
            del yigin[-n:]
            return cikan

        if a.startswith("push") and a not in ("pushscope", "pushwith", "pushnamespace"):
            yigin.append(Sabit(self.deger(isl)) if a != "pushundefined" else Sabit(Tanimsiz))
        elif a == "pushnamespace":
            yigin.append("ns")
        elif a.startswith("getlocal"):
            n = x[0] if a == "getlocal" else int(a[-1])
            yigin.append(yereller.get(n, "this" if n == 0 else "yerel%d" % n))
        elif a.startswith("setlocal"):
            n = x[0] if a == "setlocal" else int(a[-1])
            v = al(1)[0]
            if isinstance(v, (Dizi, Nesne)):
                yereller[n] = v
            else:
                yereller.pop(n, None)
        elif a in ("pop",
                   "pushscope", "pushwith", "iftrue", "iffalse", "lookupswitch", "returnvalue", "throw",
                   "setglobalslot", "dxnslate"):
            al(1)
        elif a in ("getlex", "findpropstrict", "findproperty", "finddef"):
            al(self.calisma_anli(x[0]))
            yigin.append(self.ad(x[0]) if a == "getlex" else Bulunan(self.ad(x[0])))
        elif a == "getproperty":
            ad = al(1 + self.calisma_anli(x[0]))
            nesne = ad[0]
            yigin.append(_alan(nesne, self.ad(x[0]), ad[1:]))
        elif a in ("setproperty", "initproperty", "setsuper"):
            v = al(2 + self.calisma_anli(x[0]))
            if isinstance(v[0], Nesne) and len(v) == 2 and self.ad(x[0]) != "[]":
                # yereldeki nesneye alan yazımı: o.cmd = ...; o.args = [...]
                anahtar = Sabit(self.ad(x[0]))
                v[0][:] = [(k, d) for k, d in v[0] if k != anahtar] + [(anahtar, v[1])]
        elif a in ("deleteproperty", "getsuper", "getdescendants"):
            al(1 + self.calisma_anli(x[0]))
            yigin.append("?")
        elif a in ("callproperty", "callproplex", "callpropvoid", "callsuper", "callsupervoid",
                   "constructprop"):
            args = al(x[1])
            rt = al(self.calisma_anli(x[0]))
            nesne = al(1)[0]
            ifade = "%s.%s(%s)" % (_yaz(nesne), self.ad(x[0]), ", ".join(_yaz(v) for v in args))
            if a == "constructprop":
                if self.ad(x[0]) == "Object" and not args:
                    yigin.append(Nesne())
                    return None
                ifade = "new " + ifade
            if a not in ("callpropvoid", "callsupervoid"):
                yigin.append(ifade)
            return ("cagri", self.ad(x[0]), nesne, args, rt)
        elif a in ("callmethod", "callstatic"):
            al(x[1] + 1)
            yigin.append("?")
        elif a == "call":
            al(x[0] + 2)
            yigin.append("?")
        elif a == "construct":
            al(x[0] + 1)
            yigin.append("?")
        elif a == "constructsuper":
            al(x[0] + 1)
        elif a == "newarray":
            yigin.append(Dizi(al(x[0])))
        elif a == "newobject":
            ogeler = al(2 * x[0])
            yigin.append(Nesne(list(zip(ogeler[0::2], ogeler[1::2]))))
        elif a in ("newfunction", "newactivation", "getglobalscope", "getscopeobject", "getouterscope",
                   "getglobalslot"):
            yigin.append("?")
        elif a in ("coerce", "astype"):
            yigin.append(al(1)[0])  # tür dönüşümü değeri değiştirmez
        elif a in ("newclass", "getslot", "istype"):
            al(1)
            yigin.append("?")
        elif a == "setslot":
            al(2)
        elif a == "dup":
            v = al(1)[0]
            yigin.extend([v, v])
        elif a == "swap":
            v = al(2)
            yigin.extend([v[1], v[0]])
        elif a in ("convert_s", "convert_i", "convert_u", "convert_d", "convert_b", "convert_o",
                   "coerce_a", "coerce_s", "coerce_i", "coerce_d", "coerce_b", "coerce_u", "coerce_o",
                   "checkfilter", "kill", "label", "nop", "debug", "debugline", "debugfile", "bkpt",
                   "bkptline", "timestamp", "inclocal", "declocal", "inclocal_i", "declocal_i",
                   "jump", "returnvoid", "popscope", "dxns"):
            pass
        elif a in ("negate", "increment", "decrement", "typeof", "not", "bitnot", "increment_i",
                   "decrement_i", "negate_i", "esc_xelem", "esc_xattr", "sxi1", "sxi8", "sxi16",
                   "li8", "li16", "li32", "lf32", "lf64"):
            v = al(1)[0]
            yigin.append("%s(%s)" % (a, _yaz(v)))
        elif a in ("add", "subtract", "multiply", "divide", "modulo", "lshift", "rshift", "urshift",
                   "bitand", "bitor", "bitxor", "equals", "strictequals", "lessthan", "lessequals",
                   "greaterthan", "greaterequals", "instanceof", "istypelate", "astypelate", "in",
                   "add_i", "subtract_i", "multiply_i", "nextname", "nextvalue", "hasnext"):
            v = al(2)
            isaret = {"add": "+", "subtract": "-", "multiply": "*", "divide": "/", "modulo": "%",
                      "add_i": "+", "subtract_i": "-", "multiply_i": "*"}.get(a)
            yigin.append("(%s %s %s)" % (_yaz(v[0]), isaret, _yaz(v[1])) if isaret
                         else "%s(%s, %s)" % (a, _yaz(v[0]), _yaz(v[1])))
        elif a in KOSULLU:
            al(2)
        elif a in ("si8", "si16", "si32", "sf32", "sf64"):
            al(2)
        elif a == "hasnext2":
            yigin.append("?")
        elif a == "applytype":
            al(x[0] + 1)
            yigin.append("?")
        elif a == "newcatch":
            yigin.append("?")
        else:
            del yigin[:]
        return None

    def bloklar(self, islemler: dict):
        """Temel blokların başlangıç ofsetleri: 0, dal hedefleri ve dal ya da bitiren işlemden sonrası."""
        baslar = {0}
        for isl in islemler.values():
            if isl.hedefler or isl.ad in BITIRIR:
                baslar.update(isl.hedefler)
                baslar.add(isl.sonraki)
        return baslar

    def cagrilar(self, ad: str, yontem: int = None):
        """`ad` adlı özelliğe yapılan çağrılar (Cagri listesi). Argümanlar simgesel ifadelerdir.

        İşlemler ofset sırasıyla işlenir. Bir bloğun giriş yığını, ona ilk ulaşan dalın ya da düz
        geçişin yığınıdır (ileri dallarda ?: gibi ifadeler böylece korunur); bilinmiyorsa boştur.
        İstisna yakalayıcısı yığında yakalanan hatayla başlar.
        """
        if ad not in self.dizeler:
            return []
        cikti = []
        govdeler = [self.govdeler[yontem]] if yontem is not None else self.govdeler.values()
        for g in govdeler:
            islemler = self.coz(g)
            baslar = self.bloklar(islemler)
            giris = {}
            for x in g.istisnalar:
                baslar.add(x[2])
                giris[x[2]] = ["hata"]
            yigin, onceki, yereller = [], None, {}
            for p in sorted(islemler):
                if p in baslar:
                    if onceki is not None and onceki.sonraki == p and onceki.ad not in BITIRIR and                             onceki.ad not in ("jump", "lookupswitch"):
                        giris.setdefault(p, yigin)
                    yigin = list(giris.get(p, []))
                isl = islemler[p]
                sonuc = self._yigin_etkisi(isl, yigin, yereller)
                for h in isl.hedefler:
                    if h > p:
                        giris.setdefault(h, list(yigin))
                if sonuc and sonuc[1] == ad:
                    cikti.append(Cagri(g.yontem, p, ad, list(sonuc[3])))
                onceki = isl
        return cikti

    def sabitler(self, sinif: str) -> dict:
        """Sınıfın değeri derlemede yazılmış statik sabitleri: ad -> değer (dize, sayı)."""
        cikti = {}
        for i, ornek in enumerate(self.ornekler):
            if self.ad(ornek["ad"]) != sinif:
                continue
            for k in self.siniflar[i][1]:
                if k[0] in (0, 6) and k[4]:
                    cikti[self.ad(k[1])] = self._yuva_degeri(k[4], k[5])
        return cikti

    def _yuva_degeri(self, i, tur):
        return {0x01: lambda: self.dize(i), 0x03: lambda: self.tamsayilar[i],
                0x04: lambda: self.isaretsizler[i], 0x06: lambda: self.ondaliklar[i],
                0x0A: lambda: False, 0x0B: lambda: True, 0x0C: lambda: None}.get(tur, lambda: "?")()


class _Tanimsiz:
    def __repr__(self):
        return "undefined"


Tanimsiz = _Tanimsiz()


class Sabit:
    __slots__ = ("deger",)

    def __init__(self, deger):
        self.deger = deger

    def __repr__(self):
        return repr(self.deger) if self.deger is not Tanimsiz else "undefined"

    def __eq__(self, o):
        return isinstance(o, Sabit) and o.deger == self.deger

    def __hash__(self):
        return hash(("Sabit", repr(self.deger)))


class Bulunan(str):
    """findpropstrict'in bulduğu kapsam nesnesi; üstünde çağrılan adın sahibi."""


class Dizi(list):
    pass


class Nesne(list):
    pass


def _alan(nesne, ad, rt):
    if isinstance(nesne, Bulunan):
        return ad
    if isinstance(nesne, Nesne):  # {g: x, w: y}.g -> x
        for k, d in nesne:
            if k == Sabit(ad):
                return d
    if ad == "[]":
        return "%s[%s]" % (_yaz(nesne), _yaz(rt[-1]) if rt else "?")
    return "%s.%s" % (_yaz(nesne), ad)


def _yaz(v) -> str:
    if isinstance(v, Sabit):
        return repr(v)
    if isinstance(v, Dizi):
        return "[%s]" % ", ".join(_yaz(x) for x in v)
    if isinstance(v, Nesne):
        return "{%s}" % ", ".join("%s: %s" % (_yaz(k), _yaz(d)) for k, d in v)
    if isinstance(v, Bulunan):
        return "<%s>" % v
    return str(v)


yaz = _yaz


def swf_abc(veri: bytes):
    """SWF'deki her DoABC etiketi için Abc nesnesi."""
    return [Abc(b) for _, b in abc_etiketleri(veri)]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("swf")
    ap.add_argument("--cagri", help="bu adlı özelliğe yapılan çağrıları yaz")
    a = ap.parse_args(argv)
    with open(a.swf, "rb") as f:
        veri = f.read()
    for i, abc in enumerate(swf_abc(veri)):
        print("ABC %d: %d.%d, %d dize, %d çok adlı, %d yöntem, %d gövde, %d sınıf" % (
            i, abc.buyuk, abc.kucuk, len(abc.dizeler) - 1, len(abc.coklu_adlar) - 1,
            len(abc.yontemler), len(abc.govdeler), len(abc.ornekler)))
        if a.cagri:
            adlar = abc.yontem_adlari()
            for c in abc.cagrilar(a.cagri):
                print("  %s @%d: %s(%s)" % (adlar.get(c.yontem, "yontem%d" % c.yontem), c.ofset, c.ad,
                                            ", ".join(_yaz(v) for v in c.argumanlar)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
