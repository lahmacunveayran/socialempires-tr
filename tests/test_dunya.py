"""Yaşayan dünya (oyun/dunya.py): bot ekonomisi, akınlar, seferler, olaylar, panel verisi.

Bot dünyası bizim özelliğimiz; istemcide kâhini yok. Beklenen değerler uygulamanın çıktısından alınmaz, kaynakları:
  - modülün belge dizeleri ve yorumları (dosya/satır anılır),
  - docs/gorev/BULGULAR.json kararları: OYN-01 (ittifak, sefer 12 turda en çok 3 akın, en güçlü uygun üye, 6 saat
    kuralı, oyuncuya akınlar kalkana ve aralığa saygılı), denetim kaydı (bot kayıtları 5 turda bir yazılır),
  - oyun config'i (birim bedeli, seviye eşikleri, sosyal binaların işçi sayısı),
  - denge.py (ganimet en fazla %10, kaynak başına tavan; 6 saatte 3 saldırı),
  - değişmezler (kaynak eksiye düşmez, ganimet korunur, rapor kayıtla tutarlı...).
Rastgelelik sabit tohumla ya da yamayla belirlenir; saat dunya.time yamasıyla sabittir.
"""

import contextlib
import random
import types
import unittest
from unittest import mock

from ortak import bos_kayit
from oyun import denge, dunya
from oyun.config import get_game_config

SIMDI = 2_000_000_000
SOVALYE = 512        # Light Knight (config: u, attack 10, life 60, cost 75)
KULE_V = 33          # Tower V (config: b, attack 16)
KULE_I = 29          # Tower I (config: b, attack 4)
BUZ_KULESI = 384     # Ice Tower (config: b, attack 1)
EV = 1               # House I (config: b, attack 0)
SOSYAL = 6           # Mill II: config social_items, worker_cost 2

AYAR = dict(aktif=True, tick_saniye=60, saldiri_olasiligi=0, oyuncuya_saldiri=0, intikam_olasiligi=0,
            oyuncuya_intikam=0, olay_saklama=200, tur_basina_saldiri=8, bot_saldiri_araligi=180,
            oyuncu_saldiri_araligi=600)


def esya(esya_id, i=0):
    return [esya_id, 10 + i % 40, 10 + i // 40, 0, 0, 0, [], {}]


def koy(pid, seviye=10, birim=0, binalar=(), bot=True, ittifak=None, **kaynak):
    k = bos_kayit(pid)
    k["playerInfo"].update(name=f"Köy {pid}", bot=bot)
    h = k["maps"][0]
    h["level"] = seviye
    h["items"] = [esya(SOVALYE, i) for i in range(birim)] + [esya(b, 100 + i) for i, b in enumerate(binalar)]
    h.update(kaynak)
    if ittifak is not None:
        k["privateState"]["bot_hafiza"] = {"ittifak": ittifak}
    return k


def birim(kayit):
    """Haritadaki birim sayısı; birim olduğu config'teki türünden ('u')."""
    turler = {int(i["id"]): i.get("type") for i in get_game_config()["items"]}
    return sum(1 for e in kayit["maps"][0]["items"] if turler.get(int(e[0])) == "u")


KAYNAKLAR = ("coins", "wood", "stone", "food")


class DunyaTesti(unittest.TestCase):
    def kur(self, **kayitlar):
        """Kayıtlar bellekte; save_session yazılanları toplar; saat SIMDI; zaman ölçeği 1."""
        self.kayitlar, self.yazilan = kayitlar, []
        for ad, deger in (("all_saves_userid", lambda: list(self.kayitlar)), ("session", self.kayitlar.get),
                          ("save_session", self.yazilan.append), ("zaman_olcegi", lambda: 1.0),
                          ("time", types.SimpleNamespace(time=lambda: SIMDI, sleep=lambda s: None))):
            yama = mock.patch.object(dunya, ad, deger)
            yama.start()
            self.addCleanup(yama.stop)
        random.seed(20261105)
        d = dunya.Dunya()
        d.ayar.update(AYAR)
        return d

    def secilen(self, d, saldiran_id, sira, f=None):
        """_akin'in seçtiği hedef (savaş çözülmez). f verilirse random.uniform(a, b) = a + f·(b − a)."""
        botlar = [(u, self.kayitlar[u]) for u in sira]
        with mock.patch.object(d, "_savas", side_effect=lambda sid, s, hid, h, simdi, oyuncuya=False: hid):
            if f is None:
                return d._akin(saldiran_id, self.kayitlar[saldiran_id], botlar, SIMDI)
            with mock.patch.object(dunya.random, "uniform", side_effect=lambda a, b: a + f * (b - a)):
                return d._akin(saldiran_id, self.kayitlar[saldiran_id], botlar, SIMDI)


class GucTestleri(unittest.TestCase):
    """ordu_gucu / kule_gucu / birim_sil: belge dizeleri ve toplanabilirlik."""

    def test_ordu_gucu_birim_basina_toplanir_ve_istatistikle_artar(self):
        self.assertEqual(dunya.ordu_gucu({}), 0)
        tek = dunya.ordu_gucu({SOVALYE: 1})
        self.assertGreater(tek, 0)
        self.assertAlmostEqual(dunya.ordu_gucu({SOVALYE: 3}), 3 * tek)
        self.assertAlmostEqual(dunya.ordu_gucu({SOVALYE: 1, 516: 2}), tek + dunya.ordu_gucu({516: 2}))
        # Config'te karşılığı olmayan (istatistiksiz) birim güç katmaz; saldırı da can da gücü artırır.
        sahte = {-1: {}, -2: {"attack": 10}, -3: {"attack": 20}, -4: {"life": 100}}
        with mock.patch.dict(dunya._ITEM_CACHE, sahte):
            self.assertEqual(dunya.ordu_gucu({-1: 5}), 0)
            self.assertGreater(dunya.ordu_gucu({-2: 1}), 0)
            self.assertGreater(dunya.ordu_gucu({-3: 1}), dunya.ordu_gucu({-2: 1}))
            self.assertGreater(dunya.ordu_gucu({-4: 1}), 0)

    def test_kule_gucu_yalniz_saldirili_binalardan(self):
        """Belge dizesi: 'Savunma binalarının (kule vb.) ek gücü'. Birim, ev, çiçek savunma binası değildir."""
        self.assertEqual(dunya.kule_gucu(koy("a")), 0)
        self.assertEqual(dunya.kule_gucu(koy("a", birim=5, binalar=[EV])), 0)
        self.assertGreater(dunya.kule_gucu(koy("a", binalar=[BUZ_KULESI])), 0)  # saldırısı 1 olan kule de sayılır
        bir = dunya.kule_gucu(koy("a", binalar=[KULE_I]))
        self.assertGreater(bir, 0)
        self.assertAlmostEqual(dunya.kule_gucu(koy("a", birim=3, binalar=[KULE_I, KULE_I, EV])), 2 * bir)

    def test_birim_sil_istenen_kadar_ve_yalniz_birim(self):
        """Belge dizesi: '{id: adet} kadar birimi haritadan siler'; bina birim değildir, eksiye inilmez."""
        k = koy("a", birim=3, binalar=[KULE_I, EV])
        k["maps"][0]["items"] += [esya(516, 60), esya(516, 61)]
        say = lambda esya_id: sum(1 for e in k["maps"][0]["items"] if e[0] == esya_id)  # noqa: E731
        kalan = dunya.birim_sil(k, {SOVALYE: 2, KULE_I: 1})
        self.assertEqual((say(SOVALYE), say(516), say(KULE_I)), (1, 2, 1))  # istenmeyen birim ve bina kalır
        self.assertEqual(kalan, {SOVALYE: 0, KULE_I: 1})
        self.assertEqual(dunya.birim_sil(k, {SOVALYE: 5}), {SOVALYE: 4})  # bir tane vardı, 4'ü silinemedi
        self.assertEqual((say(SOVALYE), say(516)), (0, 2))

    def test_rapor_listesi_sinirli_ve_en_yenisi_kalir(self):
        hedef, saldiran = koy("v"), koy("a")
        for t in range(120):
            dunya.rapor_ekle(hedef, saldiran, {"time": t})
        liste = hedef["privateState"]["attacksReceived"]
        self.assertLess(len(liste), 120)
        self.assertEqual(liste[-1]["description"]["time"], 119)
        self.assertEqual((liste[-1]["viewPending"], liste[-1]["attacker_id"]), (1, "a"))


class OlayKaydiTestleri(unittest.TestCase):
    def test_olay_saklama_siniri(self):
        """ayar olay_saklama: en çok bu kadar olay tutulur, en yeniler kalır; sınırın altındakiler silinmez."""
        d = dunya.Dunya()
        d.ayar["olay_saklama"] = 5
        for i in range(3):
            d.olay("savas", str(i))
        self.assertEqual([o["id"] for o in d.olaylar], [1, 2, 3])
        for i in range(5):
            d.olay("savas", str(i))
        self.assertEqual([o["id"] for o in d.olaylar], [4, 5, 6, 7, 8])

    def test_olaylar_sonra_en_cok_ve_varsayilan(self):
        """Belge dizesi: '`sonra` numaralı olaydan sonrakiler (eskiden yeniye)'; en_cok en fazla bu kadar."""
        d = dunya.Dunya()
        for i in range(10):
            d.olay("savas", str(i))
        self.assertEqual([o["id"] for o in d.olaylar_sonra()], list(range(1, 11)))
        self.assertEqual([o["id"] for o in d.olaylar_sonra(0, en_cok=4)], [7, 8, 9, 10])
        self.assertEqual([o["id"] for o in d.olaylar_sonra(8, en_cok=4)], [9, 10])
        self.assertEqual(d.olaylar_sonra(10), [])  # son numara: yeni olay yok
        # Yorum: 'sunucu yeniden başladı: istemcinin numarası geçersiz' -> baştan verilir.
        self.assertEqual([o["id"] for o in d.olaylar_sonra(999)], list(range(1, 11)))

    def test_turkce_ad(self):
        """Belge dizesi: 'Eşyanın Türkçe adı'; çevirisi yoksa config adı, o da yoksa kimliği."""
        ceviri = dunya._ceviriler().get(f"item:{SOVALYE}")
        self.assertTrue(ceviri)
        self.assertNotEqual(ceviri, "Light Knight")
        self.assertEqual(dunya.turkce_ad(SOVALYE), ceviri)
        with mock.patch.object(dunya, "_ceviriler", return_value={}):
            self.assertEqual(dunya.turkce_ad(SOVALYE), "Light Knight")
            self.assertEqual(dunya.turkce_ad(-999), "-999")


class DunyaOlayiTestleri(DunyaTesti):
    def test_sekiz_turda_bir_olay(self):
        """_dunya_olayi belge dizesi: 'Her 8 turda bir tüm dünyayı etkileyen bir olay'."""
        d = self.kur(a=koy("a"))
        for tur in range(1, 8):
            d.tick = tur
            d._dunya_olayi(SIMDI)
            self.assertIsNone(d.aktif_olay, tur)
        d.tick = 8
        d._dunya_olayi(SIMDI)
        self.assertIsNotNone(d.aktif_olay)
        self.assertEqual(d.olaylar[-1]["tur"], "dunya")
        # Olay süresi: bir tur sonra sürer, 8 tur sonraki olay turunda bitmiştir (yoksa 'her 8 turda bir' bozulur).
        d._olay_guncelle(SIMDI + 60)
        self.assertIsNotNone(d.aktif_olay)
        d._olay_guncelle(SIMDI + 8 * 60)
        self.assertIsNone(d.aktif_olay)
        self.assertIn("Son buldu", d.olaylar[-1]["metin"])

    def test_olay_turu_carpan_yonu(self):
        """Olay metinleri: savaş 'botlar daha saldirgan', bereket 'uretim artti', kriz 'uretim azaldi',
        ticaret 'altin akisi hizlandi'."""
        beklenen = {"savas": (lambda e, s: e == 1.0 and s > 1), "bereket": (lambda e, s: e > 1 and s == 1.0),
                    "kriz": (lambda e, s: e < 1 and s == 1.0), "ticaret": (lambda e, s: e > 1 and s == 1.0)}
        for tur, kosul in beklenen.items():
            d = self.kur(a=koy("a"), b=koy("b"))
            d.tick = 8
            with mock.patch.object(dunya.random, "choice", side_effect=lambda s: tur if "savas" in s else s[0]):
                d._dunya_olayi(SIMDI)
            self.assertEqual(d.aktif_olay["tur"], tur)
            self.assertTrue(kosul(d.ekonomi_carpan, d.savas_carpan), (tur, d.ekonomi_carpan, d.savas_carpan))

    def test_savas_olayi_botlari_ofkelendirir_oyuncuyu_degil(self):
        """Savaş olayı metni 'botlar daha saldirgan': her botun öfkesi artar; oyuncunun hafızasına dokunulmaz."""
        d = self.kur(a=koy("a"), b=koy("b"), c=koy("c"), p=koy("p", bot=False))
        d.tick = 8
        with mock.patch.object(dunya.random, "choice", side_effect=lambda s: "savas" if "savas" in s else s[0]):
            d._dunya_olayi(SIMDI)
        for u in "abc":
            ofke = self.kayitlar[u]["privateState"]["bot_hafiza"]["ofke"]
            self.assertGreater(sum(ofke.values()), 0, u)
        self.assertNotIn("bot_hafiza", self.kayitlar["p"]["privateState"])

    def test_olay_yokken_carpanlar_notr(self):
        """_olay_guncelle: olay sürerken çarpan korunur, bitince ve olay yokken 1'e döner."""
        d = dunya.Dunya()
        self.assertEqual((d.ekonomi_carpan, d.savas_carpan), (1.0, 1.0))
        d.aktif_olay, d.ekonomi_carpan, d.savas_carpan = {"bitis": SIMDI + 10, "metin": "x"}, 1.25, 1.25
        d._olay_guncelle(SIMDI)
        self.assertEqual((d.ekonomi_carpan, d.savas_carpan), (1.25, 1.25))
        d._olay_guncelle(SIMDI + 10)
        self.assertIsNone(d.aktif_olay)
        self.assertEqual((d.ekonomi_carpan, d.savas_carpan), (1.0, 1.0))


class EkonomiTestleri(DunyaTesti):
    def ekonomi(self, d, uid, rastgele, secim=None):
        """random.random sırayla `rastgele`yi döndürür (4 kaynak zarı, sonra birim zarı)."""
        with contextlib.ExitStack() as yigin:
            yigin.enter_context(mock.patch.object(dunya.random, "random", side_effect=rastgele))
            if secim:
                yigin.enter_context(mock.patch.object(dunya.random, "choice", side_effect=lambda s: secim))
            return d._ekonomi(uid, self.kayitlar[uid])

    def test_her_kaynak_uretilir_ve_uretim_stoktan_bagimsiz(self):
        """Köy her turda dört kaynağı da üretir (en düşük zarda bile); üretim depodaki miktara bağlı değil."""
        d = self.kur(a=koy("a", seviye=7, coins=10, wood=1000, stone=0, food=3),
                     b=koy("b", seviye=7, coins=900, wood=5000, stone=77, food=40000))
        once = {u: {k: self.kayitlar[u]["maps"][0][k] for k in KAYNAKLAR} for u in "ab"}
        for u in "ab":
            self.assertTrue(self.ekonomi(d, u, [0.0] * 4 + [0.99]))  # değişti: yazılacak
        artis = {u: {k: self.kayitlar[u]["maps"][0][k] - once[u][k] for k in KAYNAKLAR} for u in "ab"}
        self.assertTrue(all(v > 0 for v in artis["a"].values()), artis)
        self.assertEqual(artis["a"], artis["b"])

    def test_eksik_kaynak_sifirdan_baslar(self):
        d = self.kur(a=koy("a"))
        del self.kayitlar["a"]["maps"][0]["stone"]
        d.ekonomi_carpan = 0
        self.ekonomi(d, "a", [0.5] * 4 + [0.99])
        self.assertEqual(self.kayitlar["a"]["maps"][0]["stone"], 0)

    def test_birim_parasi_yetince_alinir(self):
        """Yorum 'Ara sıra yeni birim üret'; bedel config'ten (Light Knight cost 75). Altın eksiye düşmez."""
        bedel = int(dunya._item(SOVALYE)["cost"])
        self.assertEqual(bedel, 75)
        d = self.kur(a=koy("a", coins=bedel - 1), b=koy("b", coins=bedel), c=koy("c", coins=10**6))
        d.ekonomi_carpan = 0  # üretim sıfır: altını yalnızca alım değiştirir
        self.ekonomi(d, "a", [0.5] * 4 + [0.0], secim=SOVALYE)
        self.assertEqual((birim(self.kayitlar["a"]), self.kayitlar["a"]["maps"][0]["coins"]), (0, bedel - 1))
        self.ekonomi(d, "b", [0.5] * 4 + [0.0], secim=SOVALYE)
        self.assertEqual((birim(self.kayitlar["b"]), self.kayitlar["b"]["maps"][0]["coins"]), (1, 0))
        self.assertEqual(dunya.birim_sayilari(self.kayitlar["b"]), {SOVALYE: 1})
        self.ekonomi(d, "c", [0.5] * 4 + [0.99], secim=SOVALYE)  # zar tutmadı: alım yok
        self.assertEqual(birim(self.kayitlar["c"]), 0)

    def test_seviye_atlama_esik_altinda_yok_tavanda_son_seviye(self):
        """XP config eşiğinin altındaysa köy seviye atlamaz; tüm eşikleri aşan köy son seviyeye çıkar (1.4.07'de
        100 seviye: test_komutlar.test_seviye_siniri_asilirsa_son_seviye). Her atlama bir 'seviye' haberidir.
        Tam eşik bilerek sabitlenmez: config.get_level_from_xp levels[i]'yi (i+1). seviyenin eşiği sayar
        ('29 xp ile 2. seviye', test_komutlar), _ekonomi ise i. seviyenin; açık hata, rapora yazıldı."""
        esik = [int(s["exp_required"]) for s in get_game_config()["levels"]]
        son = len(esik) - 1
        self.assertEqual(son, 99)
        # 'a': iki kuralda da eşiğin altında. 'e', 't': tek ve çift başlangıç seviyesinden tavana.
        d = self.kur(a=koy("a", seviye=10, xp=esik[10] - 1), e=koy("e", seviye=son - 1, xp=esik[-1] + 1),
                     t=koy("t", seviye=son - 4, xp=10 ** 12), u=koy("u", seviye=son, xp=10 ** 12))
        d.ekonomi_carpan = 0
        for u in "aetu":
            self.ekonomi(d, u, [0.5] * 4 + [0.99])
        seviye = {u: self.kayitlar[u]["maps"][0]["level"] for u in "aetu"}
        self.assertEqual(seviye, {"a": 10, "e": son, "t": son, "u": son})
        haberler = [o["metin"] for o in d.olaylar if o["tur"] == "seviye"]
        self.assertEqual(sorted(haberler), [f"Köy e seviye {son} oldu", f"Köy t seviye {son} oldu"])

    def test_ekonomi_carpani_uretimi_yonlendirir(self):
        """Dünya olayı metinleri: bereket 'uretim artti', kriz 'uretim azaldi' (ekonomi_carpan). Aynı zarla
        büyük çarpan daha çok, küçük çarpan daha az üretir; zaman ölçeği (oyun hızı, zaman.py) de üretimi artırır."""
        uretim = {}
        for anahtar, carpan, olcek in (("kriz", 0.8, 1.0), ("notr", 1.0, 1.0), ("bereket", 1.25, 1.0),
                                       ("hizli", 1.0, 3.0)):
            d = self.kur(a=koy("a", seviye=10, coins=0, wood=0, stone=0, food=0))
            d.ekonomi_carpan = carpan
            with mock.patch.object(dunya, "zaman_olcegi", lambda: olcek):
                self.ekonomi(d, "a", [0.5] * 4 + [0.99])
            uretim[anahtar] = [self.kayitlar["a"]["maps"][0][k] for k in KAYNAKLAR]
        for k in range(4):
            self.assertLess(uretim["kriz"][k], uretim["notr"][k], uretim)
            self.assertLess(uretim["notr"][k], uretim["bereket"][k], uretim)
            self.assertLess(uretim["notr"][k], uretim["hizli"][k], uretim)

    def test_alinan_birim_gercek_birim_ve_bedeli_odenir(self):
        """Haber 'ordusuna bir X kattı': alınan eşya config'te birimdir (tür 'u', yoksa ordu sayılmaz) ve
        altından tam bedeli düşer (config cost). Seçim yamalanmaz: botun gerçek birim listesi denenir."""
        d = self.kur(a=koy("a", coins=10 ** 6))
        d.ekonomi_carpan = 0
        harita = self.kayitlar["a"]["maps"][0]
        random.seed(7)
        for _ in range(60):
            once_altin, once_esya = harita["coins"], len(harita["items"])
            self.ekonomi(d, "a", [0.5] * 4 + [0.0])
            yeni = harita["items"][once_esya:]
            self.assertEqual(len(yeni), 1)
            item = dunya._item(yeni[0][0])
            self.assertEqual(item.get("type"), "u", yeni[0][0])
            self.assertEqual(once_altin - harita["coins"], int(item["cost"]))
        self.assertEqual(birim(self.kayitlar["a"]), 60)
        self.assertEqual(len(d._ekonomi_haberleri), 60)
        self.assertTrue(all("ordusuna bir" in h for h in d._ekonomi_haberleri))


class HafizaTestleri(DunyaTesti):
    def test_ofke_sayar(self):
        d = self.kur(a=koy("a"))
        k = self.kayitlar["a"]
        self.assertEqual(d._ofke(k, "x"), 0)
        d._ofke_artir(k, "x")
        self.assertEqual(d._ofke(k, "x"), 1)
        d._ofke_artir(k, "x")
        self.assertEqual((d._ofke(k, "x"), d._ofke(k, "y")), (2, 0))

    def test_saldiri_hakki_ve_ayni_hedef_kurali(self):
        """denge: 6 saatte 3 saldırı (orijinal oyunun kuralı); _hedefe_uygun: aynı hedefe 6 saatte bir."""
        d = self.kur(a=koy("a"))
        k, p = self.kayitlar["a"], denge.SALDIRI_PERIYODU
        k["privateState"]["attacksSent"] = [{"time": SIMDI - 10}, {"time": SIMDI - 20}, {"time": SIMDI - p}]
        self.assertTrue(d._saldiri_hakki(k, SIMDI))
        k["privateState"]["attacksSent"].append({"time": SIMDI - p + 1})
        self.assertFalse(d._saldiri_hakki(k, SIMDI))
        k["privateState"]["bot_hafiza"] = {"son_hedef": {"id": "v", "zaman": SIMDI - 60}}
        self.assertFalse(d._hedefe_uygun(k, "v", SIMDI))
        self.assertTrue(d._hedefe_uygun(k, "w", SIMDI))
        self.assertTrue(d._hedefe_uygun(k, "v", SIMDI - 60 + p))


class SavasTestleri(DunyaTesti):
    def test_ganimet_korunur_sinirli_ve_raporla_tutarli(self):
        """denge: ganimet kurbanın kaynağının en fazla %10'u ve kaynak başına GANIMET_TAVANI. Kurbanın kaybı
        saldıranın kazancıdır; rapor (g, x), haber ve attacksSent gerçekleşenle aynıdır."""
        d = self.kur(a=koy("a", birim=20, ittifak=0, coins=0, wood=0, stone=0, food=0, xp=7),
                     v=koy("v", ittifak=1, coins=1_000_000, wood=1234, stone=0, food=5, xp=0))
        a, v = self.kayitlar["a"], self.kayitlar["v"]
        once_a, once_v = dict(a["maps"][0]), dict(v["maps"][0])
        self.assertEqual(d._savas("a", a, "v", v, SIMDI), "v")
        self.assertTrue(d._son_sonuc["kazandi"])  # savunmasız köy: kule yok, birim yok
        kayip = {}
        for k in KAYNAKLAR:
            kayip[k] = once_v[k] - v["maps"][0][k]
            self.assertEqual(kayip[k], a["maps"][0][k] - once_a[k], k)
            self.assertGreaterEqual(v["maps"][0][k], 0)
            self.assertLessEqual(kayip[k], min(once_v[k] * denge.GANIMET_ORANI, denge.GANIMET_TAVANI))
        self.assertGreater(kayip["coins"], 0)
        self.assertGreater(kayip["wood"], 0)
        rapor = v["privateState"]["attacksReceived"][-1]
        self.assertEqual((rapor["attacker_id"], rapor["viewPending"]), ("a", 1))
        r = rapor["description"]
        self.assertEqual((r["win"], r["time"], r["resources"]["g"]), (1, SIMDI, kayip["coins"]))
        self.assertEqual(r["resources"]["x"], a["maps"][0]["xp"] - 7)
        self.assertGreater(r["resources"]["x"], 0)
        self.assertEqual((r["oponent"]["user_id"], r["oponent"]["level"], r["oponent"]["name"]), ("a", 10, "Köy a"))
        self.assertIn(f"{sum(kayip.values())} kaynak ganimet", d.olaylar[-1]["metin"])
        self.assertEqual(d._son_sonuc, {"kazandi": True, "ganimet": sum(kayip.values())})
        self.assertEqual(a["privateState"]["attacksSent"][-1], {"victim_id": "v", "time": SIMDI})
        self.assertEqual(a["privateState"]["bot_hafiza"]["son_hedef"], {"id": "v", "zaman": SIMDI})

    def test_altini_olmayandan_altin_alinmaz(self):
        d = self.kur(a=koy("a", birim=20, ittifak=0), v=koy("v", ittifak=1, coins=0))
        d._savas("a", self.kayitlar["a"], "v", self.kayitlar["v"], SIMDI)
        self.assertEqual(self.kayitlar["v"]["privateState"]["attacksReceived"][-1]["description"]["resources"]["g"], 0)
        self.assertEqual(self.kayitlar["v"]["maps"][0]["coins"], 0)

    def test_kayiplar_silinir_kazanan_daha_az_kaybeder_ofke(self):
        """Kayıplar haritadan silinir; kazanan, kaybedenden oransal olarak az kaybeder. Yorum (dunya.py
        _savas): 'saldırılan, saldırana öfkelenir; kaybeden saldıran da öfkelenir'."""
        for a_birim, v_birim, kazanir in ((20, 6, True), (5, 40, False)):
            d = self.kur(a=koy("a", birim=a_birim, ittifak=0), v=koy("v", birim=v_birim, ittifak=1))
            a, v = self.kayitlar["a"], self.kayitlar["v"]
            d._savas("a", a, "v", v, SIMDI)
            r = v["privateState"]["attacksReceived"][-1]["description"]
            self.assertEqual(r["win"], int(kazanir))
            giden = sum(n for _, n, *_ in r["attacker_units"])
            self.assertLessEqual(giden, a_birim)
            self.assertEqual(sum(n for _, n, *_ in r["victim_units"]), v_birim)
            oran_a, oran_v = (a_birim - birim(a)) / giden, (v_birim - birim(v)) / v_birim
            if kazanir:
                self.assertLess(oran_a, oran_v)
            else:
                self.assertLess(oran_v, oran_a)
            self.assertGreater(a_birim - birim(a) + v_birim - birim(v), 0)
            self.assertEqual(d._ofke(v, "a"), 1)
            self.assertEqual(d._ofke(a, "v"), 0 if kazanir else 1)

    def test_ordusuz_saldiran_kazanamaz(self):
        """Değişmez: hiç birimi olmayan saldıran, savunmasız köye bile kazanamaz, ganimet alamaz."""
        d = self.kur(a=koy("a", ittifak=0), v=koy("v", ittifak=1, coins=1000))
        d._savas("a", self.kayitlar["a"], "v", self.kayitlar["v"], SIMDI)
        self.assertFalse(d._son_sonuc["kazandi"])
        self.assertEqual((self.kayitlar["v"]["maps"][0]["coins"], d._son_sonuc["ganimet"]), (1000, 0))

    def test_intikam_yalniz_yenilen_botun_baska_ittifakina(self):
        """Yorum (_savas): 'Yenilen botun ittifakı (başka ittifaksa) intikam seferi ilan edebilir'.
        Akın püskürtülürse, kurban oyuncuysa ya da iki bot aynı ittifaktansa sefer yok; olasılık 0 ise de yok."""
        for durum, v_birim, v_bot, v_ittifak, olasilik, sefer in (
                ("yenildi", 0, True, 1, 1.0, [(1, "a")]), ("puskurttu", 40, True, 1, 1.0, []),
                ("oyuncu", 0, False, None, 1.0, []), ("ayni", 0, True, 0, 1.0, []),
                ("olasilik0", 0, True, 1, 0.0, [])):
            d = self.kur(a=koy("a", birim=10, ittifak=0), v=koy("v", birim=v_birim, bot=v_bot, ittifak=v_ittifak))
            d.ayar["intikam_olasiligi"] = olasilik
            d._savas("a", self.kayitlar["a"], "v", self.kayitlar["v"], SIMDI, oyuncuya=not v_bot)
            self.assertEqual(d._son_sonuc["kazandi"], durum != "puskurttu", durum)
            self.assertEqual([(s["ittifak"], s["hedef"]) for s in d.seferler], sefer, durum)

    def test_oyuncu_saldirinca_intikam_olasiligi(self):
        """VARSAYILAN_AYAR oyuncuya_intikam: 'oyuncu bir bota saldırınca' kurbanın ittifakı sefer ilan eder;
        olasılık 0 ise etmez. Sefer kurbanın ittifakından, hedefi oyuncu."""
        d = self.kur(v=koy("v", ittifak=2), p=koy("p", bot=False))
        self.assertIsNone(d.oyuncu_saldirdi("p", "Oyuncu", "v", self.kayitlar["v"]))
        self.assertEqual(d.seferler, [])
        d.ayar["oyuncuya_intikam"] = 1.0
        s = d.oyuncu_saldirdi("p", "Oyuncu", "v", self.kayitlar["v"])
        self.assertEqual((s["ittifak"], s["hedef"], s["oyuncu"]), (2, "p", True))
        self.assertIn("Köy v için senin köyüne", d.olaylar[-1]["metin"])

    def test_kule_savunani_guclendirir(self):
        """kule_gucu: savunma binalarının ek gücü. Aynı saldırı kulesiz köyü yener, çok kuleli köye yenilir."""
        for kule, kazanir in ((0, True), (10, False)):
            d = self.kur(a=koy("a", birim=5, ittifak=0), v=koy("v", ittifak=1, binalar=[KULE_V] * kule))
            d._savas("a", self.kayitlar["a"], "v", self.kayitlar["v"], SIMDI)
            self.assertEqual(d._son_sonuc["kazandi"], kazanir, kule)


class HedefSecimiTestleri(DunyaTesti):
    def test_ayni_ittifaka_saldirilmaz(self):
        """dunya.py: 'aynı ittifaktaki botlar birbirine saldırmaz' (OYN-01)."""
        d = self.kur(a=koy("a", birim=10, ittifak=0), m=koy("m", ittifak=0), x=koy("x", ittifak=2))
        secimler = {self.secilen(d, "a", ["a", "m", "x"]) for _ in range(30)}
        self.assertEqual(secimler, {"x"})
        self.assertIsNone(self.secilen(d, "a", ["a", "m"]))

    def test_dusuk_seviye_ve_yakinda_vurulan_hedef_secilmez(self):
        """_hedefe_uygun: aynı hedefe 6 saat içinde ikinci kez saldırılmaz; düşük seviyeli (sv 1) köye akın yok."""
        d = self.kur(a=koy("a", birim=10, ittifak=0), dus=koy("dus", seviye=1, ittifak=1),
                     yak=koy("yak", ittifak=1), ser=koy("ser", ittifak=2))
        a = self.kayitlar["a"]
        a["privateState"]["bot_hafiza"]["son_hedef"] = {"id": "yak", "zaman": SIMDI - 60}
        sira = ["a", "dus", "yak", "ser"]
        self.assertEqual({self.secilen(d, "a", sira) for _ in range(30)}, {"ser"})
        a["privateState"]["bot_hafiza"]["son_hedef"]["zaman"] = SIMDI - denge.SALDIRI_PERIYODU
        self.assertIn("yak", {self.secilen(d, "a", sira) for _ in range(40)})

    def test_zayif_ofkeli_ve_kulesiz_hedef_daha_olasi(self):
        """Yorum (_akin): 'öfke duyduğuna ve zayıf olana daha istekli saldırır'. Ağırlığı daha büyük aday,
        toplamın ortasındaki seçimi (uniform'un ortası) her iki sırada da alır."""
        d = self.kur(a=koy("a", birim=10, ittifak=0), g=koy("g", birim=40, ittifak=1), z=koy("z", ittifak=1),
                     o=koy("o", birim=10, ittifak=1), s=koy("s", birim=10, ittifak=2),
                     k=koy("k", birim=10, ittifak=1, binalar=[KULE_V] * 5), y=koy("y", birim=10, ittifak=2))
        self.kayitlar["a"]["privateState"]["bot_hafiza"]["ofke"] = {"o": 3}
        for istekli, oteki in (("z", "g"), ("o", "s"), ("y", "k")):
            for sira in ((istekli, oteki), (oteki, istekli)):
                self.assertEqual(self.secilen(d, "a", ["a", *sira], f=0.5), istekli, sira)

    def test_oyuncuya_aralik_kalkan_ve_seviye(self):
        """Yorum: 'Oyuncuya saldırı: belirli aralıktan sık değil'; kalkanlıya ve düşük seviyeye akın yok."""
        d = self.kur(a=koy("a", birim=10, ittifak=0), m=koy("m", ittifak=0), p=koy("p", birim=3, bot=False))
        d.ayar["oyuncuya_saldiri"] = 1.0
        p, sira = self.kayitlar["p"], ["a", "m"]
        d._son_oyuncu_saldiri = SIMDI - 10
        self.assertIsNone(self.secilen(d, "a", sira))
        d._son_oyuncu_saldiri = SIMDI - 600
        self.assertEqual(self.secilen(d, "a", sira), "p")
        p["privateState"]["shield_until"] = SIMDI + 100
        self.assertIsNone(self.secilen(d, "a", sira))
        p["privateState"]["shield_until"], p["maps"][0]["level"] = 0, 1
        self.assertIsNone(self.secilen(d, "a", sira))
        p["maps"][0]["level"] = 10
        d.ayar["oyuncuya_saldiri"] = 0
        self.assertIsNone(self.secilen(d, "a", sira))
        # Gerçek akın oyuncu zamanını işler; hemen ikinci akın olmaz.
        d.ayar["oyuncuya_saldiri"] = 1.0
        self.assertEqual(d._akin("a", self.kayitlar["a"], d._botlar(), SIMDI), "p")
        self.assertEqual(d._son_oyuncu_saldiri, SIMDI)
        self.assertIsNone(d._akin("a", self.kayitlar["a"], d._botlar(), SIMDI))


class TurTestleri(DunyaTesti):
    def gonderilen(self):
        return {u: len(k["privateState"].get("attacksSent") or []) for u, k in self.kayitlar.items()}

    def test_tur_basina_saldiri_siniri_ve_ittifak(self):
        """ayar tur_basina_saldiri: bir turda en çok bu kadar bot akını; akınlar başka ittifaka."""
        d = self.kur(**{f"b{i}": koy(f"b{i}", birim=10, ittifak=i % 2) for i in range(6)})
        d.ayar.update(saldiri_olasiligi=1.0, tur_basina_saldiri=2)
        d.tek_tick()
        self.assertEqual(d.tick, 1)
        self.assertEqual(sum(self.gonderilen().values()), 2)
        for u, k in self.kayitlar.items():
            for akin in k["privateState"].get("attacksSent") or []:
                self.assertNotEqual(d._ittifak(u, k), d._ittifak(akin["victim_id"]))

    def test_aralik_seviye_ve_olasilik(self):
        """ayar bot_saldiri_araligi (180 sn) ve saldiri_olasiligi; seviyesi düşük bot akın etmez."""
        for son, seviye, olasilik, akin in ((SIMDI - 100, 10, 1.0, 0), (SIMDI - 200, 10, 1.0, 1),
                                            (0, 1, 1.0, 0), (0, 10, 0, 0)):
            d = self.kur(a=koy("a", seviye=seviye, birim=10, ittifak=0), v=koy("v", ittifak=1))
            d.ayar["saldiri_olasiligi"] = olasilik
            d._son_saldiri["a"] = son
            d.tek_tick()
            self.assertEqual(self.gonderilen()["a"], akin, (son, seviye, olasilik))

    def test_bot_kayitlari_bes_turda_bir_yazilir(self):
        """BULGULAR (denetim, 30.10.2026): 'bot kayıtları 5 turda bir' yazılır; bekleyenler durdurulunca yazılır."""
        d = self.kur(b=koy("b"))
        yazilan_turlar = []
        for _ in range(10):
            self.yazilan.clear()
            d.tek_tick()
            if "b" in self.yazilan:
                yazilan_turlar.append(d.tick)
        self.assertEqual(yazilan_turlar, [5, 10])
        d.tek_tick()
        self.assertEqual(d._bekleyen_botlar, {"b"})
        self.yazilan.clear()
        d.durdur()
        self.assertEqual((self.yazilan, d._bekleyen_botlar), (["b"], set()))

    def test_oyuncu_kaydi_akin_turunda_yazilir(self):
        """Yorum (tek_tick): 'Oyuncunun kaydı hemen yazılır'; saldıran botun ganimeti de yazılmak üzere bekler."""
        d = self.kur(a=koy("a", birim=10, ittifak=0), p=koy("p", bot=False))
        d.ayar.update(saldiri_olasiligi=1.0, oyuncuya_saldiri=1.0)
        d.tek_tick()
        self.assertEqual(d.tick, 1)
        self.assertEqual(self.gonderilen()["a"], 1)
        self.assertEqual(self.yazilan, ["p"])  # 1. tur: bot kayıtları henüz yazılmaz
        self.assertIn("a", d._bekleyen_botlar)

    def test_turda_tek_ekonomi_haberi(self):
        """Yorum (tek_tick): 'turda yalnızca biri haber olur'; biriken haberler tur sonunda boşaltılır."""
        d = self.kur(**{f"b{i}": koy(f"b{i}", coins=10 ** 6) for i in range(5)})
        with mock.patch.object(dunya.random, "random", return_value=0.0):  # her bot birim alır
            d.tek_tick()
        self.assertEqual(sum(1 for o in d.olaylar if o["tur"] == "ekonomi"), 1)
        self.assertEqual(sum(birim(k) for k in self.kayitlar.values()), 5)
        self.assertEqual(d._ekonomi_haberleri, [])

    def test_panel_verisi_tur_sonrasi_yenilenir(self):
        """Panel önbelleği turu gizlemez: tek_tick'ten sonra veri() yeni turu gösterir."""
        d = self.kur(a=koy("a"))
        once = d.veri()
        d.tek_tick()
        sonra = d.veri()
        self.assertIsNot(sonra, once)
        self.assertEqual((once["tick"], sonra["tick"]), (0, 1))

    def test_dongu_hatada_durmaz_tick_saniye_bekler(self):
        """Yorum (dongu): 'dünya döngüsü sunucuyu düşürmesin'; modül belgesi: tick_saniye aralığıyla çalışır."""
        d = self.kur(a=koy("a"))
        beklenen = []
        cagri = []

        def tur():
            cagri.append(1)
            if len(cagri) == 1:
                raise RuntimeError("bozuk kayıt")
            d._duruyor = True
        with mock.patch.object(dunya.time, "sleep", beklenen.append), mock.patch.object(d, "tek_tick", tur):
            d.dongu()
        self.assertEqual(len(cagri), 2)
        self.assertEqual(beklenen, [60, 60])

    def test_baslat_arka_planda_is_parcacigi(self):
        """Modül belgesi: 'arka planda tick_saniye aralığıyla çalışır' -> daemon iş parçacığı dongu'yu çalıştırır."""
        d = self.kur(a=koy("a"))
        eski = dunya.etkin
        self.addCleanup(setattr, dunya, "etkin", eski)
        with mock.patch.object(dunya.threading, "Thread") as thread:
            d.baslat()
        self.assertIs(dunya.etkin, d)
        thread.assert_called_once_with(target=d.dongu, name="dunya", daemon=True)
        thread.return_value.start.assert_called_once_with()

    def test_gecmis_dunya_toplamlari(self):
        """Panel eğrisi: turdaki dünya toplamı = kayıtlardaki dört kaynağın ve birimlerin toplamı."""
        d = self.kur(a=koy("a", birim=4), p=koy("p", birim=2, bot=False))
        d.tek_tick()
        kaynak = sum(int(k["maps"][0][r]) for k in self.kayitlar.values() for r in KAYNAKLAR)
        adet = sum(birim(k) for k in self.kayitlar.values())
        self.assertEqual(d.gecmis[-1], {"tick": 1, "kaynak": kaynak, "birim": adet})

    def test_kapaliyken_calismaz(self):
        d = self.kur(a=koy("a"))
        d.ayar["aktif"] = False
        eski = dunya.etkin
        self.addCleanup(setattr, dunya, "etkin", eski)
        d.baslat()
        self.assertIs(dunya.etkin, d)
        self.assertIsNone(d._is_parcacigi)
        d.tek_tick()
        self.assertEqual(d.tick, 0)


class SeferTestleri(DunyaTesti):
    def test_ilan_kurallari(self):
        """OYN-01: sefer 12 turda en çok 3 akın; aynı ittifak aynı hedefe iki sefer açmaz, başka ittifak ya da
        başka hedef açabilir; aynı anda en çok EN_COK_SEFER sefer."""
        d = self.kur(x=koy("x"), z=koy("z"), w=koy("w"))
        d.tick = 20
        s = d._sefer_ilan(1, "x", "X", "Y")
        self.assertEqual((s["kalan"], s["bitis"] - d.tick, s["zafer"], s["yenilgi"]), (3, 12, 0, 0))
        self.assertIsNone(d._sefer_ilan(1, "x", "X", "Y"))
        self.assertIsNotNone(d._sefer_ilan(0, "x", "X", "Y"))
        self.assertIsNotNone(d._sefer_ilan(1, "w", "W", "Y"))  # aynı ittifak, başka hedef
        self.assertEqual(len(d.seferler), dunya.EN_COK_SEFER)
        self.assertIsNone(d._sefer_ilan(2, "z", "Z", "Y"))
        # Ilan edilen sefer, süresi içinde (uygun üye yokken bile) dağılmaz.
        d.tick = 21
        d._seferleri_yurut([], SIMDI)
        self.assertEqual(len(d.seferler), dunya.EN_COK_SEFER)

    def test_uc_akinda_biter_sayac_ve_ganimet_haberi(self):
        """OYN-01: her turda ittifakın en güçlü uygun üyesi akın eder; 3 akın bitince sefer hemen kapanır.
        Haberdeki akın sayısı zafer + yenilgi, ganimet hedefin gerçek kaybıdır."""
        d = self.kur(b0=koy("b0", birim=20, ittifak=0), b1=koy("b1", birim=5, ittifak=0), b2=koy("b2", ittifak=1))
        b2 = self.kayitlar["b2"]
        once = sum(b2["maps"][0][k] for k in KAYNAKLAR)
        sefer = d._sefer_ilan(0, "b2", "Köy b2", "Köy b1")
        for i in range(3):
            simdi = SIMDI + i * (denge.SALDIRI_PERIYODU + 1)
            degisen = d._seferleri_yurut(d._botlar(), simdi)
            self.assertEqual(degisen, {"b0", "b2"})  # en güçlü uygun üye
            self.assertEqual(sefer["zafer"] + sefer["yenilgi"], 3 - sefer["kalan"])
            self.assertEqual(sefer in d.seferler, i < 2)
        self.assertEqual(sefer["zafer"], 3)  # birimsiz hedef her akında yenilir
        kayip = once - sum(b2["maps"][0][k] for k in KAYNAKLAR)
        self.assertGreater(kayip, 0)
        self.assertIn(f"Köy b2 3 akında {kayip} kaynak kaybetti", d.olaylar[-1]["metin"])

    def test_sure_sinirinda_surer_sonra_dagilir_hedef_yoksa_biter(self):
        """SEFER_SURESI yorumu: 'tur; bu sürede bitmeyen sefer dağılır' (OYN-01: 12 turda en çok 3 akın).
        İlandan 12 tur sonra hâlâ akın edilir, 13. turda sefer kalkar. Hedef köy yoksa sefer biter."""
        d = self.kur(b0=koy("b0", birim=20, ittifak=0), b2=koy("b2", ittifak=1))
        sefer = d._sefer_ilan(0, "b2", "Köy b2", "Köy b1")
        d.tick += dunya.SEFER_SURESI
        d._seferleri_yurut(d._botlar(), SIMDI)
        self.assertEqual(sefer["kalan"], dunya.SEFER_SALDIRI - 1)
        d.tick += 1
        d._seferleri_yurut(d._botlar(), SIMDI + denge.SALDIRI_PERIYODU + 1)
        self.assertEqual((d.seferler, sefer["kalan"]), ([], dunya.SEFER_SALDIRI - 1))
        sefer = d._sefer_ilan(0, "yok", "Kayıp", "Köy b1")
        d._seferleri_yurut(d._botlar(), SIMDI)
        self.assertEqual(d.seferler, [])
        self.assertIn("Kayıp seferi dağıldı", d.olaylar[-1]["metin"])

    def test_bitis_haberleri(self):
        d = self.kur(a=koy("a"))
        for zafer, yenilgi, ganimet, metin in ((2, 1, 500, "bitirdi: X 3 akında 500 kaynak"),
                                               (0, 2, 0, "X, Kızıl Birlik'in intikam seferini 2 akında püskürttü"),
                                               (0, 0, 0, "seferi dağıldı")):
            s = d._sefer_ilan(0, "x", "X", "Y")
            s.update(zafer=zafer, yenilgi=yenilgi, ganimet=ganimet)
            d._sefer_bitir(s)
            self.assertIn(metin, d.olaylar[-1]["metin"])
            self.assertEqual(d.seferler, [])

    def test_uye_secimi(self):
        """Akın eden: aynı ittifaktan, seviyesi yeten, en az 3 birimli, bot aralığı geçmiş en güçlü üye."""
        guclu = max((i for i in get_game_config()["items"] if i.get("type") == "u"),
                    key=lambda i: float(i.get("attack") or 0))
        for b0_son, beklenen in ((SIMDI - 1000, "b0"), (SIMDI - 10, "b5")):
            d = self.kur(b0=koy("b0", birim=20, ittifak=0), b1=koy("b1", ittifak=0), b4=koy("b4", seviye=1, birim=30,
                         ittifak=0), b5=koy("b5", birim=5, ittifak=0), b2=koy("b2", ittifak=1),
                         b3=koy("b3", birim=30, ittifak=2))
            self.kayitlar["b1"]["maps"][0]["items"] += [esya(int(guclu["id"]), 70), esya(int(guclu["id"]), 71)]
            self.assertGreater(dunya.ordu_gucu(dunya.birim_sayilari(self.kayitlar["b1"])), dunya.ordu_gucu({SOVALYE: 20}))
            d._son_saldiri["b0"] = b0_son
            d._sefer_ilan(0, "b2", "Köy b2", "Köy b1")
            d._seferleri_yurut(d._botlar(), SIMDI)
            saldiranlar = [u for u, k in self.kayitlar.items() if k["privateState"].get("attacksSent")]
            self.assertEqual(saldiranlar, [beklenen])

    def test_oyuncuya_sefer_araliga_ve_seviyeye_saygili(self):
        """OYN-01: 'oyuncuya akınlar kalkana ve aralığa saygılı'; oyuncuya son akından hemen sonra sefer akını
        olmaz, oyuncu_saldiri_araligi geçince olur; düşük seviyeli oyuncuya olmaz."""
        for son, seviye, akin in ((SIMDI, 10, 0), (SIMDI - 600, 10, 1), (0, 1, 0)):
            d = self.kur(b0=koy("b0", birim=10, ittifak=0), p=koy("p", seviye=seviye, birim=3, bot=False))
            sefer = d._sefer_ilan(0, "p", "Oyuncu", "Köy b1", oyuncu=True)
            d._son_oyuncu_saldiri = son
            d._seferleri_yurut(d._botlar(), SIMDI)
            self.assertEqual(3 - sefer["kalan"], akin, (son, seviye))
            self.assertEqual(len(self.kayitlar["p"]["privateState"].get("attacksReceived") or []), akin)


class IttifakDegisimiTestleri(DunyaTesti):
    """OYN-01: '15 turda bir bot kalabalık ittifaktan en küçüğüne geçebiliyor (haber)'. Belge dizesi:
    'kalabalık ittifakından ayrılıp en küçük ittifaka geçer'. (Geçişin kendisi test_sistemler'de.)"""

    def degisim(self, d, tick):
        d.tick = tick
        with mock.patch.object(dunya.random, "random", return_value=0.0):
            return d._ittifak_degisimi()

    def test_en_kalabaliktan_en_kucuge(self):
        d = self.kur(**{f"b{i}": koy(f"b{i}", ittifak=t) for i, t in enumerate((0, 0, 0, 1, 1, 2))})
        (uid,) = self.degisim(d, dunya.ITTIFAK_DEGISIMI)
        self.assertIn(uid, ("b0", "b1", "b2"))
        self.assertEqual(d._ittifak(uid, self.kayitlar[uid]), 2)
        self.assertEqual(d.olaylar[-1]["metin"], f"Köy {uid}, Kızıl Birlik'ten ayrılıp Yeşil Birlik'e katıldı")

    def test_aralik_disi_dengeli_ya_da_az_botta_degisim_yok(self):
        d = self.kur(**{f"b{i}": koy(f"b{i}", ittifak=t) for i, t in enumerate((0, 0, 0, 1, 1, 2))})
        self.assertEqual(self.degisim(d, dunya.ITTIFAK_DEGISIMI - 1), set())
        d = self.kur(**{f"b{i}": koy(f"b{i}", ittifak=i) for i in range(3)})  # her ittifakta bir: zaten dengeli
        self.assertEqual(self.degisim(d, dunya.ITTIFAK_DEGISIMI), set())
        d = self.kur(b0=koy("b0", ittifak=0), b1=koy("b1", ittifak=0))
        self.assertEqual(self.degisim(d, dunya.ITTIFAK_DEGISIMI), set())
        self.assertEqual(d.olaylar, [])


class LoncaVeriTestleri(DunyaTesti):
    def test_lonca_sosyal_binayi_config_iscileriyle_tamamlar(self):
        """_lonca belge dizesi: arkadaş işçi gerektiren binayı tur başına bir tane tamamlar; botlara dokunmaz.
        İşçi sayısı ve adları config social_items'tan (Mill II: worker_cost 2)."""
        bilgi = next(x for x in get_game_config()["social_items"] if int(x["id"]) == SOSYAL)
        gerekli, adlar = int(bilgi["worker_cost"]), bilgi["workers"].split(",")
        oyuncu = koy("p", bot=False, birim=1, binalar=[EV])
        oyuncu["maps"][0]["items"] += [[SOSYAL, 30, 30, 0, 0, 0], [SOSYAL, 34, 30, 0, 0, 0]]
        bot = koy("b")
        bot["maps"][0]["items"].append([SOSYAL, 30, 30, 0, 0, 0])
        d = self.kur(b=bot, p=oyuncu)
        self.assertEqual(d._lonca(SIMDI), "p")
        sosyal = [e for e in oyuncu["maps"][0]["items"] if e[0] == SOSYAL]
        self.assertEqual(sosyal[0][7]["workers"], gerekli)
        self.assertEqual(len(sosyal[0][7]["hired"]), gerekli)
        self.assertTrue(set(sosyal[0][7]["hired"]) <= set(adlar))
        self.assertEqual(sosyal[0][4], SIMDI)
        self.assertEqual(len(sosyal[1]), 6)  # turda bir bina
        self.assertEqual(d._lonca(SIMDI), "p")
        self.assertIsNone(d._lonca(SIMDI))  # hepsi tamam
        self.assertEqual(len(bot["maps"][0]["items"][-1]), 6)
        self.assertEqual(d.olaylar[-1]["tur"], "lonca")

    def test_panel_verisi(self):
        """Kalkan alanı kalan süredir; sonraki tur = son güncelleme + tick_saniye; toplamlar kayıtların toplamı;
        konum yorumu: '9 sütunlu ızgara + kişiye özgü küçük sapma: köyler üst üste binmez'."""
        kayitlar = {"p": koy("p", bot=False, birim=2)}
        kayitlar["p"]["privateState"]["shield_until"] = SIMDI + 3600
        for i in range(17):
            kayitlar[f"b{i:02}"] = koy(f"b{i:02}", birim=i % 3, ittifak=i % 3)
        kayitlar["b00"]["privateState"]["shield_until"] = SIMDI - 5
        d = self.kur(**kayitlar)
        veri = d.veri()
        self.assertIs(d.veri(), veri)  # kısa süre içinde önbellekten
        o = {x["id"]: x for x in veri["oyuncular"]}
        self.assertEqual((o["p"]["kalkan"], o["b00"]["kalkan"], o["b01"]["kalkan"]), (3600, 0, 0))
        self.assertEqual((o["p"]["ittifak"], o["b01"]["ittifak"]), ("", dunya.ITTIFAKLAR[1]))
        self.assertEqual(veri["sonraki_tick"] - veri["guncelleme"], veri["tick_saniye"])
        for k in KAYNAKLAR:
            self.assertEqual(veri["toplam"][k], sum(int(x["maps"][0][k]) for x in kayitlar.values()))
        self.assertEqual(veri["toplam"]["birim"], sum(birim(x) for x in kayitlar.values()))
        xs = [x["konum"]["x"] for x in veri["oyuncular"]]
        ys = [x["konum"]["y"] for x in veri["oyuncular"]]
        self.assertTrue(all(xs[i] < xs[i + 1] for i in range(8)), xs)
        self.assertLess(xs[9], xs[1])  # onuncu köy yeni satırın başında
        self.assertTrue(all(abs(y - ys[0]) < 30 for y in ys[:9]), ys)
        self.assertGreater(min(ys[9:18]) - max(ys[:9]), 30)


if __name__ == "__main__":
    unittest.main()
