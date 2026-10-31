"""İstemcinin `command.php` ile gönderdiği oyun komutları.

Oyun mantığı istemcide (Flash) çalışır; istemci her değişikliği bir komut
olarak bildirir ve sunucu aynı değişikliği kayda uygular. Kayıt yeniden
yüklendiğinde istemcinin gördüğüyle aynı olmalıdır; bu yüzden işleyiciler
istemcinin yaptığını birebir taklit eder, kendi kurallarını uygulamaz.

Argüman sıraları istemci bytecode'undan çıkarılmıştır (her işleyicinin
belge dizesinde `[...]` olarak yazılı). Kaynaklar eksiye düşmez.
"""

import json
import math
import os
import traceback

from oyun import pvp
from oyun.config import (get_game_config, get_item_from_id, get_item_from_subcat_functional,
                         get_level_from_xp)
from oyun.ekonomi import apply_collect, apply_collect_xp, apply_cost, timestamp_now
from oyun.kayit import all_saves_userid, neighbor_session, save_session, session
from oyun.oyuncu import acik_kasaba
from oyun.yollar import SAVES_DIR, VILLAGES_DIR
from oyun.zaman import zaman_olcegi

KOMUTLAR = {}

# İstemcideki Config sabitleri (game_config'te yok)
DIVISOR_SELL = 20
MULTIPLIER_UNLOCK = 1 / 3
TOWN_PRICE_CASH = 22
TOWN_PRICE_GOLD = 100000
NEST_PRICE_CASH = 50
NEST_PRICE_GOLD = 100000
COLLECT_MINUTES = [5, 60, 240, 480]

KAYNAK_ALANI = {"g": "coins", "w": "wood", "f": "food", "s": "stone"}


def komut(*adlar):
    """Bir işleyiciyi istemci komut adlarıyla kaydeder."""
    def kaydet(fonksiyon):
        for ad in adlar:
            KOMUTLAR[ad] = fonksiyon
        return fonksiyon
    return kaydet


# ---------------------------------------------------------------------------
# Argümanlar ve kayıt yardımcıları
# ---------------------------------------------------------------------------

class Arg:
    """Komut argümanlarına güvenli erişim (eksik/bozuk değerde varsayılan)."""

    def __init__(self, liste):
        self.liste = list(liste) if isinstance(liste, (list, tuple)) else []

    def __len__(self):
        return len(self.liste)

    def ham(self, i, varsayilan=None):
        return self.liste[i] if i < len(self.liste) else varsayilan

    def tam(self, i, varsayilan=0):
        deger = self.ham(i)
        try:
            return int(float(deger))
        except (TypeError, ValueError):
            return varsayilan

    def ondalik(self, i, varsayilan=1.0):
        try:
            return float(self.ham(i))
        except (TypeError, ValueError):
            return varsayilan

    def metin(self, i, varsayilan=""):
        deger = self.ham(i)
        return varsayilan if deger is None else str(deger)

    def json(self, i, varsayilan=None):
        deger = self.ham(i)
        if isinstance(deger, (dict, list)):
            return deger
        try:
            return json.loads(deger)
        except (TypeError, ValueError):
            return varsayilan


def harita(save, town_id):
    haritalar = save["maps"]
    return haritalar[town_id] if 0 <= town_id < len(haritalar) else haritalar[0]


def esya_bul(h, x, y, esya_id=None):
    for esya in h["items"]:
        if esya[1] == x and esya[2] == y and (esya_id is None or esya[0] == esya_id):
            return esya
    return None


def esya_ekle(h, esya_id, x, y, yon=0):
    h["items"].append([esya_id, x, y, yon, timestamp_now(), 0])


def ozellikler(esya):
    """Eşyanın attrs sözlüğü (eşya 8 elemana tamamlanır)."""
    while len(esya) < 6:
        esya.append(0)
    if len(esya) < 7:
        esya.append([])
    if len(esya) < 8 or not isinstance(esya[7], dict):
        esya[7:] = [{}]
    return esya[7]


def cash_ekle(save, miktar):
    pi = save["playerInfo"]
    pi["cash"] = max(0, int(pi.get("cash", 0)) + int(miktar))


def kaynak_ekle(save, h, tur, miktar):
    """tur: g/w/f/s (harita), c (cash), m (mana). Eksiye düşmez."""
    miktar = int(miktar)
    if tur == "c":
        cash_ekle(save, miktar)
    elif tur == "m":
        ps = save["privateState"]
        ps["mana"] = max(0, int(ps.get("mana", 0)) + miktar)
    elif tur in KAYNAK_ALANI:
        alan = KAYNAK_ALANI[tur]
        h[alan] = max(0, int(h.get(alan, 0)) + miktar)


def depo_ekle(save, esya_id, adet=1):
    if esya_id < 0 or adet <= 0:
        return
    gifts = save["privateState"].setdefault("gifts", [])
    if len(gifts) <= esya_id:
        gifts.extend([0] * (esya_id - len(gifts) + 1))
    gifts[esya_id] += adet


def depo_cikar(save, esya_id):
    """Depodan bir eşya düşer; depoda yoksa False (tekrarlanan komut)."""
    gifts = save["privateState"].setdefault("gifts", [])
    if not 0 <= esya_id < len(gifts) or gifts[esya_id] <= 0:
        return False
    gifts[esya_id] -= 1
    while gifts and gifts[-1] == 0:
        gifts.pop()
    return True


def satis_iadesi(save, h, esya_id):
    """Satılan eşyanın %5'i iade edilir (cash ile alınanlar hariç)."""
    esya = get_item_from_id(esya_id)
    if esya and esya.get("cost_type") != "c":
        apply_cost(save["playerInfo"], h, esya_id, -0.05)


def listeye_ekle(kap, anahtar, deger):
    liste = kap.get(anahtar)
    if not isinstance(liste, list):
        liste = kap[anahtar] = []
    if deger not in liste:
        liste.append(deger)
    return liste


def globals_():
    return get_game_config().get("globals", {})


# ---------------------------------------------------------------------------
# Ana döngü
# ---------------------------------------------------------------------------

def command(USERID, data):
    gunluk = []
    for komut_verisi in data.get("commands", []):
        cmd = komut_verisi.get("cmd")
        args = komut_verisi.get("args", [])
        gunluk.append((cmd, args))
        try:
            do_command(USERID, cmd, args)
        except Exception:
            # Bozuk tek bir komut aynı paketteki diğerlerini düşürmesin.
            print(f" ! KOMUT HATASI: {cmd} args={args}")
            traceback.print_exc()
    _gunluge_yaz(USERID, gunluk)
    save_session(USERID)


def do_command(USERID, cmd, args):
    save = session(USERID)
    isleyici = KOMUTLAR.get(cmd)
    if isleyici is None:
        print(f" ! Bilinmeyen komut '{cmd}' args={args}")
        return
    print(f" [+] KOMUT: {cmd} {args}")
    isleyici(save, Arg(args))


def _gunluge_yaz(USERID, komutlar):
    """Paketteki komutları saves/komut_gunlugu.jsonl'a yazar (hata ayıklama)."""
    if not komutlar:
        return
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        simdi = timestamp_now()
        with open(os.path.join(SAVES_DIR, "komut_gunlugu.jsonl"), "a", encoding="utf-8") as f:
            for cmd, args in komutlar:
                f.write(json.dumps({"ts": simdi, "user": str(USERID), "cmd": cmd, "args": args},
                                   ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Kayıt değiştirmeyen komutlar
# ---------------------------------------------------------------------------

@komut("game_status", "ping", "system_set_count_hack", "perform_city_quest",
       "spy_player", "reset_position_univers",
       "rt_publish_achievement_unit", "start_quest", "gold_statue_conversion",
       # Yalnızca istemcideki geliştirici panelinden gelenler:
       "fast_forward", "load_map", "save_map", "reset", "clear_tiles_area", "set_variables")
def kayitsiz(save, a):
    pass


# ---------------------------------------------------------------------------
# Eşyalar: satın alma, taşıma, satma, depo
# ---------------------------------------------------------------------------

@komut("buy")
def buy(save, a):
    """[id, x, y, yon, kasaba, kaynak_dusme(1=bedava), fiyat_carpani, tur]"""
    esya_id, town = a.tam(0), a.tam(4)
    h = harita(save, town)
    if not a.tam(5):
        apply_cost(save["playerInfo"], h, esya_id, a.ondalik(6, 1.0))
        h["xp"] = int(h.get("xp", 0)) + int((get_item_from_id(esya_id) or {}).get("xp", 0) or 0)
    esya_ekle(h, esya_id, a.tam(1), a.tam(2), a.tam(3))


@komut("move")
def move(save, a):
    """[eski_x, eski_y, id, yeni_x, yeni_y, yon, kasaba, neden]"""
    esya = esya_bul(harita(save, a.tam(6)), a.tam(0), a.tam(1), a.tam(2))
    if esya:
        esya[1], esya[2], esya[3] = a.tam(3), a.tam(4), a.tam(5)


@komut("orient")
def orient(save, a):
    """[x, y, yon, kasaba]"""
    esya = esya_bul(harita(save, a.tam(3)), a.tam(0), a.tam(1))
    if esya:
        esya[3] = a.tam(2)


@komut("sell")
def sell(save, a):
    """[x, y, id, kasaba, kaynak_dokunma(1), neden, (mezarliga_git)]"""
    esya_id = a.tam(2)
    h = harita(save, a.tam(3))
    esya = esya_bul(h, a.tam(0), a.tam(1), esya_id)
    if esya is None:
        return
    h["items"].remove(esya)
    if not a.tam(4):
        satis_iadesi(save, h, esya_id)
    if a.tam(6):
        mezarliga_ekle(save, esya_id)


@komut("kill")
def kill(save, a):
    """[x, y, id, kasaba, tur]"""
    h = harita(save, a.tam(3))
    esya = esya_bul(h, a.tam(0), a.tam(1), a.tam(2))
    if esya:
        apply_collect_xp(h, esya[0])
        h["items"].remove(esya)


@komut("store_item", "store_item_frombug")
def store_item(save, a):
    """[x, y, kasaba, id]"""
    esya_id = a.tam(3)
    h = harita(save, a.tam(2))
    esya = esya_bul(h, a.tam(0), a.tam(1), esya_id)
    if esya:
        h["items"].remove(esya)
    depo_ekle(save, esya_id)


@komut("place_gift", "place_stored_item")
def place_gift(save, a):
    """[id, x, y, yon, kasaba]"""
    esya_id = a.tam(0)
    if depo_cikar(save, esya_id):
        esya_ekle(harita(save, a.tam(4)), esya_id, a.tam(1), a.tam(2), a.tam(3))


@komut("sell_gift", "sell_stored_item")
def sell_gift(save, a):
    """[id, kasaba]"""
    esya_id = a.tam(0)
    if depo_cikar(save, esya_id):
        satis_iadesi(save, harita(save, a.tam(1)), esya_id)


@komut("buy_stored_item_cash")
def buy_stored_item_cash(save, a):
    """[kasaba, id, cash]"""
    cash_ekle(save, -a.tam(2))
    depo_ekle(save, a.tam(1))


@komut("add_items_store")
def add_items_store(save, a):
    """[json id listesi, cash]"""
    cash_ekle(save, -a.tam(1))
    for esya_id in a.json(0, []) or []:
        depo_ekle(save, int(esya_id))


@komut("store_add_items")
def store_add_items(save, a):
    """[json id listesi]"""
    for esya_id in a.json(0, []) or []:
        depo_ekle(save, int(esya_id))


@komut("upgrade")
def upgrade(save, a):
    """[x, y, kasaba] - aynı binanın seviyesi bir artar."""
    esya = esya_bul(harita(save, a.tam(2)), a.tam(0), a.tam(1))
    if esya:
        ozellikler(esya)
        esya[5] = int(esya[5] or 0) + 1


@komut("expand")
def expand(save, a):
    """[arazi_id, 'gold'|'cash', kasaba]"""
    arazi = a.tam(0)
    h = harita(save, a.tam(2))
    if arazi in h["expansions"]:
        return
    fiyatlar = get_game_config()["expansion_prices"]
    fiyat = fiyatlar[min(len(h["expansions"]) - 1, len(fiyatlar) - 1)]
    if a.metin(1) == "gold":
        kaynak_ekle(save, h, "g", -int(fiyat["coins"]))
    elif a.metin(1) == "cash":
        cash_ekle(save, -int(fiyat["cash"]))
    h["expansions"].append(arazi)


@komut("name_map")
def name_map(save, a):
    """[kasaba, ad]"""
    save["playerInfo"]["map_names"][a.tam(0)] = a.metin(1)


@komut("buy_map")
def buy_map(save, a):
    """[1, cash_ile(1|0), irk, mevcut_kasaba] - ikinci kasabayı açar."""
    if len(save["maps"]) > 1:
        return  # zaten açık (tekrarlanan komut): yeniden ücret alma
    if a.tam(1):
        cash_ekle(save, -TOWN_PRICE_CASH)
    else:
        kaynak_ekle(save, harita(save, a.tam(3)), "g", -TOWN_PRICE_GOLD)
    with open(os.path.join(VILLAGES_DIR, "initial.json"), encoding="utf-8") as f:
        yeni = json.load(f)["maps"][0]
    yeni.update({"id": 1, "race": a.metin(2) or "h", "timestamp": timestamp_now()})
    save["maps"].append(yeni)
    pi = save["playerInfo"]
    for alan, varsayilan in (("map_names", "Troll Empire"), ("map_sizes", 0)):
        liste = pi.setdefault(alan, [])
        if len(liste) < 2:
            liste.append(varsayilan if alan == "map_names" or not liste else liste[0])


@komut("set_skin")
def set_skin(save, a):
    """[kasaba, tema_id]"""
    harita(save, a.tam(0))["skin"] = a.tam(1)


@komut("unlock_skin")
def unlock_skin(save, a):
    """[tema_id] - istemci COST_UNLOCK_SKIN cash düşer."""
    cash_ekle(save, -int(globals_().get("COST_UNLOCK_SKIN", 20)))
    save["privateState"].setdefault("unlockedSkins", {})[a.metin(0)] = True


@komut("unlock_building")
def unlock_building(save, a):
    """[bina_id] - erken açma bedeli ceil(min_level / 3) cash."""
    esya = get_item_from_id(a.tam(0)) or {}
    cash_ekle(save, -math.ceil(int(esya.get("min_level", 0) or 0) * MULTIPLIER_UNLOCK))
    save["privateState"].setdefault("unlockedEarlyBuildings", {})[a.metin(0)] = True


# ---------------------------------------------------------------------------
# Üretim ve toplama
# ---------------------------------------------------------------------------

@komut("collect_new")
def collect_new(save, a):
    """[x, y, kasaba, id, (icindeki_birim, carpan, cash)]"""
    esya_id = a.tam(3)
    h = harita(save, a.tam(2))
    carpan = max(1, min(a.tam(5, 1), 10))
    apply_collect(save["playerInfo"], h, esya_id, carpan)
    cash_ekle(save, -a.tam(6))
    esya = esya_bul(h, a.tam(0), a.tam(1), esya_id)
    if esya and len(esya) > 4:
        esya[4] = timestamp_now()


@komut("activate")
def activate(save, a):
    """[x, y, kasaba, id, uretim_secimi(0-4)]"""
    esya = esya_bul(harita(save, a.tam(2)), a.tam(0), a.tam(1), a.tam(3))
    if esya is None:
        return
    secim = a.tam(4)
    ozellikler(esya)["cp"] = secim
    if secim > 0:
        esya[4] = timestamp_now()


@komut("accept_collect_help")
def accept_collect_help(save, a):
    """[x, y, kasaba, id, arkadas] - üretim COLLECT_HELP_SECONDS kısalır."""
    esya = esya_bul(harita(save, a.tam(2)), a.tam(0), a.tam(1), a.tam(3))
    if esya:
        ozellikler(esya).setdefault("hc", {})[a.metin(4)] = True
        esya[4] = int(esya[4]) - int(globals_().get("COLLECT_HELP_SECONDS", 3600))


@komut("assist_send_feed")
def assist_send_feed(save, a):
    """[x, y, kasaba, id, arkadas]"""
    esya = esya_bul(harita(save, a.tam(2)), a.tam(0), a.tam(1), a.tam(3))
    if esya:
        ozellikler(esya).setdefault("sif", {})[a.metin(4)] = True


@komut("set_resource_allies")
def set_resource_allies(save, a):
    """[kaynak('g','f','w','s','n'), x, y, kasaba, id]"""
    h = harita(save, a.tam(3))
    h["resourceAlliesMarket"] = a.metin(0)
    if a.metin(0) != "n":
        esya = esya_bul(h, a.tam(1), a.tam(2), a.tam(4))
        if esya:
            esya[4] = timestamp_now()


@komut("trade_resource_b")
def trade_resource_b(save, a):
    """[kasaba, kaynak('w','s','f'), satis(1|0), miktar] - istemci formülüyle."""
    g = globals_()
    h = harita(save, a.tam(0))
    kaynak, satis, miktar = a.metin(1), a.tam(2) == 1, a.tam(3)
    if kaynak not in ("w", "s", "f") or miktar <= 0:
        return
    sayac = h.get("resourcesTraded")
    if not isinstance(sayac, dict):
        sayac = h["resourcesTraded"] = {}
    islem = int(sayac.get(kaynak, 0))
    taban = g["MARKET_BASE_COSTS"][kaynak] * miktar / 100
    fiyat = math.floor(taban + taban * islem * g["MARKET_INCREMENT"] + 0.5)
    if satis:
        fiyat = math.floor(fiyat * g["MARKET_SELL_PERCENTAGE"] + 0.5)
    yon = 1 if satis else -1
    kaynak_ekle(save, h, "g", yon * fiyat)
    kaynak_ekle(save, h, kaynak, -yon * miktar)
    sayac[kaynak] = max(-g["MARKET_MAX_DECREMENTS"], min(g["MARKET_MAX_INCREMENTS"], islem - yon))


@komut("exchange_cash_new")
def exchange_cash_new(save, a):
    """[kasaba]"""
    g = globals_()
    cash_ekle(save, -int(g.get("EXCHANGE_CASH", 5)))
    kaynak_ekle(save, harita(save, a.tam(0)), "g", int(g.get("EXCHANGE_GOLD", 2500)))


# ---------------------------------------------------------------------------
# Birimler ve binalar içindeki birimler
# ---------------------------------------------------------------------------

@komut("push_unit")
def push_unit(save, a):
    """[birim_x, birim_y, birim_id, bina_x, bina_y, kasaba]"""
    h = harita(save, a.tam(5))
    birim_id = a.tam(2)
    bina = esya_bul(h, a.tam(3), a.tam(4))
    if bina:
        ozellikler(bina)
        bina[6].append(birim_id)
    birim = esya_bul(h, a.tam(0), a.tam(1), birim_id)
    if birim:
        h["items"].remove(birim)


@komut("pop_unit")
def pop_unit(save, a):
    """[bina_x, bina_y, kasaba, birim_id, (x, y, yon)]"""
    h = harita(save, a.tam(2))
    birim_id = a.tam(3)
    bina = esya_bul(h, a.tam(0), a.tam(1))
    if bina and len(bina) > 6 and birim_id in bina[6]:
        bina[6].remove(birim_id)
    if len(a) > 4:
        esya_ekle(h, birim_id, a.tam(4), a.tam(5), a.tam(6))


@komut("pop_sell")
def pop_sell(save, a):
    """[bina_x, bina_y, kasaba, bina_id, birim_id] - kurban binası."""
    h = harita(save, a.tam(2))
    birim_id = a.tam(4)
    bina = esya_bul(h, a.tam(0), a.tam(1), a.tam(3))
    if bina is None:
        return
    if len(bina) > 6 and birim_id in bina[6]:
        bina[6].remove(birim_id)
    birim = get_item_from_id(birim_id) or {}
    if birim.get("cost_type") == "g":
        kaynak_ekle(save, h, "g", int(birim.get("cost", 0) or 0) // DIVISOR_SELL)
    if len(bina) > 6 and not bina[6]:
        bina[4] = timestamp_now()


# Eğitim kuyruğu (1.4.07, BuildingQueueManager / BuildingQueueData). Kuyruk privateState.barracksQueues[qid]
# = {"ts": sıradaki birimin eğitime başladığı an, "amount": kalan birim, "unit": birim id}; qid binanın
# attrs'ındaki "bq". Bedel ve iade formülü istemciden (docs/inceleme/1407-formuller.md). Ruh Karıştırıcı'da
# (1529) eğitim bedelsizdir, xp vermez ve sm_training_time kullanır.
KUYRUK_SINIRI = 5  # BuildingQueueManager/addUnit: remainingUnits < 5
RUH_KARISTIRICI = 1529
DEMIRCI, UNIVERSITE = 131, 134  # SUBCATFUNC_BUILDING_*
INDIRIM = 0.9  # REDUCTION_MULTIPLIER_BLACKSMITH / _UNIVERSITY
DEMIRCI_BIRIMLERI = (78, 79, 80)  # piyade, atlı, okçu
KUSATMA = 81
KOYLU = 71
EGITIM_YEMEGI = 2  # FOOD_PER_GOLD_INTRAINING
HIZLANDIRMA_SAATI = 1  # COST_SPEED_UP_UNIT_QUEUE: kalan her (başlamış) saat için nakit


def kuyruklar(save):
    ps = save["privateState"]
    if not isinstance(ps.get("barracksQueues"), dict):
        ps["barracksQueues"] = {}
    return ps["barracksQueues"]


def egitim_suresi(birim, ruh_karistirici=False):
    """İstemcinin gördüğü süre: config'te ölçeğe bölünür (config.get_client_game_config), istemci tam sayıya keser."""
    deger = birim.get("sm_training_time" if ruh_karistirici else "training_time")
    try:
        sayi = float(deger)
    except (TypeError, ValueError):
        return 0
    olcek = zaman_olcegi()
    if sayi > 0 and olcek != 1.0:
        sayi = float(f"{sayi / olcek:.6g}")
    return int(sayi)


def egitim_bedeli(h, birim):
    """(bedel, yemek) - BuildingQueueManager/addUnit, BuildingQueueData/returnCost.

    Haritada demirci varsa piyade/atlı/okçu, üniversite varsa kuşatma birimi %10 ucuz (yukarı yuvarlanır);
    üstüne bedelin iki katı yemek."""
    bedel = int(float(birim.get("cost", 0) or 0))
    alt = int(birim.get("subcat_functional", 0) or 0)
    if alt in DEMIRCI_BIRIMLERI:
        bina = DEMIRCI
    elif alt == KUSATMA:
        bina = UNIVERSITE
    else:
        bina = None
    if bina and any(int((get_item_from_id(e[0]) or {}).get("subcat_functional", 0) or 0) == bina
                    for e in h["items"]):
        bedel = math.ceil(bedel * INDIRIM)
    return bedel, math.ceil(bedel * EGITIM_YEMEGI)


def egitim_odemesi(h, birim, bina_id):
    """[(kaynak, miktar), ...]: eğitimde alınan. Ruh Karıştırıcı'da bedel yok, köylüde yemek yok."""
    if bina_id == RUH_KARISTIRICI:
        return []
    bedel, yemek = egitim_bedeli(h, birim)
    odeme = [(birim.get("cost_type"), bedel)]
    if int(birim.get("subcat_functional", 0) or 0) != KOYLU:
        odeme.append(("f", yemek))
    return odeme


@komut("push_queue_unit")
def push_queue_unit(save, a):
    """[bina_x, bina_y, bina_id, birim_id, kuyruk_no, ruh_karistirici_degil] - açık kasabada."""
    h = harita(save, acik_kasaba(save["playerInfo"].get("pid")))
    bina_id, birim_id, qid = a.tam(2), a.tam(3), str(a.tam(4))
    bina = esya_bul(h, a.tam(0), a.tam(1), bina_id)
    birim = get_item_from_id(birim_id)
    if bina is None or birim is None:
        print(" ! kuyruk: bina ya da birim yok")
        return
    kuyruk = kuyruklar(save).get(qid)
    if kuyruk and int(kuyruk.get("amount", 0)) >= KUYRUK_SINIRI:
        print(" ! kuyruk dolu")
        return
    ozellikler(bina)["bq"] = qid
    if kuyruk and int(kuyruk.get("amount", 0)) > 0:
        kuyruk["amount"] = int(kuyruk["amount"]) + 1
        kuyruk["unit"] = birim_id
    else:
        kuyruklar(save)[qid] = {"ts": timestamp_now(), "amount": 1, "unit": birim_id}
    for tur, miktar in egitim_odemesi(h, birim, bina_id):
        kaynak_ekle(save, h, tur, -miktar)


def _kuyruk_ve_bina(save, h, qid):
    kuyruk = kuyruklar(save).get(qid)
    bina = next((e for e in h["items"] if len(e) > 7 and isinstance(e[7], dict) and e[7].get("bq") == qid), None)
    return kuyruk, bina


def _kuyruktan_dus(save, qid, kuyruk, bina, sure=0):
    kuyruk["amount"] = int(kuyruk.get("amount", 0)) - 1
    kuyruk["ts"] = int(kuyruk.get("ts", 0)) + sure
    if kuyruk["amount"] <= 0:
        del kuyruklar(save)[qid]
        if bina is not None:
            bina[7].pop("bq", None)


@komut("pop_queue_unit")
def pop_queue_unit(save, a):
    """[kuyruk_no, x, y, bina_id] - sıradaki birim eğitimi bitince haritaya çıkar.

    Sıradakinin başlangıcı bir öncekinin bitişidir (BuildingQueueData/setData zinciri)."""
    h = harita(save, acik_kasaba(save["playerInfo"].get("pid")))
    qid = a.metin(0)
    kuyruk, bina = _kuyruk_ve_bina(save, h, qid)
    if not kuyruk:
        print(" ! kuyruk yok:", qid)
        return
    birim_id = int(kuyruk.get("unit", 0))
    birim = get_item_from_id(birim_id) or {}
    ruh = a.tam(3) == RUH_KARISTIRICI
    esya_ekle(h, birim_id, a.tam(1), a.tam(2))
    if not ruh:
        h["xp"] = int(h.get("xp", 0)) + int(birim.get("xp", 0) or 0)
    _kuyruktan_dus(save, qid, kuyruk, bina, egitim_suresi(birim, ruh))


@komut("unqueue_unit")
def unqueue_unit(save, a):
    """[kuyruk_no, bina_id] - kuyruktan bir birim çıkar, eğitimde alınan iade edilir.

    İstemcinin iadesi (BuildingQueueData/returnCost) köylüde alınmayan yemeği, Ruh Karıştırıcı'da alınmayan bedeli
    de verir; sahibinin kararıyla sunucu yalnızca alınanı iade eder (KAR-11, KYT-04). İstemci fazlayı o oturumda
    gösterir, yeniden yüklenince kayıttaki değer görünür."""
    h = harita(save, acik_kasaba(save["playerInfo"].get("pid")))
    qid = a.metin(0)
    kuyruk, bina = _kuyruk_ve_bina(save, h, qid)
    if not kuyruk:
        print(" ! kuyruk yok:", qid)
        return
    birim = get_item_from_id(int(kuyruk.get("unit", 0))) or {}
    for tur, miktar in egitim_odemesi(h, birim, a.tam(1)):
        kaynak_ekle(save, h, tur, miktar)
    _kuyruktan_dus(save, qid, kuyruk, bina)  # istemci sondakini çıkarır: sıradakinin başlangıcı değişmez


@komut("speed_up_queue")
def speed_up_queue(save, a):
    """[kuyruk_no] - kalan bütün birimler hemen biter; kalan sürenin başlamış her saati için nakit.

    Kalan süre (BuildingQueueData/get remainingSeconds): sıradakinin kalanı + bekleyenlerin tam süresi.
    İstemci ardından her birim için pop_queue_unit gönderir."""
    h = harita(save, acik_kasaba(save["playerInfo"].get("pid")))
    qid = a.metin(0)
    kuyruk, bina = _kuyruk_ve_bina(save, h, qid)
    if not kuyruk:
        print(" ! kuyruk yok:", qid)
        return
    birim = get_item_from_id(int(kuyruk.get("unit", 0))) or {}
    sure = egitim_suresi(birim, bool(bina) and bina[0] == RUH_KARISTIRICI)
    adet, simdi = int(kuyruk.get("amount", 0)), timestamp_now()
    kalan = max(0, int(kuyruk.get("ts", 0)) + sure - simdi + (adet - 1) * sure)
    bedel = math.ceil(kalan / 3600) * HIZLANDIRMA_SAATI
    if int(save["playerInfo"].get("cash", 0)) < bedel:
        print(" ! hizlandirma icin nakit yetmiyor")
        return
    cash_ekle(save, -bedel)
    kuyruk["ts"] = simdi - adet * sure


# Birlik paketleri (1.4.07, UnitPacksManager). Bedel burada düşülür; paketten çıkan birlikleri istemci
# get_up_data.php'nin rastgele sayılarıyla kendisi seçer ve her birini store_add_items ile depoya bildirir.
# Kayıtta privateState.unitPacks = {paket_no: alınan adet} (initPlayerData).
PAKET_INDIRIMI = ((8, 0.85), (2, 0.9))  # NUM_SECOND_DISCOUNT / SECOND_DISCOUNT, NUM_FIRST_ / FIRST_


def paket_bedeli(paket, adet):
    """(kaynak, toplam) - UnitPacksManager/buyPack: adet × fiyat; 8 ve üstünde %15, 2 ve üstünde %10 indirim."""
    fiyat = paket.get("price") or {}
    tur = "g" if fiyat.get("g") is not None else "c" if fiyat.get("c") is not None else None
    if tur is None:
        return None, 0
    toplam = int(float(fiyat[tur]) * adet)
    for sinir, carpan in PAKET_INDIRIMI:
        if adet >= sinir:
            toplam = int(toplam * carpan + 0.5)
            break
    return tur, toplam


@komut("buy_unit_pack")
def buy_unit_pack(save, a):
    """[paket_no, adet] - açık kasabanın altınıyla ya da nakitle."""
    no, adet = a.tam(0), a.tam(1)
    paket = next((p for p in get_game_config().get("unit_packs", []) if int(p.get("id", -1)) == no), None)
    if paket is None or adet <= 0:
        print(" ! birlik paketi yok:", no)
        return
    ps = save["privateState"]
    alinanlar = ps.get("unitPacks") if isinstance(ps.get("unitPacks"), dict) else {}
    alinan = int(alinanlar.get(str(no), 0) or 0)
    sinir = int(paket.get("max_purchable", 0) or 0)
    if sinir and alinan + adet > sinir:
        print(" ! birlik paketi siniri:", no)
        return
    h = harita(save, acik_kasaba(save["playerInfo"].get("pid")))
    tur, toplam = paket_bedeli(paket, adet)
    eldeki = int(save["playerInfo"].get("cash", 0)) if tur == "c" else int(h.get("coins", 0))
    if tur is None or eldeki < toplam:
        print(" ! birlik paketi icin kaynak yetmiyor")
        return
    kaynak_ekle(save, h, tur, -toplam)
    alinanlar[str(no)] = alinan + adet
    ps["unitPacks"] = alinanlar


@komut("add_unit_warehouse")
def add_unit_warehouse(save, a):
    """[x, y, kasaba, birim_id]"""
    h = harita(save, a.tam(2))
    birim_id = a.tam(3)
    birim = esya_bul(h, a.tam(0), a.tam(1), birim_id)
    if birim:
        h["items"].remove(birim)
    h.setdefault("warehousedUnits", []).append(birim_id)


@komut("place_warehoused_item")
def place_warehoused_item(save, a):
    """[birim_id, x, y, yon, kasaba]"""
    h = harita(save, a.tam(4))
    birim_id = a.tam(0)
    depodaki = h.setdefault("warehousedUnits", [])
    if birim_id in depodaki:
        depodaki.remove(birim_id)
    esya_ekle(h, birim_id, a.tam(1), a.tam(2), a.tam(3))


@komut("reset_warehouse")
def reset_warehouse(save, a):
    """[kasaba] - birim deposu kaldırılınca içindekiler depoya gider."""
    h = harita(save, a.tam(0))
    for birim_id in h.get("warehousedUnits", []):
        depo_ekle(save, int(birim_id))
    h["warehousedUnits"] = []


@komut("admin_add_animal")
def admin_add_animal(save, a):
    """[alt_kategori, adet]"""
    alt = a.metin(0)
    hayvanlar = save["privateState"].setdefault("arrayAnimals", {})
    hayvanlar[alt] = int(hayvanlar.get(alt, 0)) + a.tam(1)
    print("Hayvan eklendi:", (get_item_from_subcat_functional(alt) or {}).get("name"))


@komut("buy_cash")
def buy_cash(save, a):
    """[birim_id, x, y, yon, kasaba] - cash ile birim (cost_unit_cash)."""
    birim_id = a.tam(0)
    birim = get_item_from_id(birim_id) or {}
    h = harita(save, a.tam(4))
    cash_ekle(save, -int(birim.get("cost_unit_cash", 0) or 0))
    h["xp"] = int(h.get("xp", 0)) + int(birim.get("xp", 0) or 0)
    esya_ekle(h, birim_id, a.tam(1), a.tam(2), a.tam(3))


@komut("increase_population")
def increase_population(save, a):
    """[kasaba] - nüfus sınırı bir adım (POPULATION_INCREASE) artar."""
    h = harita(save, a.tam(0))
    h["increasedPopulation"] = int(h.get("increasedPopulation", 0) or 0) + 1


# ---------------------------------------------------------------------------
# Seviye, görevler, eğitim
# ---------------------------------------------------------------------------

@komut("complete_tutorial")
def complete_tutorial(save, a):
    """[adim] - 31. adımdan (ejderha seçimi) sonra eğitim bitmiş sayılır."""
    if a.tam(0) >= 31:
        save["playerInfo"]["completed_tutorial"] = 1
        save["privateState"]["dragonNestActive"] = 1


@komut("rt_level_up")
def rt_level_up(save, a):
    """[seviye]"""
    seviyeler = get_game_config()["levels"]
    seviye = max(0, min(a.tam(0), len(seviyeler) - 1))
    h = save["maps"][0]
    h["level"] = seviye
    asgari = int(seviyeler[seviye]["exp_required"])
    h["xp"] = max(asgari, min(int(h.get("xp", 0)), int(seviyeler[-1]["exp_required"])))


@komut("rt_publish_score")
def rt_publish_score(save, a):
    """[xp] - aralık dışı değerler (bilinen 2 milyar XP hatası) yok sayılır."""
    xp = a.tam(0, -1)
    if not 0 <= xp <= int(get_game_config()["levels"][-1]["exp_required"]):
        print(f" ! publish_score: mantiksiz XP ({xp}), yok sayildi")
        return
    h = save["maps"][0]
    h["xp"] = xp
    h["level"] = get_level_from_xp(xp)


@komut("complete_mission")
def complete_mission(save, a):
    """[gorev_id, cash_ile_atla(1|0)]"""
    if a.tam(1):
        cash_ekle(save, -int(globals_().get("PRICE_COMPLETE_GOAL", 2)))
    listeye_ekle(save["privateState"], "completedMissions", a.tam(0))


@komut("reward_mission")
def reward_mission(save, a):
    """[kasaba, gorev_id] - ödül hedefin 'reward' altını. 1.4.07 hedefleri `goals`'tan okur (GEC-02)."""
    gorev_id = a.tam(1)
    ps = save["privateState"]
    if gorev_id in ps.get("rewardedMissions", []):
        return
    config = get_game_config()
    gorev = next((g for g in config.get("goals", config["missions"]) if int(g["id"]) == gorev_id), {})
    kaynak_ekle(save, harita(save, a.tam(0)), "g", int(gorev.get("reward", 0) or 0))
    listeye_ekle(ps, "rewardedMissions", gorev_id)


@komut("reset_completed_missions")
def reset_completed_missions(save, a):
    save["privateState"]["completedMissions"] = []
    save["privateState"]["rewardedMissions"] = []


@komut("set_strategy")
def set_strategy(save, a):
    """[strateji]"""
    save["privateState"]["strategy"] = a.tam(0)


@komut("set_help_map")
def set_help_map(save, a):
    """[yardim_turu] - görülen yardım pencereleri listesi."""
    yardim = save["privateState"].get("helpMap")
    if not isinstance(yardim, list):
        yardim = save["privateState"]["helpMap"] = []
    if a.ham(0) not in yardim:
        yardim.append(a.ham(0))


@komut("set_info_showed")
def set_info_showed(save, a):
    """[indeks, deger]"""
    liste = save["privateState"].get("infoShowed")
    if not isinstance(liste, list):
        liste = save["privateState"]["infoShowed"] = []
    i = a.tam(0)
    if 0 <= i < 1000:
        liste.extend([0] * (i + 1 - len(liste)))
        liste[i] = a.ham(1)


@komut("clear_message")
def clear_message(save, a):
    save["privateState"]["message"] = None


@komut("reset_world_change")
def reset_world_change(save, a):
    save["privateState"]["worldChange"] = 0


@komut("set_fake_neighbors")
def set_fake_neighbors(save, a):
    """[id, id, id] ('0' = boş)"""
    save["privateState"]["fakeNeighbors"] = [x for x in a.liste if str(x) != "0"]


@komut("cross_promotion_finished")
def cross_promotion_finished(save, a):
    """[promosyon_id]"""
    listeye_ekle(save["privateState"], "crossPromotionsFinished", a.ham(0))


# ---------------------------------------------------------------------------
# Bonuslar ve ödüller (miktarları istemci seçer)
# ---------------------------------------------------------------------------

@komut("win_bonus")
def win_bonus(save, a):
    """[altin, kasaba, kahraman_id, gun, cash] - günlük bonus."""
    h = harita(save, a.tam(1))
    kaynak_ekle(save, h, "g", a.tam(0))
    cash_ekle(save, a.tam(4))
    if a.tam(2):
        depo_ekle(save, a.tam(2))
    ps = save["privateState"]
    ps["bonusNextId"] = a.tam(3) + 1
    ps["timestampLastBonus"] = timestamp_now()


def _tur_deger_odulu(save, h, tur, deger):
    if tur == "u":
        depo_ekle(save, int(deger))
    elif tur in ("g", "c", "w", "f", "s", "m"):
        kaynak_ekle(save, h, tur, int(deger))


@komut("weekly_reward")
def weekly_reward(save, a):
    """[tur('u','g','c'...), deger] - pazartesi bonusu."""
    _tur_deger_odulu(save, save["maps"][0], a.metin(0), a.tam(1))
    save["privateState"]["timestampLastMondayBonus"] = timestamp_now()


@komut("comeback_reward")
def comeback_reward(save, a):
    """[tur, deger, gun] - geri dönüş bonusu."""
    _tur_deger_odulu(save, save["maps"][0], a.metin(0), a.tam(1))
    listeye_ekle(save["privateState"], "comebackBonusCollected", a.tam(2))


@komut("collect_treasure")
def collect_treasure(save, a):
    """[altin, xp, gorev_id, x, y, kasaba]"""
    h = harita(save, a.tam(5))
    kaynak_ekle(save, h, "g", a.tam(0))
    h["xp"] = int(h.get("xp", 0)) + max(0, a.tam(1))


@komut("apply_rewards_ranking")
def apply_rewards_ranking(save, a):
    """[seviye, cash, json{esya_id: adet}] - ada sıralama ödülü."""
    ps = save["privateState"]
    if a.tam(0) in ps.get("rankingRewarded", []):
        return
    listeye_ekle(ps, "rankingRewarded", a.tam(0))
    cash_ekle(save, a.tam(1))
    for esya_id, adet in (a.json(2, {}) or {}).items():
        depo_ekle(save, int(esya_id), int(adet))


@komut("buy_offer_pack")
def buy_offer_pack(save, a):
    """[kasaba, paket_id, (secilen_esya)]"""
    paket = next((p for p in get_game_config().get("offer_packs", [])
                  if str(p.get("id")) == a.metin(1)), None)
    if paket is None:
        return
    h = harita(save, a.tam(0))
    cash_ekle(save, -int(paket.get("cost_cash", 0) or 0))
    for alan, tur in (("gold", "g"), ("wood", "w"), ("stone", "s"), ("food", "f"), ("mana", "m")):
        kaynak_ekle(save, h, tur, int(paket.get(alan, 0) or 0))
    h["xp"] = int(h.get("xp", 0)) + int(paket.get("xp", 0) or 0)
    secim = a.tam(2, 0) if len(a) > 2 else 0
    for oge in paket.get("items", []) or []:
        if isinstance(oge, (list, tuple)):  # seçmeli grup: oyuncunun seçtiği
            if secim and secim in [int(x) for x in oge]:
                depo_ekle(save, secim)
        elif int(oge) > 0:
            depo_ekle(save, int(oge))


@komut("buy_super_offer_pack")
def buy_super_offer_pack(save, a):
    """[kasaba, paket_id, "id,id,...", cash]"""
    for parca in a.metin(2).split(","):
        if parca.strip().isdigit():
            depo_ekle(save, int(parca))
    cash_ekle(save, -a.tam(3))


# İlk alım teklifi (PopupFirstBuy, KYT-02). Teklif penceresi ilk açıldığında firstPurchaseTimestamp konur;
# POPUP_FIRST_PURCHASE_OFFER_TIME saniye içinde bir kez alınır. Alınınca damga 1 olur: istemcinin
# FirstOfferButton/isActive'i bunu süresi geçmiş sayar, düğme bir daha çıkmaz.
ILK_ALIM_ALINDI = 1
SAAT_PAYI = 300  # sn; istemcinin saati sunucununkinden biraz geride olabilir


@komut("set_first_purchase_timestamp")
def set_first_purchase_timestamp(save, a):
    """[] teklif penceresi ilk açılınca; [damga] geliştirici panelinden (AdminPanel/setFP)."""
    ps = save["privateState"]
    if len(a):
        ps["firstPurchaseTimestamp"] = max(0, a.tam(0))
    elif not ps.get("firstPurchaseTimestamp"):
        ps["firstPurchaseTimestamp"] = timestamp_now()


@komut("buy_first_purchase")
def buy_first_purchase(save, a):
    """[] - PopupFirstBuy/onBuy: POPUP_FIRST_PURCHASE_OFFER_COST nakit düşer, ..._REWARD verilir.

    Kaynaklar açık kasabaya, birimler depoya gider (istemci storeItem ile depoya koyar)."""
    ps = save["privateState"]
    g = globals_()
    damga = int(ps.get("firstPurchaseTimestamp", 0) or 0)
    sure = int(g.get("POPUP_FIRST_PURCHASE_OFFER_TIME", 86400))
    bedel = int(g.get("POPUP_FIRST_PURCHASE_OFFER_COST", 0))
    if damga <= ILK_ALIM_ALINDI or timestamp_now() - damga > sure + SAAT_PAYI:
        print(" ! ilk alim teklifi acik degil")
        return
    if int(save["playerInfo"].get("cash", 0)) < bedel:
        print(" ! ilk alim teklifi icin nakit yetmiyor")
        return
    cash_ekle(save, -bedel)
    odul = g.get("POPUP_FIRST_PURCHASE_OFFER_REWARD") or {}
    h = harita(save, acik_kasaba(save["playerInfo"].get("pid")))
    for tur in ("g", "c", "w", "f", "s", "m"):
        if odul.get(tur):
            kaynak_ekle(save, h, tur, odul[tur])
    if odul.get("exp"):
        h["xp"] = int(h.get("xp", 0)) + int(odul["exp"])
    for birim in odul.get("units") or []:
        depo_ekle(save, int(birim))
    ps["firstPurchaseTimestamp"] = ILK_ALIM_ALINDI


# ---------------------------------------------------------------------------
# Görevler (quest), hazineler, hayatta kalma, ağır kuşatma
# ---------------------------------------------------------------------------

@komut("end_quest")
def end_quest(save, a):
    """[json] - görev sonucu."""
    veri = a.json(0, {}) or {}
    h = harita(save, int(veri.get("map", 0)))
    kaynaklar = veri.get("resources", {})
    kaynak_ekle(save, h, "g", int(kaynaklar.get("g", 0)))
    h["xp"] = int(h.get("xp", 0)) + int(kaynaklar.get("x", 0))
    ps = save["privateState"]
    gorev_id = int(veri.get("quest_id", 0))
    if int(veri.get("win", 0)) == 1:
        ps["unlockedQuestIndex"] = max(gorev_id + 1, int(ps.get("unlockedQuestIndex", 0)))
    for esya_id, adet in (veri.get("item_rewards") or {}).items() if isinstance(veri.get("item_rewards"), dict) else []:
        depo_ekle(save, int(esya_id), int(adet))


@komut("set_quest_var")
def set_quest_var(save, a):
    """[kasaba, degisken, json]"""
    harita(save, a.tam(0)).setdefault("currentQuestVars", {})[a.metin(1)] = a.json(2)


@komut("start_survival")
def start_survival(save, a):
    """Bir can harcanır (3 saatte bir yenilenir)."""
    ps = save["privateState"]
    simdi = timestamp_now()
    canlar = [t for t in ps.get("survivalVidaTimeStamp", []) if int(t) > simdi - 3 * 3600]
    if len(canlar) < 3:
        canlar.append(simdi)
    elif int(ps.get("survivalVidasExtra", 0)) > 0:
        ps["survivalVidasExtra"] = int(ps["survivalVidasExtra"]) - 1
    ps["survivalVidaTimeStamp"] = canlar


@komut("end_survival")
def end_survival(save, a):
    """[harita_id, sure, json{esya_id: adet}]"""
    for esya_id, adet in (a.json(2, {}) or {}).items():
        depo_ekle(save, int(esya_id), int(adet))
    haritalar = save["privateState"].setdefault("survivalMaps", {})
    kayit = haritalar.setdefault(a.metin(0), {"ts": 0, "tp": 0})
    kayit["ts"] = timestamp_now()
    kayit["tp"] = max(int(kayit.get("tp", 0)), a.tam(1))


@komut("add_survival_vida_extra")
def add_survival_vida_extra(save, a):
    """[cash]"""
    cash_ekle(save, -a.tam(0))
    ps = save["privateState"]
    ps["survivalVidasExtra"] = int(ps.get("survivalVidasExtra", 0)) + 1


@komut("buy_survival_map")
def buy_survival_map(save, a):
    """[harita_id, cash]"""
    cash_ekle(save, -a.tam(1))
    save["privateState"].setdefault("survivalMaps", {})[a.metin(0)] = {"ts": 0, "tp": 0}


@komut("start_heavy_siege")
def start_heavy_siege(save, a):
    save["privateState"]["timeStampHeavySiegeAttack"] = timestamp_now()


@komut("reset_heavy_siege")
def reset_heavy_siege(save, a):
    """[cash_ile(1|0), odul_esya_id|0]"""
    ps = save["privateState"]
    ps["timeStampHeavySiegeAttack"] = 0
    ps["timeStampHeavySiegePeriod"] = timestamp_now()
    if a.tam(0):
        cash_ekle(save, -int(globals_().get("HEAVY_SIEGE_COST_CASH", 20)))
    if a.tam(1) > 0:
        depo_ekle(save, a.tam(1))


@komut("tournament_substract_resources")
def tournament_substract_resources(save, a):
    """[tur('g'|'c'), miktar, turnuva_turu, bayrak]"""
    kaynak_ekle(save, save["maps"][0], a.metin(0), -a.tam(1))


@komut("tournament_refund_resources")
def tournament_refund_resources(save, a):
    """[tur, miktar]"""
    kaynak_ekle(save, save["maps"][0], a.metin(0), a.tam(1))


# ---------------------------------------------------------------------------
# Büyü, mana, iksir, mezarlık
# ---------------------------------------------------------------------------

@komut("buy_mana_new")
def buy_mana_new(save, a):
    """[kasaba, cash_ile(1|0)]"""
    g = globals_()
    if a.tam(1):
        cash_ekle(save, -int(g.get("COST_MANA_CASH", 1)))
    else:
        kaynak_ekle(save, harita(save, a.tam(0)), "g", -int(g.get("COST_MANA_GOLD", 20000)))
    kaynak_ekle(save, None, "m", int(g.get("MANA_PER_PURCHASE", 5)))


@komut("buy_magic")
def buy_magic(save, a):
    """[buyu_id, kasaba, cash_ile(1|0)]"""
    buyu = next((m for m in get_game_config().get("magics", []) if int(m["id"]) == a.tam(0)), None)
    if buyu is None:
        return
    if a.tam(2):
        cash_ekle(save, -int(buyu.get("cash", 0)))
    else:
        kaynak_ekle(save, harita(save, a.tam(1)), "g", -int(buyu.get("gold", 0)))
    buyuler = save["privateState"].get("magics")
    if not isinstance(buyuler, dict):
        buyuler = save["privateState"]["magics"] = {}
    buyuler.setdefault(str(buyu["id"]), 0)


@komut("use_magic")
def use_magic(save, a):
    """[buyu_id]"""
    buyu = next((m for m in get_game_config().get("magics", []) if int(m["id"]) == a.tam(0)), None)
    if buyu:
        kaynak_ekle(save, None, "m", -int(buyu.get("mana", 0)))


@komut("graveyard_buy_potions")
def graveyard_buy_potions(save, a):
    iksir = globals_()["GRAVEYARD_POTIONS"]
    cash_ekle(save, -int(iksir["price"]["c"]))
    ps = save["privateState"]
    ps["potion"] = int(ps.get("potion", 0)) + int(iksir["amount"])


def mezarliga_ekle(save, birim_id):
    """Mezarlık: privateState.deadHeroes = {"birim_id": adet}."""
    mezarlik = save["privateState"].get("deadHeroes")
    if not isinstance(mezarlik, dict):
        mezarlik = save["privateState"]["deadHeroes"] = {}
    mezarlik[str(birim_id)] = int(mezarlik.get(str(birim_id), 0)) + 1


@komut("put_graveyard")
def put_graveyard(save, a):
    """[birim_id] - ölen anka kuşu mezarlığa."""
    mezarliga_ekle(save, a.tam(0))


@komut("resurrect_hero")
def resurrect_hero(save, a):
    """[birim_id, x, y, kasaba, (iksir_ile '1'|'0')]"""
    birim_id = a.tam(0)
    ps = save["privateState"]
    mezarlik = ps.get("deadHeroes")
    if isinstance(mezarlik, dict) and str(birim_id) in mezarlik:
        mezarlik[str(birim_id)] = int(mezarlik[str(birim_id)]) - 1
        if mezarlik[str(birim_id)] <= 0:
            del mezarlik[str(birim_id)]
    if a.metin(4) == "1":
        ps["potion"] = max(0, int(ps.get("potion", 0)) - 1)
    esya_ekle(harita(save, a.tam(3)), birim_id, a.tam(1), a.tam(2))


# ---------------------------------------------------------------------------
# Ejderha / canavar yuvası, binici, tapınak
# ---------------------------------------------------------------------------

def _yuva_etkinlestir(save, a, aktif_alan, sayac_alan):
    if a.metin(0) == "c":
        cash_ekle(save, -NEST_PRICE_CASH)
    elif a.metin(0) == "g":
        kaynak_ekle(save, save["maps"][0], "g", -NEST_PRICE_GOLD)
    save["privateState"][aktif_alan] = 1
    save["privateState"][sayac_alan] = -1


@komut("activate_dragon")
def activate_dragon(save, a):
    """['c'|'g']"""
    _yuva_etkinlestir(save, a, "dragonNestActive", "timeStampTakeCare")


@komut("activate_monster")
def activate_monster(save, a):
    """['c'|'g']"""
    _yuva_etkinlestir(save, a, "monsterNestActive", "timeStampTakeCareMonster")


@komut("desactivate_dragon")
def desactivate_dragon(save, a):
    ps = save["privateState"]
    ps.update(dragonNestActive=0, stepNumber=0, dragonNumber=0, timeStampTakeCare=-1)


@komut("desactivate_monster")
def desactivate_monster(save, a):
    ps = save["privateState"]
    ps.update(monsterNestActive=0, stepMonsterNumber=0, monsterNumber=0, timeStampTakeCareMonster=-1)


@komut("next_step")
def next_step(save, a):
    """[cash] - ejderha bakım adımı (cash ile hızlandırıldıysa bedeli)."""
    cash_ekle(save, -max(0, a.tam(0)))
    ps = save["privateState"]
    ps["stepNumber"] = int(ps.get("stepNumber", 0)) + 1
    ps["timeStampTakeCare"] = timestamp_now()


@komut("next_monster_step")
def next_monster_step(save, a):
    """[cash]"""
    cash_ekle(save, -max(0, a.tam(0)))
    ps = save["privateState"]
    ps["stepMonsterNumber"] = int(ps.get("stepMonsterNumber", 0)) + 1
    ps["timeStampTakeCareMonster"] = timestamp_now()


@komut("next_dragon")
def next_dragon(save, a):
    ps = save["privateState"]
    ps.update(stepNumber=0, dragonNumber=int(ps.get("dragonNumber", 0)) + 1, timeStampTakeCare=-1)


@komut("next_monster")
def next_monster(save, a):
    ps = save["privateState"]
    ps.update(stepMonsterNumber=0, monsterNumber=int(ps.get("monsterNumber", 0)) + 1,
              timeStampTakeCareMonster=-1)


@komut("buy_step_cash")
def buy_step_cash(save, a):
    """[cash]"""
    cash_ekle(save, -a.tam(0))
    save["privateState"]["timeStampTakeCare"] = -1


@komut("buy_monster_step_cash")
def buy_monster_step_cash(save, a):
    """[cash]"""
    cash_ekle(save, -a.tam(0))
    save["privateState"]["timeStampTakeCareMonster"] = -1


@komut("finish_dragon_help")
def finish_dragon_help(save, a):
    save["privateState"]["dragonSocialHelp"] = []


@komut("rider_buy_step_cash")
def rider_buy_step_cash(save, a):
    """[cash]"""
    cash_ekle(save, -a.tam(0))
    save["privateState"]["riderTimeStamp"] = -1


@komut("rider_next_step")
def rider_next_step(save, a):
    ps = save["privateState"]
    ps["riderStepNumber"] = int(ps.get("riderStepNumber", 0)) + 1
    ps["riderTimeStamp"] = timestamp_now()


@komut("rider_select")
def rider_select(save, a):
    """[binici_no] - 0 sıfırlar."""
    ps = save["privateState"]
    if a.tam(0) in (1, 2, 3):
        ps["riderNumber"] = a.tam(0)
    else:
        ps.update(riderNumber=0, riderStepNumber=0, riderTimeStamp=-1)


@komut("next_temple_step")
def next_temple_step(save, a):
    """[json adim_verisi, adim] - kaynak isteyen adımlarda kaynak düşülür."""
    veri = a.json(0, {}) or {}
    for tur, miktar in veri.items() if isinstance(veri, dict) else []:
        if tur in ("g", "w", "f", "s", "c", "m"):
            kaynak_ekle(save, save["maps"][0], tur, -int(miktar))
    ps = save["privateState"]
    ps.setdefault("templeStep", []).append(a.tam(1))
    ps["timeStampTemple"] = timestamp_now()


@komut("buy_temple_step_cash")
def buy_temple_step_cash(save, a):
    """[cash]"""
    cash_ekle(save, -a.tam(0))
    save["privateState"]["timeStampTemple"] = 0


@komut("reset_temple")
def reset_temple(save, a):
    save["privateState"].update(timeStampTemple=0, templeStep=[])


# ---------------------------------------------------------------------------
# Dart oyunu
# ---------------------------------------------------------------------------

@komut("darts_reset")
def darts_reset(save, a):
    """[tohum]"""
    simdi = timestamp_now()
    save["privateState"].update(timeStampDartsReset=simdi, timeStampDartsNewFree=simdi,
                                dartsBalloonsShot=[], dartsRandomSeed=a.tam(0),
                                dartsHasFree=True, dartsGotExtra=False)


@komut("darts_new_free")
def darts_new_free(save, a):
    save["privateState"].update(timeStampDartsNewFree=timestamp_now(), dartsHasFree=True)


@komut("darts_shoot_balloon")
def darts_shoot_balloon(save, a):
    """[balon, ucretli(1|0), ekstra(1|0)] - ödüller store_add_items ile gelir."""
    ps = save["privateState"]
    ps.setdefault("dartsBalloonsShot", []).append(a.tam(0))
    ps["dartsHasFree"] = False
    if a.tam(1):
        cash_ekle(save, -int(globals_().get("DART_COST_CASH", 20)))
    if a.tam(2):
        ps["dartsGotExtra"] = True


# ---------------------------------------------------------------------------
# Koleksiyonlar
# ---------------------------------------------------------------------------

@komut("unit_collections_completed")
def unit_collections_completed(save, a):
    """[kategori_id] - istemci +1 cash verir."""
    ps = save["privateState"]
    if a.metin(0) in [str(x) for x in ps.get("unitCollectionsCompleted", [])]:
        return
    ps.setdefault("unitCollectionsCompleted", []).append(a.metin(0))
    cash_ekle(save, 1)


@komut("add_collectable")
def add_collectable(save, a):
    """[koleksiyon, parca(1-5)] - privateState.collections[c] = [tamam, p1..p5]."""
    c, parca = a.tam(0), a.tam(1)
    if not (0 <= c < 1000 and 1 <= parca <= 5):
        return
    koleksiyonlar = save["privateState"].get("collections")
    if not isinstance(koleksiyonlar, list):
        koleksiyonlar = save["privateState"]["collections"] = []
    while len(koleksiyonlar) <= c:
        koleksiyonlar.append([0, 0, 0, 0, 0, 0])
    if not isinstance(koleksiyonlar[c], list) or len(koleksiyonlar[c]) < 6:
        koleksiyonlar[c] = [0, 0, 0, 0, 0, 0]
    koleksiyonlar[c][parca] += 1


@komut("finish_collection")
def finish_collection(save, a):
    """[koleksiyon, (cash_ile=1, cash)] - parçalarla ya da cash ile tamamlanır."""
    c = a.tam(0)
    if a.tam(1) == 1:
        cash_ekle(save, -a.tam(2))
    else:
        koleksiyonlar = save["privateState"].get("collections") or []
        if 0 <= c < len(koleksiyonlar) and isinstance(koleksiyonlar[c], list):
            for i in range(1, len(koleksiyonlar[c])):
                koleksiyonlar[c][i] = max(0, koleksiyonlar[c][i] - 1)
    listeye_ekle(save["privateState"], "collectionsCompleted", c)


# ---------------------------------------------------------------------------
# Komşular ve sosyal binalar
# ---------------------------------------------------------------------------

def _komsuya_yardim_kaydet(save, komsu_id):
    """Aynı komşuya 24 saatte bir yardım: privateState.neighborAssists["u"+pid]."""
    yardimlar = save["privateState"].get("neighborAssists")
    if not isinstance(yardimlar, dict):
        yardimlar = save["privateState"]["neighborAssists"] = {}
    yardimlar["u" + str(komsu_id)] = timestamp_now()


@komut("assist_neighbor")
def assist_neighbor(save, a):
    """[komsu_id, yardim_turu, kasaba]"""
    g = globals_()
    h = harita(save, a.tam(2))
    kaynak_ekle(save, h, "g", int(g.get("ASSIST_REWARD_GOLD", 10)))
    h["xp"] = int(h.get("xp", 0)) + int(g.get("ASSIST_REWARD_XP", 3))
    _komsuya_yardim_kaydet(save, a.metin(0))


@komut("assist_neighbor_new")
def assist_neighbor_new(save, a):
    """[komsu_id, 0, json [[x, y, id], ...]] - tıklanan her bina için ödül."""
    g = globals_()
    tiklananlar = [t for t in (a.json(2, []) or []) if isinstance(t, list) and len(t) >= 3][:5]
    h = save["maps"][0]
    kaynak_ekle(save, h, "g", int(g.get("ASSIST_REWARD_GOLD", 10)) * len(tiklananlar))
    h["xp"] = int(h.get("xp", 0)) + int(g.get("ASSIST_REWARD_XP", 3)) * len(tiklananlar)
    _komsuya_yardim_kaydet(save, a.metin(0))
    komsu_id = a.metin(0)
    komsu = neighbor_session(komsu_id)
    if komsu is None or komsu is save or not tiklananlar:
        return
    alinan = komsu["maps"][0].get("receivedAssists")
    if not isinstance(alinan, dict):
        alinan = komsu["maps"][0]["receivedAssists"] = {}
    alinan.setdefault("u" + str(save["playerInfo"]["pid"]), []).extend(tiklananlar)
    if komsu_id in all_saves_userid():
        save_session(komsu_id)


@komut("assist_receive")
def assist_receive(save, a):
    """[kasaba, bina_id] - yardım arabası: binanın üretiminin 1/4'ü + 10 XP."""
    h = harita(save, a.tam(0))
    bina = get_item_from_id(a.tam(1)) or {}
    tur = bina.get("collect_type")
    if tur in ("g", "w", "f", "s"):
        kaynak_ekle(save, h, tur, int(bina.get("collect", 0) or 0) // 4)
    h["xp"] = int(h.get("xp", 0)) + 10


@komut("clean_received_assists")
def clean_received_assists(save, a):
    """[arkadas_id, kasaba]"""
    alinan = harita(save, a.tam(1)).get("receivedAssists")
    if isinstance(alinan, dict):
        alinan.pop("u" + a.metin(0), None)
        alinan.pop(a.metin(0), None)


@komut("buy_si_help")
def buy_si_help(save, a):
    """[x, y, kasaba, id, (bedava=1)] - sosyal binaya bir işçi."""
    esya_id = a.tam(3)
    esya = esya_bul(harita(save, a.tam(2)), a.tam(0), a.tam(1), esya_id)
    if not a.tam(4):
        bilgi = next((s for s in get_game_config().get("social_items", [])
                      if int(s["id"]) == esya_id), {})
        cash_ekle(save, -int(bilgi.get("worker_cost", 0) or 0))
    if esya:
        ozellik = ozellikler(esya)
        if not isinstance(ozellik.get("si"), list):
            ozellik["si"] = []
        ozellik["si"].append(0)


@komut("finish_si")
def finish_si(save, a):
    """[x, y, kasaba, id] - sosyal bina açılır (Zirve binası yeniden kurulur)."""
    esya = esya_bul(harita(save, a.tam(2)), a.tam(0), a.tam(1), a.tam(3))
    if esya:
        ozellik = ozellikler(esya)
        if a.tam(3) == 234:
            ozellik["si"] = []
        else:
            ozellik.pop("si", None)


# ---------------------------------------------------------------------------
# Saldırı/casusluk paketleri, depo kapasitesi, PvP bölgesi, mobil depo
# ---------------------------------------------------------------------------

@komut("buy_attacks_pack")
def buy_attacks_pack(save, a):
    cash_ekle(save, -30)
    save["privateState"]["attacksPack"] = 50


@komut("buy_spyings_pack")
def buy_spyings_pack(save, a):
    cash_ekle(save, -15)
    save["privateState"]["spyingsPack"] = 50


@komut("buy_warehouse_capacity_single")
def buy_warehouse_capacity_single(save, a):
    """[kasaba]"""
    cash_ekle(save, -int(globals_().get("WAREHOUSE_CAPACITY_INCREASE_PRICE_SINGLE", 2)))
    h = harita(save, a.tam(0))
    h["warehouseAditionalCapacitySingle"] = int(h.get("warehouseAditionalCapacitySingle", 0) or 0) + 1


@komut("buy_pvp_territory")
def buy_pvp_territory(save, a):
    """[konum]"""
    cash_ekle(save, -int(globals_().get("PVP_BUY_TERRITORY_CASH", 5)))
    h = save["maps"][0]
    if not isinstance(h.get("universAttackWin"), list):
        h["universAttackWin"] = []
    h["universAttackWin"].append(a.ham(0))


def _mobil_depodan_cikar(save, esya_id):
    kutu = save["privateState"].get("iphoneBox")
    if isinstance(kutu, list):
        for i, oge in enumerate(kutu):
            if (oge[0] if isinstance(oge, list) else oge) == esya_id:
                del kutu[i]
                return


@komut("place_iphone")
def place_iphone(save, a):
    """[id, x, y, yon, kasaba] - mobil depodan haritaya."""
    _mobil_depodan_cikar(save, a.tam(0))
    esya_ekle(harita(save, a.tam(4)), a.tam(0), a.tam(1), a.tam(2), a.tam(3))


@komut("sell_iphone_item")
def sell_iphone_item(save, a):
    """[id, kasaba]"""
    _mobil_depodan_cikar(save, a.tam(0))
    satis_iadesi(save, harita(save, a.tam(1)), a.tam(0))


# ---------------------------------------------------------------------------
# Takımlar, PvP
# ---------------------------------------------------------------------------

@komut("set_attack_team")
def set_attack_team(save, a):
    """[mod('tournament'|'quest'), json takim]"""
    takimlar = save["privateState"].get("teams")
    if not isinstance(takimlar, dict):
        takimlar = save["privateState"]["teams"] = {}
    takimlar[a.metin(0)] = a.json(1, [])


@komut("modify_position_univers")
def modify_position_univers(save, a):
    """[yeni_yuva, eski_yuva] - oyuncunun dünya haritasındaki yuvası."""
    save["privateState"]["kita_konum"] = a.tam(0) % 8


@komut("attack_player")
def attack_player(save, a):
    pvp.saldiri_baslat(save, a.liste)


@komut("end_attack")
def end_attack(save, a):
    pvp.saldiri_bitir(save, a.liste)


@komut("clean_attacks")
def clean_attacks(save, a):
    """[] - savunma raporları görüldü: geçmiş kalır, yalnızca işaret kalkar."""
    for rapor in save["privateState"].get("attacksReceived") or []:
        if isinstance(rapor, dict):
            rapor.pop("viewPending", None)
