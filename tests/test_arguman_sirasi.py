"""Argüman sırası sözleşmesi: işleyici, istemcinin gönderdiği kasaba ve koordinatı doğru sıradan okuyor mu?

Beklenen sıra uygulamadan değil istemcinin bayt kodundan gelir: `docs/inceleme/1407-komutlar.md` her komut için
gerçek bir çağrı yerinin argüman ifadelerini yazar (`araclar/komut_imzalari.py` üretir, elle düzenlenmez). Ör. `kill`:
`[...tx, ...ty, ...building.id, Base.Main.townID, ...type]`.

Neden: mutasyon ölçümünde (docs/TEST_OLCUMU.md) kalan mutantların en kalabalık türü argüman sırasının bozulmasıydı
(`a.tam(2)` yerine `a.tam(1)`). Eski testler tek kasaba ve x = y olan eşyalarla (10,10), (20,20) yazıldığı için
bunları göremiyordu. Burada her argümana ayrı bir değer verilir; ikinci kasaba vardır ve x ≠ y'dir.

Sınama: `harita`, `esya_bul` ve `esya_ekle` izlenir. İstemci kasaba gönderiyorsa her `harita` çağrısı o kasabayı
almalı; her (x, y) çifti bir `esya_bul`/`esya_ekle` çağrısına aynı sırayla gitmeli; çiftin eşya id'si de
gönderiliyorsa `esya_bul` onu (ya da hiç id) almalı.
"""

import contextlib
import io
import os
import re
import unittest

import ortak

MD = os.path.join(ortak.KOK, "docs", "inceleme", "1407-komutlar.md")
KASABA = 1
CIFTLER = [(37, 41), (53, 59)]  # x ≠ y; kasaba ve id'lerden farklı
IDLER = [131, 134]  # oyunda var olan iki bina (Ancient Ceramic, Troll Hut)

# İstemci kasabayı ya da koordinatı gönderiyor ama sınanan yolda gerekmiyor (gerekçesiyle). Bunlarda yalnızca
# yanlış kasaba okunmaması sınanır.
GEREKMEZ = {
    "reward_viral_offer": "yalnızca 'ödül verildi' işareti; birimi istemci store_add_items ile ayrıca bildirir",
    "pop_queue_unit": "kasaba göndermez (açık kasaba); dolu kuyruk ister. Koordinat sırası "
                      "test_komutlar.EgitimKuyrugu.test_cikan_birim_haritaya_xp_ve_zincir'de x ≠ y ile sınanır",
    "buy_mana_new": "nakitle alım (istemcinin bu çağrısı) kaynağa dokunmaz; altınla alımda kasaba okunur",
    "buy_map": "nakitle alım; altınla alımda kasaba okunur",
    "buy_stored_item_cash": "depo (gifts) kasabadan bağımsız",
    "buy_super_offer_pack": "yalnızca depo ve nakit; kasabadan bağımsız",
    "name_map": "ad playerInfo.map_names[kasaba]'ya yazılır, harita okunmaz (test_ad_dogru_kasabaya)",
}
# İstemcinin geçerli göndereceği ama çağrı ifadesinden çıkmayan değerler: {komut: {sıra: değer}}
GECERLI_DEGER = {
    "buy_magic": {0: 2},  # this.spell.id: oyundaki ilk büyü
    "buy_offer_pack": {1: 2},  # paket id'si (yerel1): oyundaki 2. paket
    "finish_si_recruitment": {4: 1},  # yerel3.id: recruitment_prices'taki ilk ödül
}


def bol(metin):
    """Üst düzey virgüllerle böler (parantez, köşeli ayraç, süslü ayraç ve tırnak içi bölünmez)."""
    parcalar, derinlik, simdiki, tirnak = [], 0, "", None
    for ch in metin:
        if tirnak:
            simdiki += ch
            tirnak = None if ch == tirnak else tirnak
            continue
        if ch in "'\"":
            tirnak = ch
        elif ch in "([{":
            derinlik += 1
        elif ch in ")]}":
            derinlik -= 1
        elif ch == "," and derinlik == 0:
            parcalar.append(simdiki.strip())
            simdiki = ""
            continue
        simdiki += ch
    if simdiki.strip():
        parcalar.append(simdiki.strip())
    return parcalar


def istemci_ornekleri():
    ornekler = {}
    with open(MD, encoding="utf-8") as f:
        for satir in f:
            m = re.match(r"\| `([a-z_0-9]+)` \|.*\| ([A-Za-z_$]+/[A-Za-z_$]+@\d+): \[(.*)\] \|\s*$", satir)
            if m:
                ornekler[m.group(1)] = (m.group(2), bol(m.group(3)))
    return ornekler


X_IFADESI = re.compile(r"^(?P<ref>.*?)\.(o?tx|iLastPosSentToServerX)$|^\(?(?P<yer>yerel\d+) % Config\.EI_MAP_WIDTH\)?$")
Y_IFADESI = re.compile(r"^(?P<ref>.*?)\.(o?ty|iLastPosSentToServerY)$|^<int>\.int\(\((?P<yer>yerel\d+) / Config\.EI_MAP_WIDTH\)\)$")


def roller(args):
    """Argüman ifadelerinden roller: kasaba sırası, (x sırası, y sırası, id sırası ya da None) çiftleri."""
    kasaba = [i for i, a in enumerate(args) if a.endswith("townID")]
    xler = [(i, X_IFADESI.match(a)) for i, a in enumerate(args) if X_IFADESI.match(a)]
    yler = [(i, Y_IFADESI.match(a)) for i, a in enumerate(args) if Y_IFADESI.match(a)]
    ciftler = []
    for (xi, xm), (yi, ym) in zip(xler, yler):
        ref = xm.group("ref") or xm.group("yer")
        if (ym.group("ref") or ym.group("yer")) != ref:
            raise ValueError(f"eşleşmeyen koordinat çifti: {args[xi]} / {args[yi]}")
        kok = re.sub(r"\.buildingReference$", "", ref)
        idler = [i for i, a in enumerate(args) if a in (f"{kok}.building.id", f"{kok}.buildingReference.building.id")]
        ciftler.append((xi, yi, idler[0] if len(idler) == 1 else None))
    return (kasaba[0] if kasaba else None), ciftler


def sinama_argumanlari(ad, args, kasaba, ciftler):
    """Her argümana ayrı değer: roller sabit değerlerini, düz sabitler kendilerini alır. Gerisi oyunda var olan bir
    bina id'si alır (çoğu id'dir; geçersiz id işleyiciyi erken döndürür, okunacak argümana varılmaz)."""
    degerler = []
    for a in args:
        if re.fullmatch(r"-?\d+", a):
            degerler.append(int(a))
        elif re.fullmatch(r"'[^']*'", a):
            degerler.append(a[1:-1])
        else:
            degerler.append(IDLER[0])
    if kasaba is not None:
        degerler[kasaba] = KASABA
    for n, (xi, yi, ii) in enumerate(ciftler):
        degerler[xi], degerler[yi] = CIFTLER[n]
        if ii is not None:
            degerler[ii] = IDLER[n]
    for sira, deger in GECERLI_DEGER.get(ad, {}).items():
        degerler[sira] = deger
    return degerler


class ArgumanSirasi(ortak.KomutTesti):
    def _kayit_kur(self):
        """İki kasabalı, depoda iki binası olan yeni kayıt (her komut kendi kaydında koşar)."""
        kayit = ortak.bos_kayit()
        ikinci = ortak.bos_kayit()["maps"][0]
        ikinci["id"] = 1
        kayit["maps"].append(ikinci)
        for h in kayit["maps"]:
            h["items"].append([150, 5, 9, 0, 0, 0])  # kahraman sunağı: buy_cash kahramanı ancak sunak varsa koyar
        kayit["playerInfo"]["map_names"].append("İkinci")
        kayit["playerInfo"]["map_sizes"].append(0)
        kayit["privateState"]["gifts"] = [0] * IDLER[1] + [1]  # depodan yerleştirme ve satma için
        kayit["privateState"]["gifts"][IDLER[0]] = 1
        self.kayitlar["test"] = kayit
        return kayit

    def setUp(self):
        super().setUp()
        self.cagrilar = []
        k = self.komutlar
        self._asil = (k.harita, k.esya_bul, k.esya_ekle)
        harita, esya_bul, esya_ekle = self._asil

        def harita_izle(save, town_id):
            self.cagrilar.append(("harita", town_id))
            return harita(save, town_id)

        def esya_bul_izle(h, x, y, esya_id=None):
            self.cagrilar.append(("bul", x, y, esya_id))
            return esya_bul(h, x, y, esya_id)

        def esya_ekle_izle(h, esya_id, x, y, yon=0):
            self.cagrilar.append(("ekle", x, y, esya_id))
            return esya_ekle(h, esya_id, x, y, yon)

        k.harita, k.esya_bul, k.esya_ekle = harita_izle, esya_bul_izle, esya_ekle_izle

    def tearDown(self):
        self.komutlar.harita, self.komutlar.esya_bul, self.komutlar.esya_ekle = self._asil
        super().tearDown()

    def test_istemcinin_kasaba_ve_koordinat_sirasi(self):
        ornekler = istemci_ornekleri()
        self.assertGreater(len(ornekler), 140)  # belge okunamazsa sınama boşa geçmesin
        sinanan = 0
        for ad, (yer, args) in sorted(ornekler.items()):
            if ad not in self.komutlar.KOMUTLAR:
                continue
            kasaba, ciftler = roller(args)
            if kasaba is None and not ciftler:
                continue
            isleyici = self.komutlar.KOMUTLAR[ad]
            if isleyici is self.komutlar.KOMUTLAR["ping"]:
                continue  # kaydı değiştirmeyen komutlar (kayitsiz) argüman okumaz
            with self.subTest(komut=ad, cagri=yer):
                sinanan += 1
                self.cagrilar.clear()
                degerler = sinama_argumanlari(ad, args, kasaba, ciftler)
                with contextlib.redirect_stdout(io.StringIO()):
                    try:
                        isleyici(self._kayit_kur(), self.komutlar.Arg(degerler))
                    except Exception:  # noqa: BLE001 - sözleşme, işleyicinin okuduğu argümanlarla sınanır
                        pass
                kasabalar = [c[1] for c in self.cagrilar if c[0] == "harita"]
                if kasaba is not None and ad not in GEREKMEZ:
                    self.assertTrue(kasabalar, f"{ad}: istemci kasabayı {kasaba}. sırada gönderiyor, okunmadı")
                if kasaba is not None:
                    self.assertLessEqual(set(kasabalar), {KASABA}, f"{ad}: argümanlar {degerler}")
                for n, (xi, yi, ii) in enumerate([] if ad in GEREKMEZ else ciftler):
                    x, y = CIFTLER[n]
                    eslesen = [c for c in self.cagrilar if c[0] in ("bul", "ekle") and c[1:3] == (x, y)]
                    self.assertTrue(eslesen, f"{ad}: ({x}, {y}) aranmadı/eklenmedi; çağrılar {self.cagrilar}")
                    if ii is not None:
                        self.assertTrue(all(c[3] in (IDLER[n], None) for c in eslesen if c[0] == "bul"),
                                        f"{ad}: id {IDLER[n]} bekleniyordu; çağrılar {eslesen}")
        self.assertGreater(sinanan, 30)

    def test_ad_dogru_kasabaya(self):
        # EnterNamePopUp/setTownName: [Base.Main.townID, inputText.text]
        kayit = self._kayit_kur()
        self.komutlar.KOMUTLAR["name_map"](kayit, self.komutlar.Arg([KASABA, "Yeni"]))
        self.assertEqual(kayit["playerInfo"]["map_names"], ["Test", "Yeni"])


if __name__ == "__main__":
    unittest.main()
