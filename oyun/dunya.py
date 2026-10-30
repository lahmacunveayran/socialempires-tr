# -*- coding: utf-8 -*-
"""Yaşayan dünya: bot köyleri kendi ekonomilerini işletir, birbirine ve
oyuncuya akın düzenler.

Sunucu açılırken `dunya.baslat()` çağrılır; arka planda `tick_saniye`
aralığıyla çalışır. Tüm değişiklikler `save_lock` altında yapılır ve
normal kayıt dosyalarına yazılır; istemci tarafında ek bir şey gerekmez.

Ayarlar: `ayarlar.json` içindeki `dunya` bölümü
"""

import functools
import hashlib
import random
import threading
import time

from oyun import ayarlar, denge
from oyun.config import get_game_config
from oyun.kayit import all_saves_userid, save_lock, save_session, session
from oyun.turkce import cevirileri_yukle
from oyun.zaman import zaman_olcegi

VARSAYILAN_AYAR = {
    "aktif": True,
    "tick_saniye": 90,
    "saldiri_olasiligi": 0.45,
    "oyuncuya_saldiri": 0.15,
    "olay_saklama": 200,
    "intikam_olasiligi": 0.35,   # bir bot yenilince ittifakının intikam seferi ilan etmesi
    "oyuncuya_intikam": 0.5,     # oyuncu bir bota saldırınca
}

# İttifaklar: aynı ittifaktaki botlar birbirine saldırmaz. Üyelik bot kaydında (bot_hafiza.ittifak) durur;
# hiç değişmemiş botun ittifakı kimliğinden çıkar. Zaman zaman bir bot ittifak değiştirir.
ITTIFAKLAR = ["Kızıl Birlik", "Mavi Birlik", "Yeşil Birlik"]
SEFER_SALDIRI = 3     # bir intikam seferinde en çok saldırı
SEFER_SURESI = 12     # tur; bu sürede bitmeyen sefer dağılır
EN_COK_SEFER = 3      # aynı anda süren sefer
ITTIFAK_DEGISIMI = 15  # tur: bu aralıkla bir bot ittifak değiştirebilir


@functools.lru_cache(maxsize=1)
def _ceviriler():
    return cevirileri_yukle()


def turkce_ad(esya_id):
    """Eşyanın Türkçe adı (haber metinleri için)."""
    return _ceviriler().get(f"item:{esya_id}") or _item(esya_id).get("name") or str(esya_id)


def rutbe(seviye):
    """Seviyeye özgü rütbe adı (Nefer, Yeniçeri, Sipahi, Paşa...)."""
    return _ceviriler().get(f"level:{seviye}", "")


def ayarlari_yukle():
    ayar = dict(VARSAYILAN_AYAR)
    ayar.update(ayarlar.oku().get("dunya") or {})
    return ayar


# ---------------------------------------------------------------------------
# Yardımcılar (test edilebilir saf fonksiyonlar)
# ---------------------------------------------------------------------------

def birim_sayilari(save):
    """Haritadaki birimleri {birim_id: adet} olarak döndürür."""
    sayilar = {}
    for esya in save.get("maps", [{}])[0].get("items", []):
        try:
            esya_id = int(esya[0])
        except (TypeError, ValueError, IndexError):
            continue
        item = get_game_config()["items"]
        # config'te tür bilgisi; pahalı olmasın diye önbellek kullanılır
        tur = _ITEM_TURU.get(esya_id)
        if tur is None:
            tur = _tur_bul(esya_id)
        if tur == "u":
            sayilar[esya_id] = sayilar.get(esya_id, 0) + 1
    return sayilar


_ITEM_TURU = {}
_ITEM_CACHE = {}


def _tur_bul(esya_id):
    for item in get_game_config()["items"]:
        if int(item["id"]) == int(esya_id):
            _ITEM_TURU[int(esya_id)] = item.get("type")
            return item.get("type")
    return None


def _item(esya_id):
    anahtar = int(esya_id)
    if anahtar in _ITEM_CACHE:
        return _ITEM_CACHE[anahtar]
    for item in get_game_config()["items"]:
        if int(item["id"]) == anahtar:
            _ITEM_CACHE[anahtar] = item
            return item
    _ITEM_CACHE[anahtar] = {}
    return {}


def ordu_gucu(sayilar):
    """Birim sayılarından yaklaşık savaş gücü."""
    guc = 0.0
    for esya_id, adet in sayilar.items():
        item = _item(esya_id)
        try:
            saldiri = float(item.get("attack") or 0)
            can = float(item.get("life") or 0)
        except (TypeError, ValueError):
            saldiri = can = 0
        guc += adet * (saldiri + can * 0.35)
    return guc


def kule_gucu(save):
    """Savunma binalarının (kule vb.) ek gücü."""
    guc = 0.0
    for esya in save.get("maps", [{}])[0].get("items", []):
        try:
            item = _item(int(esya[0]))
        except (TypeError, ValueError, IndexError):
            continue
        if item.get("type") == "b":
            try:
                saldiri = float(item.get("attack") or 0)
            except (TypeError, ValueError):
                saldiri = 0
            if saldiri > 0:
                guc += saldiri * 3
    return guc


def birim_sil(save, silinecek):
    """{id: adet} kadar birimi haritadan rastgele siler."""
    kalan = dict(silinecek)
    esyalar = save["maps"][0]["items"]
    for esya in list(esyalar):
        try:
            esya_id = int(esya[0])
        except (TypeError, ValueError, IndexError):
            continue
        if kalan.get(esya_id, 0) > 0 and _tur_bul(esya_id) == "u":
            esyalar.remove(esya)
            kalan[esya_id] -= 1
    return kalan


def kaynak_ekle(save, kaynak, miktar):
    harita = save["maps"][0]
    harita[kaynak] = int(harita.get(kaynak, 0)) + int(miktar)


def rapor_ekle(hedef, saldiran, veri):
    """Savunanın attacksReceived listesine rapor ekler."""
    ps = hedef.setdefault("privateState", {})
    liste = ps.get("attacksReceived")
    if not isinstance(liste, list):
        liste = []
        ps["attacksReceived"] = liste
    liste.append({
        "time": veri["time"],
        "attacker_id": str(saldiran.get("playerInfo", {}).get("pid", "")),
        "viewPending": 1,  # istemci açılışta saldırı penceresini gösterir
        "description": veri,
    })
    del liste[:-50]


# ---------------------------------------------------------------------------
# Dünya
# ---------------------------------------------------------------------------

# Sunucuda çalışan dünya (haber şeridi buradan okur); başlatılmadıysa None.
etkin = None


def _hafiza(kayit):
    """Botun kayıttaki hafızası (öfke, son hedef, ittifak); yoksa kurulur."""
    ps = kayit.setdefault("privateState", {})
    if not isinstance(ps.get("bot_hafiza"), dict):
        ps["bot_hafiza"] = {}
    return ps["bot_hafiza"]


# Bot kayıtları bu kadar turda bir diske yazılır (oyuncunun kaydı her turda)
BOT_YAZMA_ARALIGI = 5


def _bot_mu(uid):
    return bool((session(uid) or {}).get("playerInfo", {}).get("bot"))


class Dunya:
    def __init__(self):
        self.ayar = ayarlari_yukle()
        self.tick = 0
        self.olaylar = []
        self._olay_no = 0
        self._ekonomi_haberleri = []
        self.aktif_olay = None
        self.ekonomi_carpan = 1.0
        self.savas_carpan = 1.0
        self._duruyor = False
        self._is_parcacigi = None
        self._son_guncelleme = int(time.time())
        self._son_saldiri = {}       # bot_id -> son akın zamanı
        self._bekleyen_botlar = set()  # yazılmayı bekleyen bot kayıtları (BOT_YAZMA_ARALIGI)
        self._son_oyuncu_saldiri = 0  # oyuncuya son akın zamanı
        self._veri_onbellek = None
        self._veri_zamani = 0
        self.gecmis = []
        self.seferler = []           # süren intikam seferleri
        self._son_sonuc = None       # son akının sonucu (seferin hesabı için)

    # -- erişim -----------------------------------------------------------
    def oyuncular(self):
        oyuncular = []
        for uid in all_saves_userid():
            kayit = session(uid)
            if not kayit:
                continue
            oyuncular.append((uid, kayit))
        return oyuncular

    def _botlar(self):
        return [(uid, k) for uid, k in self.oyuncular() if k.get("playerInfo", {}).get("bot")]

    # -- olay kaydı -------------------------------------------------------
    def olaylar_sonra(self, sonra=0, en_cok=20):
        """Haber şeridi için `sonra` numaralı olaydan sonrakiler (eskiden yeniye)."""
        if sonra > self._olay_no:
            sonra = 0  # sunucu yeniden başladı: istemcinin numarası geçersiz
        return [o for o in self.olaylar if o["id"] > sonra][-en_cok:]

    def olay(self, tur, metin):
        self._olay_no += 1
        self.olaylar.append({"id": self._olay_no, "zaman": int(time.time()), "tur": tur, "metin": metin})
        fazla = len(self.olaylar) - int(self.ayar.get("olay_saklama", 200))
        if fazla > 0:
            del self.olaylar[:fazla]

    # -- tick -------------------------------------------------------------
    def tek_tick(self):
        if not self.ayar.get("aktif", True):
            return
        with save_lock:
            self.tick += 1
            simdi = int(time.time())
            self._olay_guncelle(simdi)
            degisen = set()
            botlar = self._botlar()
            random.shuffle(botlar)
            saldiri_limiti = int(self.ayar.get("tur_basina_saldiri", 8))
            saldiri_sayisi = 0

            for uid, kayit in botlar:
                if self._ekonomi(uid, kayit):
                    degisen.add(uid)

                if saldiri_sayisi >= saldiri_limiti:
                    continue
                if simdi - self._son_saldiri.get(uid, 0) < int(self.ayar.get("bot_saldiri_araligi", 180)):
                    continue
                if int(kayit["maps"][0].get("level", 1)) < 6:
                    continue
                if not self._saldiri_hakki(kayit, simdi):
                    continue

                kisi = kayit.get("playerInfo", {}).get("bot_kisi", "dengeli")
                carpan = {"agresif": 1.45, "savunmaci": 0.7, "tuccar": 0.9}.get(kisi, 1.0)
                if random.random() < float(self.ayar.get("saldiri_olasiligi", 0.35)) * carpan:
                    hedef = self._akin(uid, kayit, botlar, simdi)
                    if hedef:
                        saldiri_sayisi += 1
                        self._son_saldiri[uid] = simdi
                        degisen.update((hedef, uid))  # saldıranın ganimeti ve kayıpları da yazılsın

            degisen.update(self._seferleri_yurut(botlar, simdi))
            degisen.update(self._ittifak_degisimi())

            # Bot ekonomisi her turda onlarca birim üretir; şerit boğulmasın
            # diye turda yalnızca biri haber olur (dakikada ~1 olay).
            if self._ekonomi_haberleri:
                self.olay("ekonomi", random.choice(self._ekonomi_haberleri))
                self._ekonomi_haberleri = []

            self._dunya_olayi(simdi)
            lonca = self._lonca(simdi)
            if lonca:
                degisen.add(lonca)

            # Oyuncunun kaydı hemen yazılır. Botların kaydı her turda değişir (kaynak üretimi); hepsini her dakika
            # yazmak tablette günde ~3,5 GB yazım ve kilit bekleyişi demekti: biriktirilip birkaç turda bir yazılır.
            # Süreç kapanırsa en çok son birkaç turun bot gelişimi kaybolur.
            self._bekleyen_botlar.update(u for u in degisen if _bot_mu(u))
            yazilacak = {u for u in degisen if not _bot_mu(u)}
            if self.tick % BOT_YAZMA_ARALIGI == 0:
                yazilacak |= self._bekleyen_botlar
                self._bekleyen_botlar = set()
            for uid in yazilacak:
                try:
                    save_session(uid)
                except OSError as hata:
                    print(f" ! Dunya kaydi yazilamadi ({uid}): {hata}")
            self._son_guncelleme = int(time.time())
            self._veri_onbellek = None

            # Paneldeki eğriler için dünya toplamları
            kaynak = 0
            birim = 0
            for _, kayit in self.oyuncular():
                harita = kayit["maps"][0]
                kaynak += sum(int(harita.get(k, 0)) for k in ("coins", "wood", "stone", "food"))
                birim += sum(birim_sayilari(kayit).values())
            self.gecmis.append({"tick": self.tick, "kaynak": kaynak, "birim": birim})
            if len(self.gecmis) > 80:
                del self.gecmis[:-80]

    # -- kardeşlik loncası -------------------------------------------------
    def _lonca(self, simdi):
        """Oyuncunun arkadaş işçi gerektiren binalarını bot ustalarla tamamlar.

        Orijinal oyunda bu binalar için arkadaş davet edilir; tek kişilik
        sunucuda lonca devreye girip bir binayı tur başına tamamlar.
        """
        sosyal = {int(x["id"]): x for x in get_game_config().get("social_items", [])}
        for uid, kayit in self.oyuncular():
            if kayit.get("playerInfo", {}).get("bot"):
                continue
            for esya in kayit["maps"][0]["items"]:
                try:
                    esya_id = int(esya[0])
                except (TypeError, ValueError, IndexError):
                    continue
                bilgi = sosyal.get(esya_id)
                if not bilgi:
                    continue
                gerekli = int(bilgi.get("worker_cost", 1))
                sozluk = esya[7] if len(esya) > 7 and isinstance(esya[7], dict) else {}
                if len(esya) >= 8 and int(sozluk.get("workers", 0)) >= gerekli:
                    continue
                while len(esya) < 8:
                    esya.append([] if len(esya) == 6 else {})
                isimler = [i.strip() for i in str(bilgi.get("workers", "")).split(",") if i.strip()]
                esya[7] = {
                    "workers": gerekli,
                    "hired": isimler[:gerekli],
                    "guild": 1,
                }
                esya[4] = simdi
                ad = kayit.get("playerInfo", {}).get("name", uid)
                self.olay("lonca", f"Kardeşlik Loncası, {ad} köyündeki {turkce_ad(esya_id)} için usta işçi gönderdi")
                return uid
        return None

    # -- dünya olayları ---------------------------------------------------
    def _ittifak(self, uid, kayit=None):
        kayit = kayit if kayit is not None else session(uid)
        hafiza = (kayit or {}).get("privateState", {}).get("bot_hafiza")
        secilen = hafiza.get("ittifak") if isinstance(hafiza, dict) else None
        if isinstance(secilen, int) and 0 <= secilen < len(ITTIFAKLAR):
            return secilen
        return int(hashlib.sha256(str(uid).encode("utf-8")).hexdigest(), 16) % len(ITTIFAKLAR)

    def ittifak_adi(self, uid, kayit=None):
        return ITTIFAKLAR[self._ittifak(uid, kayit)]

    def _ittifak_degisimi(self):
        """Arada bir, bir bot kalabalık ittifakından ayrılıp en küçük ittifaka geçer (haber olur)."""
        if self.tick % ITTIFAK_DEGISIMI != 0 or random.random() > 0.6:
            return set()
        botlar = self._botlar()
        if len(botlar) < 3:
            return set()
        uyeler = {i: [] for i in range(len(ITTIFAKLAR))}
        for uid, kayit in botlar:
            uyeler[self._ittifak(uid, kayit)].append((uid, kayit))
        kalabalik = max(uyeler, key=lambda i: len(uyeler[i]))
        kucuk = min(uyeler, key=lambda i: len(uyeler[i]))
        if kalabalik == kucuk or not uyeler[kalabalik]:
            return set()
        uid, kayit = random.choice(uyeler[kalabalik])
        _hafiza(kayit)["ittifak"] = kucuk
        ad = kayit.get("playerInfo", {}).get("name", uid)
        self.olay("ittifak", f"{ad}, {ITTIFAKLAR[kalabalik]}'ten ayrılıp {ITTIFAKLAR[kucuk]}'e katıldı")
        return {uid}

    # -- intikam seferleri ------------------------------------------------
    def _sefer_ilan(self, ittifak, hedef_id, hedef_ad, sebep_ad, oyuncu=False):
        """`ittifak`, üyesi `sebep_ad`'ın intikamı için `hedef_id`'ye sefer açar."""
        if len(self.seferler) >= EN_COK_SEFER or any(
                s["ittifak"] == ittifak and s["hedef"] == str(hedef_id) for s in self.seferler):
            return None
        sefer = {"ittifak": ittifak, "hedef": str(hedef_id), "hedef_ad": hedef_ad, "kalan": SEFER_SALDIRI,
                 "bitis": self.tick + SEFER_SURESI, "zafer": 0, "yenilgi": 0, "ganimet": 0, "oyuncu": oyuncu}
        self.seferler.append(sefer)
        if oyuncu:
            self.olay("ittifak", f"{ITTIFAKLAR[ittifak]}, {sebep_ad} için senin köyüne intikam seferi ilan etti!")
        else:
            self.olay("ittifak", f"{ITTIFAKLAR[ittifak]}, {sebep_ad} için {hedef_ad} köyüne intikam seferi ilan etti")
        return sefer

    def oyuncu_saldirdi(self, oyuncu_id, oyuncu_ad, kurban_id, kurban):
        """Oyuncu bir bota saldırdı (pvp.saldiri_bitir): kurbanın ittifakı intikam seferi ilan edebilir."""
        if not (kurban or {}).get("playerInfo", {}).get("bot"):
            return None
        if random.random() >= float(self.ayar.get("oyuncuya_intikam", 0.5)):
            return None
        kurban_ad = kurban.get("playerInfo", {}).get("name", kurban_id)
        return self._sefer_ilan(self._ittifak(kurban_id, kurban), oyuncu_id, oyuncu_ad, kurban_ad, oyuncu=True)

    def _seferleri_yurut(self, botlar, simdi):
        """Her seferden turda en çok bir saldırı: ittifakın en güçlü uygun üyesi hedefe akın eder."""
        degisen = set()
        aralik = int(self.ayar.get("bot_saldiri_araligi", 180))
        for sefer in list(self.seferler):
            hedef = session(sefer["hedef"])
            if sefer["kalan"] <= 0 or self.tick > sefer["bitis"] or not hedef:
                self._sefer_bitir(sefer)
                continue
            if sefer["oyuncu"]:
                # Oyuncuya akınlar da aralıklı ve kalkana saygılı
                yarim = int(self.ayar.get("oyuncu_saldiri_araligi", 600)) // 2
                if (simdi - self._son_oyuncu_saldiri < yarim or int(hedef["maps"][0].get("level", 1)) < 6
                        or int(hedef.get("privateState", {}).get("shield_until", 0) or 0) > simdi):
                    continue
            uyeler = [(u, k) for u, k in botlar
                      if u != sefer["hedef"] and self._ittifak(u, k) == sefer["ittifak"]
                      and int(k["maps"][0].get("level", 1)) >= 6 and sum(birim_sayilari(k).values()) >= 3
                      and simdi - self._son_saldiri.get(u, 0) >= aralik
                      and self._saldiri_hakki(k, simdi) and self._hedefe_uygun(k, sefer["hedef"], simdi)]
            if not uyeler:
                continue
            uid, kayit = max(uyeler, key=lambda uk: ordu_gucu(birim_sayilari(uk[1])))
            if not self._akin(uid, kayit, botlar, simdi, zorla=(sefer["hedef"], hedef)):
                continue
            self._son_saldiri[uid] = simdi
            degisen.update((uid, sefer["hedef"]))
            sefer["kalan"] -= 1
            if self._son_sonuc["kazandi"]:
                sefer["zafer"] += 1
                sefer["ganimet"] += self._son_sonuc["ganimet"]
            else:
                sefer["yenilgi"] += 1
            if sefer["kalan"] <= 0:
                self._sefer_bitir(sefer)
        return degisen

    def _sefer_bitir(self, sefer):
        if sefer not in self.seferler:
            return
        self.seferler.remove(sefer)
        ittifak = ITTIFAKLAR[sefer["ittifak"]]
        hedef_ad = "Köyün" if sefer["oyuncu"] else sefer["hedef_ad"]
        saldiri = sefer["zafer"] + sefer["yenilgi"]
        if not saldiri:
            self.olay("ittifak", f"{ittifak}'in {sefer['hedef_ad']} seferi dağıldı")
        elif sefer["zafer"]:
            self.olay("ittifak", f"{ittifak} intikam seferini bitirdi: {hedef_ad} {saldiri} akında "
                                 f"{sefer['ganimet']} kaynak kaybetti")
        else:
            self.olay("ittifak", f"{hedef_ad}, {ittifak}'in intikam seferini {saldiri} akında püskürttü")

    def _olay_guncelle(self, simdi):
        if self.aktif_olay and simdi >= self.aktif_olay.get("bitis", 0):
            self.olay("dunya", f"Son buldu: {self.aktif_olay.get('metin')}")
            self.aktif_olay = None
        if not self.aktif_olay:
            self.ekonomi_carpan = 1.0
            self.savas_carpan = 1.0

    def _dunya_olayi(self, simdi):
        """Her 8 turda bir tüm dünyayı etkileyen bir olay."""
        if self.aktif_olay or self.tick % 8 != 0:
            return
        tur = random.choice(["savas", "bereket", "kriz", "ticaret"])
        if tur == "savas":
            metin, ekonomi, savas = "Kizil Savaslari: botlar daha saldirgan!", 1.0, 1.25
            bot_uidleri = [u for u, _ in self._botlar()]
            for uid, kayit in self._botlar():
                if bot_uidleri:
                    self._ofke_artir(kayit, random.choice(bot_uidleri), 1)
        elif tur == "bereket":
            metin, ekonomi, savas = "Bereketli hasat: uretim artti", 1.25, 1.0
        elif tur == "kriz":
            metin, ekonomi, savas = "Kaynak krizi: uretim azaldi", 0.8, 1.0
        else:
            metin, ekonomi, savas = "Ticaret kervani: altin akisi hizlandi", 1.15, 1.0
        self.aktif_olay = {"tur": tur, "metin": metin,
                           "bitis": simdi + 8 * int(self.ayar.get("tick_saniye", 60))}
        self.ekonomi_carpan = ekonomi
        self.savas_carpan = savas
        self.olay("dunya", metin)

    # -- ekonomi ----------------------------------------------------------
    def _ekonomi(self, uid, kayit):
        harita = kayit["maps"][0]
        seviye = max(1, int(harita.get("level", 1)))
        degisti = False

        for alan, taban in (("wood", 4), ("stone", 3), ("food", 4), ("coins", 3)):
            artis = int((taban + random.random() * taban) * seviye * self.ekonomi_carpan * zaman_olcegi())
            harita[alan] = int(harita.get(alan, 0)) + artis
            degisti = True

        # Ara sıra yeni birim üret
        if random.random() < 0.35:
            birimler = [512, 516, 517, 518]
            secim = random.choice(birimler)
            item = _item(secim)
            maliyet = int(item.get("cost") or 0)
            if maliyet <= int(harita.get("coins", 0)) and len(kayit["maps"][0]["items"]) < 700:
                harita["coins"] = int(harita.get("coins", 0)) - maliyet
                from oyun.ekonomi import timestamp_now
                kayit["maps"][0]["items"].append(
                    [secim, random.randint(38, 62), random.randint(38, 62), 0, timestamp_now(), 0, [], {}]
                )
                degisti = True
                self._ekonomi_haberleri.append(
                    f"{kayit['playerInfo'].get('name', uid)} ordusuna bir {turkce_ad(secim)} kattı")

        # Seviye atlama
        seviyeler = get_game_config()["levels"]
        xp = int(harita.get("xp", 0))
        yeni = seviye
        while yeni + 1 < len(seviyeler) and xp >= int(seviyeler[yeni + 1]["exp_required"]):
            yeni += 1
        if yeni != seviye:
            harita["level"] = yeni
            self.olay("seviye", f"{kayit['playerInfo'].get('name', uid)} seviye {yeni} oldu")
            degisti = True
        return degisti

    # -- akın -------------------------------------------------------------
    def _ofke(self, kayit, hedef_id):
        hafiza = kayit.get("privateState", {}).get("bot_hafiza", {})
        return int(hafiza.get("ofke", {}).get(str(hedef_id), 0))

    def _ofke_artir(self, kayit, hedef_id, miktar=1):
        hafiza = _hafiza(kayit)
        ofke = hafiza.get("ofke")
        if not isinstance(ofke, dict):
            ofke = {}
            hafiza["ofke"] = ofke
        anahtar = str(hedef_id)
        ofke[anahtar] = int(ofke.get(anahtar, 0)) + miktar

    def _saldiri_hakki(self, kayit, simdi):
        """Son 6 saatte 3 saldırı sınırı (orijinal oyunun kuralı)."""
        liste = kayit.get("privateState", {}).get("attacksSent") or []
        sayi = 0
        for a in liste:
            try:
                zaman = int(a.get("time"))
            except (TypeError, ValueError, AttributeError):
                continue
            if simdi - zaman < denge.SALDIRI_PERIYODU:
                sayi += 1
        return sayi < denge.SALDIRI_HAKKI

    def _hedefe_uygun(self, kayit, hedef_id, simdi):
        """Aynı hedefe 6 saat içinde ikinci kez saldırmayı engeller."""
        hafiza = kayit.get("privateState", {}).get("bot_hafiza", {})
        son = hafiza.get("son_hedef") if isinstance(hafiza, dict) else None
        if isinstance(son, dict) and str(son.get("id")) == str(hedef_id):
            try:
                if simdi - int(son.get("zaman", 0)) < denge.SALDIRI_PERIYODU:
                    return False
            except (TypeError, ValueError):
                pass
        return True

    def _akin(self, saldiran_id, saldiran, botlar, simdi, zorla=None):
        """Bir akın; hedefi ağırlıklı seçer ya da `zorla=(hedef_id, hedef)` (intikam seferi)."""
        saldiran_birimler = birim_sayilari(saldiran)
        if sum(saldiran_birimler.values()) < 3:
            return None
        oyuncu_hedefleri = [(u, k) for u, k in self.oyuncular() if not k.get("playerInfo", {}).get("bot")]
        if zorla:
            hedef_id, hedef = zorla
            return self._savas(saldiran_id, saldiran, hedef_id, hedef, simdi,
                               oyuncuya=hedef_id in [u for u, _ in oyuncu_hedefleri])

        kendi_guc = ordu_gucu(saldiran_birimler) + kule_gucu(saldiran) * 0.5
        adaylar = []

        # Diğer botlar: öfke duyduğuna ve zayıf olana daha istekli saldırır
        for u, k in botlar:
            if u == saldiran_id:
                continue
            if int(k["maps"][0].get("level", 1)) < 6:
                continue
            if not self._hedefe_uygun(saldiran, u, simdi):
                continue
            # Aynı ittifaktaki botlara saldırma; rakip ittifaklara daha istekli ol.
            ayni = self._ittifak(u, k) == self._ittifak(saldiran_id, saldiran)
            if ayni:
                continue
            guc = ordu_gucu(birim_sayilari(k)) + kule_gucu(k) * 0.6
            ofke = self._ofke(saldiran, u)
            ittifak_carpan = 1.35 if not ayni else 0.25
            agirlik = (1.0 + 2.5 * ofke) * (kendi_guc / max(1.0, guc)) ** 0.8 * ittifak_carpan
            adaylar.append((u, k, max(0.05, agirlik)))

        # Oyuncuya saldırı: belirli aralıktan sık değil
        aralik = int(self.ayar.get("oyuncu_saldiri_araligi", 600))
        if oyuncu_hedefleri and simdi - self._son_oyuncu_saldiri >= aralik:
            if random.random() < float(self.ayar.get("oyuncuya_saldiri", 0.15)):
                for u, k in oyuncu_hedefleri:
                    if int(k["maps"][0].get("level", 1)) < 6:
                        continue
                    if int(k.get("privateState", {}).get("shield_until", 0) or 0) > simdi:
                        continue
                    guc = ordu_gucu(birim_sayilari(k)) + kule_gucu(k) * 0.6
                    adaylar.append((u, k, max(0.05, (kendi_guc / max(1.0, guc)) ** 0.8 * 0.8)))

        if not adaylar:
            return None

        toplam = sum(a for _, _, a in adaylar)
        secim = random.uniform(0, toplam)
        hedef_id, hedef = adaylar[-1][0], adaylar[-1][1]
        for u, k, agirlik in adaylar:
            secim -= agirlik
            if secim <= 0:
                hedef_id, hedef = u, k
                break

        return self._savas(saldiran_id, saldiran, hedef_id, hedef, simdi,
                           oyuncuya=hedef_id in [u for u, _ in oyuncu_hedefleri])

    def _savas(self, saldiran_id, saldiran, hedef_id, hedef, simdi, oyuncuya=False):
        """Savaşı çözer, kayıtlara ve haberlere yazar; hedefin kimliğini döndürür."""
        saldiran_birimler = birim_sayilari(saldiran)
        if oyuncuya:
            self._son_oyuncu_saldiri = simdi

        # Savunma kişiliği: savunmacı daha fazla birliğini sahaya sürer
        if hedef.get("playerInfo", {}).get("bot"):
            kisi = hedef.get("playerInfo", {}).get("bot_kisi", "dengeli")
            savunma_orani = {"savunmaci": 0.8, "agresif": 0.55, "tuccar": 0.6}.get(kisi, 0.65)
        else:
            # Oyuncunun seçtiği savunma stratejisi (CMD_SET_STRATEGY)
            strateji = int(hedef.get("privateState", {}).get("strategy", 8) or 8)
            savunma_orani = {8: 0.85, 9: 0.7, 7: 0.55, 10: 0.4}.get(strateji, 0.65)
        savunan_birimler = birim_sayilari(hedef)
        savunan_guc = {i: max(1, int(n * savunma_orani)) for i, n in savunan_birimler.items()}

        kisi_s = saldiran.get("playerInfo", {}).get("bot_kisi", "dengeli")
        atak_carpan = {"agresif": 1.6, "tuccar": 1.4, "savunmaci": 1.3}.get(kisi_s, 1.5)

        giden = {i: max(1, int(n * 0.85)) for i, n in saldiran_birimler.items()}
        atak = ordu_gucu(giden) * random.uniform(0.9, 1.2) * atak_carpan * self.savas_carpan
        savunma = ordu_gucu(savunan_guc) + kule_gucu(hedef) * 0.8 * random.uniform(0.9, 1.1)
        kazandi = atak > savunma

        # Kayıplar
        kayip_orani_saldiran = 0.2 if kazandi else 0.45
        kayip_orani_savunan = 0.45 if kazandi else 0.2
        saldiran_kayip = {i: max(0, int(n * kayip_orani_saldiran)) for i, n in giden.items()}
        savunan_kayip = {i: max(0, int(n * kayip_orani_savunan)) for i, n in savunan_birimler.items()}
        birim_sil(saldiran, saldiran_kayip)
        birim_sil(hedef, savunan_kayip)

        # Ganimet
        ganimet = {}
        if kazandi:
            for alan in ("coins", "wood", "stone", "food"):
                mevcut = int(hedef["maps"][0].get(alan, 0))
                # Orijinal oyunda kaynak başına ganimet ~100.000 ile sınırlıydı.
                alinacak = min(int(mevcut * denge.GANIMET_ORANI), denge.GANIMET_TAVANI)
                if alinacak > 0:
                    hedef["maps"][0][alan] = mevcut - alinacak
                    saldiran["maps"][0][alan] = int(saldiran["maps"][0].get(alan, 0)) + alinacak
                    ganimet[alan] = alinacak

        # XP
        hedef_seviye = max(1, int(hedef["maps"][0].get("level", 1)))
        saldiran["maps"][0]["xp"] = int(saldiran["maps"][0].get("xp", 0)) + (max(1, hedef_seviye * 2) if kazandi else 1)
        if kazandi:
            hedef["maps"][0]["xp"] = int(hedef["maps"][0].get("xp", 0)) + 1

        # Raporlar (orijinal Social Empires rapor biçimi)
        rapor = {
            "duration": random.randint(20, 90),
            "townhall_gold": 0,
            "win": 1 if kazandi else 0,
            "resources": {"x": max(1, hedef_seviye * 2) if kazandi else 0,
                          "g": ganimet.get("coins", 0)},
            "attacker_units": [[i, n, 0, 0] for i, n in giden.items()],
            "victim_units": [[i, n, 0, 0] for i, n in savunan_birimler.items()],
            # İstemci bunu savunanın kazancı olarak gösterir; çalınan ganimet değil.
            "resources_victim": {"g": 0},
            "voluntary_end": 0,
            "oponent": {
                "name": saldiran.get("playerInfo", {}).get("name", "Bot"),
                "user_id": str(saldiran_id),
                "world_id": 0,
                "level": int(saldiran["maps"][0].get("level", 1)),
                "pic": saldiran.get("playerInfo", {}).get("pic", ""),
            },
            "time": simdi,
        }
        rapor_ekle(hedef, saldiran, rapor)
        saldiran.setdefault("privateState", {}).setdefault("attacksSent", []).append(
            {"victim_id": str(hedef_id), "time": simdi}
        )
        # Hafıza: saldırılan, saldırana öfkelenir; kaybeden saldıran da öfkelenir.
        self._ofke_artir(hedef, saldiran_id)
        if not kazandi:
            self._ofke_artir(saldiran, hedef_id)
        hafiza = saldiran.setdefault("privateState", {}).setdefault("bot_hafiza", {})
        hafiza["son_hedef"] = {"id": str(hedef_id), "zaman": simdi}

        hedef_ad = hedef.get("playerInfo", {}).get("name", hedef_id)
        saldiran_ad = saldiran.get("playerInfo", {}).get("name", saldiran_id)
        toplam = sum(ganimet.values())
        if kazandi:
            self.olay("savas", f"{saldiran_ad} → {hedef_ad}: kazandı, {toplam} kaynak ganimet")
        else:
            self.olay("savas", f"{saldiran_ad} → {hedef_ad}: saldırı püskürtüldü")
        self._son_sonuc = {"kazandi": kazandi, "ganimet": toplam}

        # Yenilen botun ittifakı (başka ittifaksa) intikam seferi ilan edebilir
        if (kazandi and hedef.get("playerInfo", {}).get("bot")
                and self._ittifak(hedef_id, hedef) != self._ittifak(saldiran_id, saldiran)
                and random.random() < float(self.ayar.get("intikam_olasiligi", 0.35))):
            self._sefer_ilan(self._ittifak(hedef_id, hedef), saldiran_id, saldiran_ad, hedef_ad)
        return hedef_id

    # -- döngü ------------------------------------------------------------
    def dongu(self):
        self._duruyor = False
        while not self._duruyor:
            try:
                time.sleep(max(5, int(self.ayar.get("tick_saniye", 90))))
                self.tek_tick()
            except Exception as hata:  # dünya döngüsü sunucuyu düşürmesin
                print(f" ! Dunya tick hatasi: {hata}")

    def baslat(self):
        global etkin
        etkin = self
        if not self.ayar.get("aktif", True):
            print(" [+] Dunya simulasyonu kapali (ayarlar.json)")
            return
        self._is_parcacigi = threading.Thread(target=self.dongu, name="dunya", daemon=True)
        self._is_parcacigi.start()
        print(f" [+] Dunya simulasyonu basladi (tick: {self.ayar.get('tick_saniye')} sn)")

    def durdur(self):
        self._duruyor = True
        self.bekleyenleri_yaz()

    def bekleyenleri_yaz(self):
        """Biriken bot kayıtlarını yazar (kayıtlar diskten yeniden okunmadan önce çağrılır)."""
        with save_lock:
            bekleyen, self._bekleyen_botlar = self._bekleyen_botlar, set()
            for uid in bekleyen:
                try:
                    save_session(uid)
                except OSError as hata:
                    print(f" ! Dunya kaydi yazilamadi ({uid}): {hata}")

    # -- panel verisi -----------------------------------------------------
    def veri(self):
        simdi = time.time()
        if self._veri_onbellek is not None and simdi - self._veri_zamani < 3:
            return self._veri_onbellek

        oyuncular = []
        for i, (uid, kayit) in enumerate(self.oyuncular()):
            harita = kayit["maps"][0]
            birimler = birim_sayilari(kayit)
            # 9 sütunlu ızgara + kişiye özgü küçük sapma: 50+ köy üst üste binmez
            kolon = 9
            sapma_x = (abs(hash(str(uid))) % 15) - 7
            sapma_y = (abs(hash(str(uid))) % 13) - 6
            x = 90 + (i % kolon) * 76 + sapma_x
            y = 78 + (i // kolon) * 72 + sapma_y
            pi = kayit.get("playerInfo", {})
            hafiza = kayit.get("privateState", {}).get("bot_hafiza", {})
            ofke = hafiza.get("ofke", {}) if isinstance(hafiza, dict) else {}
            oyuncular.append({
                "id": str(uid),
                "ad": pi.get("name", "Oyuncu"),
                "bot": bool(pi.get("bot")),
                "kisi": pi.get("bot_kisi", ""),
                "seviye": int(harita.get("level", 1)),
                "xp": int(harita.get("xp", 0)),
                "kaynaklar": {k: int(harita.get(k, 0)) for k in ("coins", "wood", "stone", "food")},
                "birim": sum(birimler.values()),
                "ofke": len(ofke),
                "kalkan": max(0, int(kayit.get("privateState", {}).get("shield_until", 0) or 0) - int(time.time())),
                "konum": {"x": round(x, 1), "y": round(y, 1)},
                "ittifak": self.ittifak_adi(uid, kayit) if pi.get("bot") else "",
            })
        toplam = {"coins": 0, "wood": 0, "stone": 0, "food": 0, "birim": 0}
        kisi_sayilari = {}
        for o in oyuncular:
            for k in ("coins", "wood", "stone", "food"):
                toplam[k] += o["kaynaklar"][k]
            toplam["birim"] += o["birim"]
            if o["bot"]:
                kisi_sayilari[o["kisi"] or "dengeli"] = kisi_sayilari.get(o["kisi"] or "dengeli", 0) + 1

        veri = {
            "tick": self.tick,
            "toplam": toplam,
            "kisi_sayilari": kisi_sayilari,
            "gecmis": list(self.gecmis),
            "guncelleme": self._son_guncelleme,
            "tick_saniye": int(self.ayar.get("tick_saniye", 60)),
            "sonraki_tick": self._son_guncelleme + int(self.ayar.get("tick_saniye", 60)),
            "aktif": bool(self.ayar.get("aktif", True)),
            "oyuncular": oyuncular,
            "olaylar": list(reversed(self.olaylar[-40:])),
            "seferler": [{"ittifak": ITTIFAKLAR[x["ittifak"]], "hedef": x["hedef_ad"], "kalan": x["kalan"]}
                         for x in self.seferler],
        }
        self._veri_onbellek = veri
        self._veri_zamani = simdi
        return veri
