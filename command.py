import json
import math
import os
import traceback

from sessions import session, save_session, neighbor_session, all_saves_userid
from get_game_config import get_game_config, get_level_from_xp, get_name_from_item_id, get_attribute_from_mission_id, get_xp_from_level, get_attribute_from_item_id, get_item_from_subcat_functional, get_item_from_id
from constants import Constant
from engine import apply_cost, apply_collect, apply_collect_xp, timestamp_now
from bundle import SAVES_DIR

# ---------------------------------------------------------------------------
# Komut argümanlarını çözümleme yardımcıları
#
# İstemci (SWF) komut argümanlarını sayı/string karışık gönderiyor. Sıra
# sürümden sürüme değişebildiği için argümanları "değer rolüne" göre
# eşleştiriyoruz: eşya kimliği + x/y koordinatı kayıttaki eşyalarla
# karşılaştırılarak bulunur. Böylece argüman sırası değişse bile doğru
# eşya yakalanır.
# ---------------------------------------------------------------------------

KAYNAK_ADLARI = {
    "w": "w", "wood": "w", "madera": "w", "odun": "w",
    "s": "s", "stone": "s", "piedra": "s", "tas": "s",
    "f": "f", "food": "f", "comida": "f", "yemek": "f",
}


def _tam(deger):
    """Değeri int'e çevirir; olmuyorsa None döner."""
    if isinstance(deger, bool):
        return int(deger)
    if isinstance(deger, int):
        return deger
    if isinstance(deger, float):
        return int(deger)
    try:
        metin = str(deger).strip()
        if metin.lstrip("-").isdigit():
            return int(metin)
        return int(float(metin))
    except (TypeError, ValueError):
        return None


def _tamsayilar(args):
    return [n for n in (_tam(a) for a in args) if n is not None]


def _json_veri(args):
    """Argümanların içinde JSON nesnesi/dizisi varsa çözer."""
    for a in args:
        if isinstance(a, (dict, list)):
            return a
        if isinstance(a, str) and a.strip()[:1] in ("{", "["):
            try:
                return json.loads(a)
            except json.JSONDecodeError:
                continue
    return None


def _esya_bul(save, args):
    """args içindeki (id, x, y) üçlüsüne uyan eşyayı (harita, eşya) olarak döndürür."""
    sayilar = set(_tamsayilar(args))
    for town_id, harita in enumerate(save.get("maps", [])):
        for esya in harita.get("items", []):
            if len(esya) < 3:
                continue
            esya_id, x, y = _tam(esya[0]), _tam(esya[1]), _tam(esya[2])
            if esya_id is None:
                continue
            if esya_id in sayilar and x in sayilar and y in sayilar:
                return town_id, harita, esya
    return None, None, None


def _esya_konumdan_bul(save, args):
    """Yalnızca x/y koordinatlarına bakarak eşya bulur (id gönderilmediyse)."""
    sayilar = set(_tamsayilar(args))
    for town_id, harita in enumerate(save.get("maps", [])):
        adaylar = [
            e for e in harita.get("items", [])
            if len(e) >= 3 and _tam(e[1]) in sayilar and _tam(e[2]) in sayilar
        ]
        if len(adaylar) == 1:
            return town_id, harita, adaylar[0]
    return None, None, None


def _harita_sec(save, args):
    """Argümanlardaki geçerli harita numarasını bulur (yoksa 0)."""
    for n in _tamsayilar(args):
        if 0 <= n < len(save.get("maps", [])):
            return n
    return 0


def _gift_ekle(save, esya_id, adet=1):
    """Depodaki (gifts) eşya sayısını artırır."""
    esya_id = int(esya_id)
    adet = max(1, int(adet))
    gifts = save["privateState"].setdefault("gifts", [])
    if len(gifts) <= esya_id:
        gifts.extend([0] * (esya_id - len(gifts) + 1))
    gifts[esya_id] += adet


def _gift_cikar(save, esya_id, adet=1):
    """Depodan eşya düşer; yeterli yoksa False döner."""
    esya_id = int(esya_id)
    adet = max(1, int(adet))
    gifts = save["privateState"].setdefault("gifts", [])
    if esya_id >= len(gifts) or gifts[esya_id] < adet:
        return False
    gifts[esya_id] -= adet
    while gifts and gifts[-1] == 0:
        gifts.pop()
    return True


def _komutlari_gunluge_yaz(USERID, komutlar):
    """Protokol keşfi için bir paketteki komutları tek seferde dosyaya yazar.

    Her komut için dosya açıp kapatmak (özellikle yüzlerce komutluk eğitim
    paketlerinde) gereksiz yavaşlık yaratıyordu.
    """
    if not komutlar:
        return
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        simdi = timestamp_now()
        with open(os.path.join(SAVES_DIR, "komut_gunlugu.jsonl"), "a", encoding="utf-8") as f:
            for cmd, args in komutlar:
                f.write(json.dumps(
                    {"ts": simdi, "user": str(USERID), "cmd": cmd, "args": args},
                    ensure_ascii=False,
                ) + "\n")
    except OSError:
        pass  # günlük yazılamazsa oyun akışı bozulmasın


# ---------------------------------------------------------------------------
# Yükseltme
# ---------------------------------------------------------------------------

def _yukselt(save, args):
    """Bir binayı config'teki upgrades_to zincirine göre yükseltir."""
    town_id, harita, esya = _esya_bul(save, args)
    if esya is None:
        # İstemci mevcut yerine hedef binanın kimliğini göndermiş olabilir;
        # bu durumda yalnızca koordinatlardan bulmayı dene.
        town_id, harita, esya = _esya_konumdan_bul(save, args)
    if esya is None:
        print(" ! Yukseltme: esya bulunamadi, args =", args)
        return False

    eski_id = _tam(esya[0])
    eski = get_item_from_id(eski_id)
    if not eski:
        print(" ! Yukseltme: tanimsiz esya", eski_id)
        return False

    hedef_id = _tam(eski.get("upgrades_to"))
    if not hedef_id:
        print(f" ! Yukseltme: '{eski.get('name')}' yukseltilemiyor")
        return False

    hedef = get_item_from_id(hedef_id)
    if not hedef:
        print(" ! Yukseltme: hedef esya tanimsiz", hedef_id)
        return False

    # İstemci bazen fiyat çarpanı gönderiyor (BUY komutundaki gibi).
    carpan = 1.0
    for a in args:
        if isinstance(a, str):
            try:
                f = float(a)
            except ValueError:
                continue
            if 0 < f <= 10:
                carpan = f
                break

    # Yükseltme bedeli: hedef binanın maliyeti (çarpanla). Önce bakiye kontrolü.
    maliyet = int(carpan * int(hedef.get("cost") or 0))
    tur = hedef.get("cost_type")
    if tur == "c":
        bakiye = int(save["playerInfo"].get("cash", 0))
        kaynak_adi = "cash"
    else:
        kaynak_adi = {"w": "wood", "s": "stone", "f": "food", "g": "coins"}.get(tur, tur)
        bakiye = int(harita.get(kaynak_adi, 0))
    if bakiye < maliyet:
        print(f" ! Yukseltme: yetersiz {kaynak_adi} ({bakiye} < {maliyet})")
        return False

    apply_cost(save["playerInfo"], harita, hedef_id, carpan)
    harita["xp"] = int(harita.get("xp", 0)) + int(hedef.get("xp", 0) or 0)

    esya[0] = hedef_id
    if len(esya) > 4:
        esya[4] = timestamp_now()  # üretim sayacı sıfırlanır
    if len(esya) > 5:
        esya[5] = 0

    print(f"Yukseltildi: {eski.get('name')} -> {hedef.get('name')}")
    return True


# ---------------------------------------------------------------------------
# Pazar / kaynak takası
# ---------------------------------------------------------------------------

def _pazar(save, args):
    """Kaynak alım-satımı.

    Fiyat sunucuda hesaplanır: resourcesTraded sayacı arttıkça alım fiyatı
    yükselir, satım fiyatı düşer. Sayaç MARKET_PERIOD_HOURS saatte sıfırlanır.
    """
    globals_ = get_game_config().get("globals", {})
    temel = globals_.get("MARKET_BASE_COSTS", {})
    artis = float(globals_.get("MARKET_INCREMENT", 0.02))
    satis_orani = float(globals_.get("MARKET_SELL_PERCENTAGE", 0.75))
    max_artis = int(globals_.get("MARKET_MAX_INCREMENTS", 200))
    max_azalis = int(globals_.get("MARKET_MAX_DECREMENTS", 25))
    periyot = int(globals_.get("MARKET_PERIOD_HOURS", 20)) * 3600

    veri = _json_veri(args)
    kaynak = yon = None
    adet = None
    town_id = 0

    if isinstance(veri, dict):
        kaynak = str(veri.get("resource") or veri.get("res") or veri.get("type") or "").lower()
        yon = str(veri.get("action") or veri.get("direction") or veri.get("mode") or "").lower()
        adet = _tam(veri.get("amount") or veri.get("quantity") or veri.get("qty"))
        town_id = _tam(veri.get("map") or veri.get("town") or veri.get("town_id")) or 0
    else:
        for a in args:
            anahtar = KAYNAK_ADLARI.get(str(a).strip().lower())
            if anahtar is not None:
                kaynak = anahtar
        for a in args:
            metin = str(a).strip().lower()
            if metin in ("buy", "comprar", "satin_al"):
                yon = "buy"
            elif metin in ("sell", "vender", "sat"):
                yon = "sell"
        sayilar = [n for n in _tamsayilar(args) if n > 0]
        adet = sayilar[0] if sayilar else None
        if len(args) > 2:
            town_id = _tam(args[2]) or 0

    kaynak = KAYNAK_ADLARI.get(kaynak, kaynak)
    if kaynak not in ("w", "s", "f"):
        print(" ! Pazar: gecersiz kaynak", args)
        return False
    if yon is None:
        yon = "buy"  # yön belirtilmediyse alım varsay (log'da görünür)
        print(" ! Pazar: yon belirtilmedi, alim varsayildi")
    if not adet or adet <= 0:
        print(" ! Pazar: gecersiz miktar", args)
        return False

    harita = save["maps"][town_id] if 0 <= town_id < len(save["maps"]) else save["maps"][0]
    ps = save["privateState"]
    simdi = timestamp_now()

    # Config'teki kısa kaynak anahtarı (w/s/f) ile kayıttaki alan adı farklı.
    alan = {"w": "wood", "s": "stone", "f": "food"}[kaynak]

    # Dönem dolduysa sayaçları sıfırla
    if simdi - int(ps.get("marketTimestamp", 0)) > periyot:
        harita["resourcesTraded"] = {}
        ps["marketTimestamp"] = simdi
    traded = harita.setdefault("resourcesTraded", {}) or {}
    harita["resourcesTraded"] = traded
    onceki = int(traded.get(kaynak, 0))

    if yon == "buy":
        birim = temel[kaynak] * (1 + artis * max(0, min(onceki, max_artis)))
        toplam = int(math.ceil(birim * adet))
        if harita["coins"] < toplam:
            print(f" ! Pazar: yetersiz altin ({harita['coins']} < {toplam})")
            return False
        harita["coins"] -= toplam
        harita[alan] += adet
        traded[kaynak] = max(-max_azalis, min(max_artis, onceki + adet))
        print(f"Pazar: {adet} {kaynak} alindi, {toplam} altin odendi")
    else:
        birim = temel[kaynak] * satis_orani * (1 - artis * max(0, min(-onceki, max_azalis)))
        toplam = int(math.floor(birim * adet))
        if harita[alan] < adet:
            print(f" ! Pazar: yetersiz kaynak ({harita[alan]} < {adet})")
            return False
        harita[alan] -= adet
        harita["coins"] += toplam
        traded[kaynak] = max(-max_azalis, min(max_artis, onceki - adet))
        print(f"Pazar: {adet} {kaynak} satildi, {toplam} altin alindi")
    return True


# ---------------------------------------------------------------------------
# PvP (oyuncuya saldırı)
# ---------------------------------------------------------------------------

KAYNAK_ALANLARI = {"g": "coins", "w": "wood", "s": "stone", "f": "food"}


def _liste_al(kap, anahtar):
    """Kayıtta liste alanı yoksa/None ise boş liste oluşturup döndürür."""
    deger = kap.get(anahtar)
    if not isinstance(deger, list):
        deger = []
        kap[anahtar] = deger
    return deger


def _oyuncu_ozeti(kayit):
    pi = kayit.get("playerInfo", {})
    harita = (kayit.get("maps") or [{}])[0]
    return {
        "name": pi.get("name") or "Oyuncu",
        "user_id": str(pi.get("pid") or ""),
        "world_id": pi.get("world_id", 0),
        "level": harita.get("level", 1),
        "pic": pi.get("pic", ""),
    }


def _saldiri_baslat(saldiran, args):
    """attack_player: hedefi doğrular ve saldırıyı başlatır.

    Asıl sonuç `end_attack` geldiğinde uygulanır; burada yalnızca hedefin
    gerçekten var olduğunu kontrol ediyoruz.
    """
    hedef = str(args[0]) if args else ""
    if not hedef:
        print(" ! Saldiri: hedef yok, args =", args)
        return False
    kurban = neighbor_session(hedef)
    if kurban is None:
        print(" ! Saldiri: hedef bulunamadi:", hedef)
        return False
    print(f"Saldiri basladi: {_oyuncu_ozeti(kurban)['name']} ({hedef})")
    return True


def _saldiri_bitir(saldiran, args):
    """end_attack: istemcinin gönderdiği savaş sonucunu iki tarafa uygular.

    Beklenen JSON: victim_id, map, win, duration, townhall_gold,
    resources {x,g...}, resources_victim {g,w,s,f}, attacker_units,
    victim_units, voluntary_end.
    """
    veri = _json_veri(args)
    if not isinstance(veri, dict):
        print(" ! end_attack: JSON veri yok, args =", args)
        return False

    kurban_id = str(veri.get("victim_id") or veri.get("defender_id") or veri.get("rival_id") or "")
    if not kurban_id:
        print(" ! end_attack: victim_id yok:", veri)
        return False

    kurban = neighbor_session(kurban_id)
    if kurban is None:
        print(" ! end_attack: kurban kaydi bulunamadi:", kurban_id)
        return False

    kendi_id = str(saldiran.get("playerInfo", {}).get("pid", ""))
    if kurban_id == kendi_id:
        print(" ! end_attack: kendine saldiri yok sayildi")
        return False

    # Saldırı hakkı: son 6 saatte 3'ten fazla saldırı varsa uyar (engellemez).
    simdi_once = timestamp_now()
    son_saldirilar = [
        a for a in _liste_al(saldiran.setdefault("privateState", {}), "attacksSent")
        if _tam(a.get("time")) and simdi_once - _tam(a.get("time")) < 6 * 3600
    ]
    if len(son_saldirilar) >= 3:
        print(" ! Saldiri hakki dolmus görünüyor (son 6 saatte 3+), yine de uygulaniyor")

    town_id = _tam(veri.get("map")) or 0
    if not (0 <= town_id < len(saldiran.get("maps", []))):
        town_id = 0
    harita = saldiran["maps"][town_id]

    # Saldıranın kazancı (istemci hesaplıyor; sunucu yalnızca uygular)
    kazanc = veri.get("resources") or {}
    if isinstance(kazanc, dict):
        for anahtar, deger in kazanc.items():
            miktar = _tam(deger) or 0
            if miktar == 0:
                continue
            if anahtar == "x":
                harita["xp"] = int(harita.get("xp", 0)) + miktar
            elif anahtar in KAYNAK_ALANLARI:
                alan = KAYNAK_ALANLARI[anahtar]
                harita[alan] = int(harita.get(alan, 0)) + miktar

    # Kurbandan eksilen kaynaklar (mevcut kaynağın üstüne çıkmasın)
    kurban_harita = kurban["maps"][0]
    kayip = veri.get("resources_victim") or {}
    if isinstance(kayip, dict):
        for anahtar, deger in kayip.items():
            miktar = _tam(deger) or 0
            if miktar <= 0 or anahtar not in KAYNAK_ALANLARI:
                continue
            alan = KAYNAK_ALANLARI[anahtar]
            gercek = min(miktar, int(kurban_harita.get(alan, 0)))
            kurban_harita[alan] = int(kurban_harita.get(alan, 0)) - gercek

    simdi = timestamp_now()
    saldiran_ps = saldiran.setdefault("privateState", {})
    kurban_ps = kurban.setdefault("privateState", {})

    _liste_al(saldiran_ps, "attacksSent").append({
        "victim_id": kurban_id,
        "time": str(simdi),
    })

    rapor = dict(veri)
    rapor["oponent"] = _oyuncu_ozeti(saldiran)
    rapor["time"] = simdi
    _liste_al(kurban_ps, "attacksReceived").append({
        "time": simdi,
        "attacker_id": str(saldiran.get("playerInfo", {}).get("pid", "")),
        "description": rapor,
    })

    # Kurbanın kaydı da diske yazılsın (komut sonunda saldıran yazılıyor).
    # Statik komşular (Arthur, AcidCaos...) kayıtlı oyuncu değil; onlar için yazma yok.
    if kurban_id in all_saves_userid():
        save_session(kurban_id)

    sonuc = "kazandi" if _tam(veri.get("win")) == 1 else "kaybetti"
    print(f"Saldiri bitti: {_oyuncu_ozeti(kurban)['name']} - {sonuc}")
    return True


def _depoya_ekle(save, veri):
    """Depoya (gifts) eşya ekler; JSON sözlüğü/listesi veya çift listesi kabul eder."""
    if isinstance(veri, dict):
        if "id" in veri or "item" in veri:  # tek eşya kaydı
            esya_id = _tam(veri.get("id") or veri.get("item"))
            if esya_id is not None:
                _gift_ekle(save, esya_id, _tam(veri.get("count") or veri.get("amount")) or 1)
            return
        for esya_id, adet in veri.items():  # {esya_id: adet}
            n = _tam(esya_id)
            if n is not None:
                _gift_ekle(save, n, _tam(adet) or 1)
    elif isinstance(veri, list):
        for oge in veri:
            if isinstance(oge, dict):
                esya_id = _tam(oge.get("id") or oge.get("item"))
                if esya_id is not None:
                    _gift_ekle(save, esya_id, _tam(oge.get("count") or oge.get("amount")) or 1)
            elif isinstance(oge, (list, tuple)) and len(oge) >= 2:
                curuk = _tam(oge[0])
                if curuk is not None:
                    _gift_ekle(save, curuk, _tam(oge[1]) or 1)
            else:
                n = _tam(oge)
                if n is not None:
                    _gift_ekle(save, n, 1)


def get_strategy_type(id):
    if id == 8:
        return "Defensive"
    if id == 9:
        return "Mid Defensive"
    if id == 7:
        return "Mid Aggressive"
    if id == 10:
        return "Aggressive"
    return "Unknown Strategy"

def command(USERID, data):
    timestamp = data["ts"]
    first_number = data["first_number"]
    accessToken = data["accessToken"]
    tries = data["tries"]
    publishActions = data["publishActions"]
    commands = data["commands"]

    gunluk = []
    for i, comm in enumerate(commands):
        cmd = comm.get("cmd")
        args = comm.get("args", [])
        gunluk.append((cmd, args))
        try:
            do_command(USERID, cmd, args)
        except Exception:
            # Bozuk tek bir komut, aynı paketteki diğer komutları ve kaydı
            # düşürmesin. Hata ayrıntısı konsola yazılır.
            print(f" ! KOMUT HATASI: {cmd} args={args}")
            traceback.print_exc()

    _komutlari_gunluge_yaz(USERID, gunluk)
    save_session(USERID) # Save session

def do_command(USERID, cmd, args):
    save = session(USERID)
    print (" [+] COMMAND: ", cmd, "(", args, ") -> ", sep='', end='')

    if cmd == Constant.CMD_GAME_STATUS:
        print(" ".join(args))

    elif cmd == Constant.CMD_BUY:
        id = args[0]
        x = args[1]
        y = args[2]
        frame = args[3] # TODO ??
        town_id = args[4]
        bool_dont_modify_resources = bool(args[5]) # 1 if the game "buys" for you, so does not substract whatever the item cost is.
        price_multiplier = args[6]
        type = args[7]
        print("Add", str(get_name_from_item_id(id)), "at", f"({x},{y})")
        collected_at_timestamp = timestamp_now()
        level = 0 # TODO 
        orientation = 0
        map = save["maps"][town_id]
        if not bool_dont_modify_resources:
            apply_cost(save["playerInfo"], map, id, price_multiplier)
            xp = int(get_attribute_from_item_id(id, "xp"))
            map["xp"] = map["xp"] + xp
        map["items"] += [[id, x, y, orientation, collected_at_timestamp, level]]
    
    elif cmd == Constant.CMD_COMPLETE_TUTORIAL:
        tutorial_step = args[0]
        print("Tutorial step", tutorial_step, "reached.")
        if tutorial_step >= 31: # 31 is Dragon choosing. After that, you have some freedom. There's at least until step 45.
            print("Tutorial COMPLETED!")
            save["playerInfo"]["completed_tutorial"] = 1
            save["privateState"]["dragonNestActive"] = 1 
    
    elif cmd == Constant.CMD_MOVE:
        ix = args[0]
        iy = args[1]
        id = args[2]
        newx = args[3]
        newy = args[4]
        frame = args[5]
        town_id = args[6]
        reason = args[7] # "Unitat", "moveTo", "colisio", "MouseUsed"
        print("Move", str(get_name_from_item_id(id)), "from", f"({ix},{iy})", "to", f"({newx},{newy})")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == id and item[1] == ix and item[2] == iy:
                item[1] = newx
                item[2] = newy
                break
    
    elif cmd == Constant.CMD_COLLECT:
        # Boş/eksik paketler (istemci bazen [] gönderiyor) sunucuyu düşürmesin.
        if len(args) < 7:
            print(" ! Collect: eksik argüman, atlandı:", args)
            return
        x = _tam(args[0])
        y = _tam(args[1])
        town_id = _tam(args[2])
        id = _tam(args[3])
        resource_multiplier = _tam(args[5]) or 1
        cash_to_substract = _tam(args[6]) or 0
        if id is None or town_id is None or not (0 <= town_id < len(save["maps"])):
            print(" ! Collect: geçersiz argüman, atlandı:", args)
            return
        print("Collect", str(get_name_from_item_id(id)))
        map = save["maps"][town_id]
        apply_collect(save["playerInfo"], map, id, resource_multiplier)
        save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - cash_to_substract, 0)
        # Üretim sayacını sıfırla: aksi halde kayıt yeniden yüklenince bina
        # anında yine "toplanabilir" görünüyordu.
        for esya in map["items"]:
            if _tam(esya[0]) == id and _tam(esya[1]) == x and _tam(esya[2]) == y:
                if len(esya) > 4:
                    esya[4] = timestamp_now()
                break
    
    elif cmd == Constant.CMD_SELL:
        x = args[0]
        y = args[1]
        id = args[2]
        town_id = args[3]
        bool_dont_modify_resources = args[4]
        reason = args[5]
        print("Remove", str(get_name_from_item_id(id)), "from", f"({x},{y}). Reason: {reason}")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == id and item[1] == x and item[2] == y:
                map["items"].remove(item)
                break
        if not bool_dont_modify_resources:
            price_multiplier = -0.05
            if get_attribute_from_item_id(id, "cost_type") != "c":
                apply_cost(save["playerInfo"], save["maps"][town_id], id, price_multiplier)
        if reason == 'KILL':
            pass # TODO : add to graveyard
    
    elif cmd == Constant.CMD_KILL:
        x = args[0]
        y = args[1]
        id = args[2]
        town_id = args[3]
        type = args[4]
        print("Kill", str(get_name_from_item_id(id)), "from", f"({x},{y}).")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == id and item[1] == x and item[2] == y:
                apply_collect_xp(map, id)
                map["items"].remove(item)
                break
    
    elif cmd == Constant.CMD_COMPLETE_MISSION:
        mission_id = _tam(args[0]) if args else None
        skipped_with_cash = bool(args[1]) if len(args) > 1 else False
        if mission_id is None:
            print(" ! Gecersiz gorev kimligi:", args)
            return
        print("Complete mission", mission_id, ":", str(get_attribute_from_mission_id(mission_id, "title")))
        if skipped_with_cash:
            cash_to_substract = 0 # TODO
            save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - cash_to_substract, 0)
        tamamlanan = save["privateState"].setdefault("completedMissions", [])
        if mission_id not in tamamlanan:  # aynı görev iki kez yazılmasın
            tamamlanan.append(mission_id)

    elif cmd == Constant.CMD_REWARD_MISSION:
        town_id = _tam(args[0]) if args else 0
        mission_id = _tam(args[1]) if len(args) > 1 else None
        if mission_id is None:
            print(" ! Gecersiz gorev kimligi:", args)
            return
        print("Reward mission", mission_id, ":", str(get_attribute_from_mission_id(mission_id, "title")))
        odul_verilen = save["privateState"].setdefault("rewardedMissions", [])
        if mission_id in odul_verilen:
            print(" ! Gorev odulu zaten alinmis:", mission_id)
            return
        reward = int(get_attribute_from_mission_id(mission_id, "reward")) # gold
        save["maps"][town_id]["coins"] += reward
        odul_verilen.append(mission_id)
    
    elif cmd == Constant.CMD_PUSH_UNIT:
        unit_x = args[0]
        unit_y = args[1]
        unit_id = args[2]
        b_x = args[3]
        b_y = args[4]
        town_id = args[5]
        print("Push", str(get_name_from_item_id(unit_id)), "to", f"({b_x},{b_y}).")
        map = save["maps"][town_id]
        # Unit into building
        for item in map["items"]:
            if item[1] == b_x and item[2] == b_y:
                if len(item) < 7:
                    item += [[]]
                item[6] += [unit_id]
                break
        # Remove unit
        for item in map["items"]:
            if item[0] == unit_id and item[1] == unit_x and item[2] == unit_y:
                map["items"].remove(item)
                break
    
    elif cmd == Constant.CMD_POP_UNIT:
        b_x = args[0]
        b_y = args[1]
        town_id = args[2]
        unit_id = args[3]
        place_popped_unit = len(args) > 4
        if place_popped_unit:
            unit_x = args[4]
            unit_y = args[5]
            unit_frame = args[6] # unknown use
        print("Pop", str(get_name_from_item_id(unit_id)), "from", f"({b_x},{b_y}).")
        map = save["maps"][town_id]
        # Remove unit from building
        for item in map["items"]:
            if item[1] == b_x and item[2] == b_y:
                if len(item) < 7:
                    break
                item[6].remove(unit_id)
                break
        if place_popped_unit:
            # Spawn unit outside
            collected_at_timestamp = timestamp_now()
            level = 0 # TODO 
            orientation = 0
            map["items"] += [[unit_id, unit_x, unit_y, orientation, collected_at_timestamp, level]]
    
    elif cmd == Constant.CMD_RT_LEVEL_UP:
        yeni_seviye = _tam(args[0]) if args else None
        seviyeler = get_game_config()["levels"]
        if yeni_seviye is None:
            print(" ! Level up: gecersiz arguman", args)
            return
        yeni_seviye = max(0, min(yeni_seviye, len(seviyeler) - 1))
        print("Level Up!:", yeni_seviye)
        harita = save["maps"][0]
        harita["level"] = yeni_seviye
        mevcut_xp = int(harita.get("xp", 0))
        asgari_xp = int(seviyeler[yeni_seviye]["exp_required"])
        ust_xp = int(seviyeler[-1]["exp_required"])
        harita["xp"] = max(asgari_xp, min(mevcut_xp, ust_xp))

    elif cmd == Constant.CMD_RT_PUBLISH_SCORE:
        yeni_xp = _tam(args[0]) if args else None
        seviyeler = get_game_config()["levels"]
        ust_xp = int(seviyeler[-1]["exp_required"])
        # İstemci bazen anlamsız büyük bir değer gönderiyor (oyunu kilitleyen
        # 2 milyarlık XP hatası). Makul aralık dışındaysa yok say.
        if yeni_xp is None or yeni_xp < 0 or yeni_xp > ust_xp:
            print(f" ! publish_score: mantiksiz XP ({yeni_xp}), yok sayildi")
            return
        print("xp set to", yeni_xp)
        harita = save["maps"][0]
        harita["xp"] = yeni_xp
        harita["level"] = get_level_from_xp(yeni_xp)

    elif cmd == Constant.CMD_EXPAND:
        land_id = args[0]
        resource = args[1]
        town_id = int(args[2])
        print("Expansion", land_id, "purchased")
        map = save["maps"][town_id]
        if land_id in map["expansions"]:
            return
        # Substract resources
        expansion_prices = get_game_config()["expansion_prices"]
        exp = expansion_prices[len(map["expansions"]) - 1]
        if resource == "gold":
            to_substract = exp["coins"]
            save["maps"][town_id]["coins"] = max(save["maps"][town_id]["coins"] - to_substract, 0)
        elif resource == "cash":
            to_substract = exp["cash"]
            save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - to_substract, 0)
        # Add expansion
        map["expansions"].append(land_id)

    elif cmd == Constant.CMD_NAME_MAP:
        town_id =int(args[0])
        new_name = args[1]
        print(f"Map name changed to '{new_name}'.")
        save["playerInfo"]["map_names"][town_id] = new_name

    elif cmd == Constant.CMD_EXCHANGE_CASH:
        town_id = args[0]
        print("Exchange cash -> coins.")
        save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - 5, 0)#maybe make function for editing resources
        save["maps"][town_id]["coins"] += 2500

    elif cmd == Constant.CMD_STORE_ITEM:
        x = args[0]
        y = args[1]
        town_id = int(args[2])
        item_id = args[3]
        print("Store", str(get_name_from_item_id(item_id)), "from", f"({x},{y})")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == item_id and item[1] == x and item[2] == y:
                map["items"].remove(item)
                break
        length = len(save["privateState"]["gifts"])
        if length <= item_id:
            for i in range(item_id - length + 1):
                save["privateState"]["gifts"].append(0)
        save["privateState"]["gifts"][item_id] += 1

    elif cmd == Constant.CMD_PLACE_GIFT:
        item_id = args[0]
        x = args[1]
        y = args[2]
        town_id = args[3]#unsure, both 3 and 4 seem to stay 0
        args[4]#unknown yet
        print("Add", str(get_name_from_item_id(item_id)), "at", f"({x},{y})")
        items = save["maps"][town_id]["items"]
        orientation = 0#TODO
        collected_at_timestamp = timestamp_now()
        level = 0
        items += [[item_id, x, y, orientation, collected_at_timestamp, level]]#maybe make function for adding items
        save["privateState"]["gifts"][item_id] -= 1
        if save["privateState"]["gifts"][item_id] == 0: #removes excess zeros at end if necessary
            while(save["privateState"]["gifts"][-1] == 0):
                save["privateState"]["gifts"].pop()  

    elif cmd == Constant.CMD_SELL_GIFT:
        item_id = args[0]
        town_id = args[1]
        print("Gift", str(get_name_from_item_id(item_id)), "sold on town:",town_id)
        gifts = save["privateState"]["gifts"]
        gifts[item_id] -= 1
        if gifts[item_id] == 0: #removes excess zeros at end if necessary
            while(len(gifts) != 0 and gifts[-1] == 0):
                gifts.pop()
        price_multiplier = -0.05
        if get_attribute_from_item_id(item_id, "cost_type") != "c":
            apply_cost(save["playerInfo"], save["maps"][town_id], item_id, price_multiplier)
    
    elif cmd == Constant.CMD_ACTIVATE_DRAGON:
        currency = args[0]
        print("Dragon nest activated.")
        if currency == 'c':
            save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - 50), 0)
        elif currency == 'g':
            map = save["maps"]
            map[0]["coins"] = max(int(map[0]["coins"] - 100000), 0)
        save["privateState"]["dragonNestActive"] = 1
        save["privateState"]["timeStampTakeCare"] = -1 # remove timer if any
    
    elif cmd == Constant.CMD_DESACTIVATE_DRAGON:
        print("Dragon nest deactivated.")
        pState = save["privateState"]
        pState["dragonNestActive"] = 0
        # reset step and dragon numbers
        pState["stepNumber"] = 0
        pState["dragonNumber"] = 0
        pState["timeStampTakeCare"] = -1 # remove timer if any

    elif cmd == Constant.CMD_NEXT_DRAGON_STEP:
        unknown = args[0]
        print("Dragon step increased.")
        pState = save["privateState"]
        pState["stepNumber"] += 1
        pState["timeStampTakeCare"] = timestamp_now()

    elif cmd == Constant.CMD_NEXT_DRAGON:
        print("Dragon step reset and dragonNumber increased.")
        pState = save["privateState"]
        pState["stepNumber"] = 0
        pState["dragonNumber"] += 1
        pState["timeStampTakeCare"] = -1 # remove timer

    elif cmd == Constant.CMD_DRAGON_BUY_STEP_CASH:
        price = args[0]
        print("Buy dragon step with cash.")
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price), 0)
        save["privateState"]["timeStampTakeCare"] = -1 # remove timer

    elif cmd == Constant.CMD_RIDER_BUY_STEP_CASH:
        price = args[0]
        print("Buy rider step with cash.")
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price), 0)
        save["privateState"]["riderTimeStamp"] = -1 # remove timer

    elif cmd == Constant.CMD_NEXT_RIDER_STEP:
        print("Rider step increased.")
        pState = save["privateState"]
        pState["riderStepNumber"] += 1
        pState["riderTimeStamp"] = timestamp_now()
    
    elif cmd == Constant.CMD_SELECT_RIDER:
        number = int(args[0])
        pState = save["privateState"]
        if number == 1 or number == 2 or number == 3:
            pState["riderNumber"] = number
            print("Rider", number, "Selected.")
        else:
            pState["riderNumber"] = 0
            pState["riderStepNumber"] = 0
            pState["riderTimeStamp"] = -1 # remove timer
            print("Rider reset.")
    
    elif cmd == Constant.CMD_ORIENT:
        x = args[0]
        y = args[1]
        new_orientation = args[2]
        town_id = args[3]
        print("Item at", f"({x},{y})", "changed to orientation", new_orientation)
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[1] == x and item[2] == y:
                item[3] = new_orientation
                break
    
    elif cmd == Constant.CMD_MONSTER_BUY_STEP_CASH:
        price = args[0]
        print("Buy monster step with cash.")
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price), 0)
        save["privateState"]["timeStampTakeCareMonster"] = -1 # remove timer
    
    elif cmd == Constant.CMD_ACTIVATE_MONSTER:
        currency = args[0]
        print("Monster nest activated.")
        if currency == 'c':
            save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - 50), 0)
        elif currency == 'g':
            map = save["maps"]
            map[0]["coins"] = max(int(map[0]["coins"] - 100000), 0)
        save["privateState"]["monsterNestActive"] = 1
        save["privateState"]["timeStampTakeCareMonster"] = -1 # remove timer if any
    
    elif cmd == Constant.CMD_DESACTIVATE_MONSTER: # cmd called too late
        print("Monster nest deactivated.")
        pState = save["privateState"]
        pState["monsterNestActive"] = 0
        pState["stepMonsterNumber"] = 0
        pState["MonsterNumber"] = 0
        pState["timeStampTakeCareMonster"] = -1 # remove timer if any


    elif cmd == Constant.CMD_NEXT_MONSTER_STEP:
        print("Monster Step increased.")
        pState = save["privateState"]
        pState["stepMonsterNumber"] += 1
        pState["timeStampTakeCareMonster"] = timestamp_now()

    elif cmd == Constant.CMD_NEXT_MONSTER:
        print("Monster Step reset and Monster Number increased.")
        pState = save["privateState"]
        pState["stepMonsterNumber"] = 0
        pState["monsterNumber"] += 1
        pState["timeStampTakeCareMonster"] = -1 # remove timer

    elif cmd == Constant.CMD_WIN_BONUS:
        coins = args[0]
        town_id = args[1]
        hero = args[2]
        claimId = args[3]
        cash = args[4]

        print("Claiming Win Bonus")
        map = save["maps"][town_id]

        if cash != 0:
            save["playerInfo"]["cash"] = save["playerInfo"]["cash"] + cash
            print("Added " + str(cash) + " Cash to players balance")

        if coins != 0:
            map["coins"] = map["coins"] + coins
            print("Added " + str(coins) + " Gold to players balance")

        if hero != 0:
            length = len(save["privateState"]["gifts"])
            if length <= hero:
                for i in range(hero - length + 1):
                    save["privateState"]["gifts"].append(0)
            save["privateState"]["gifts"][hero] += 1
            print("Added Hero ID=" + str(hero))

        pState = save["privateState"]
        pState["bonusNextId"] = claimId + 1
        pState["timestampLastBonus"] = timestamp_now()

    elif cmd == Constant.CMD_ADMIN_ADD_ANIMAL:
        subcatFunc = str(args[0])
        toBeAdded = int(args[1])
        print("Added", toBeAdded, get_item_from_subcat_functional(subcatFunc)["name"])

        # TODO
        oAnimals: dict = save["privateState"]["arrayAnimals"]
        oAnimals[subcatFunc] = toBeAdded + (oAnimals[subcatFunc] if subcatFunc in oAnimals else 0)
    
    elif cmd == Constant.CMD_GRAVEYARD_BUY_POTIONS:
        # no args
        print("Graveyard buy potion")
        # info from config
        graveyard_potions = get_game_config()["globals"]["GRAVEYARD_POTIONS"]
        amount = graveyard_potions["amount"]
        price_cash = graveyard_potions["price"]["c"]
        # pay
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price_cash), 0)
        # add potion
        save["privateState"]["potion"] += amount

    elif cmd == Constant.CMD_RESURRECT_HERO:
        unit_id = _tam(args[0]) if args else None
        x = _tam(args[1]) if len(args) > 1 else 0
        y = _tam(args[2]) if len(args) > 2 else 0
        town_id = _tam(args[3]) if len(args) > 3 else 0
        if unit_id is None or town_id is None or town_id >= len(save["maps"]):
            print(" ! Gecersiz diriltme komutu:", args)
            return
        bool_used_potion = len(args) > 4 and str(args[4]) == '1'
        print("Resurrect", str(get_name_from_item_id(unit_id)), "from graveyard")
        # Ödeme
        if bool_used_potion:
            save["privateState"]["potion"] = max(int(save["privateState"]["potion"]) - 1, 0)
        # Birimi haritaya koy (önceki sürümde 'map' ve 'id' tanımsızdı)
        harita = save["maps"][town_id]
        harita["items"].append([unit_id, x, y, 0, timestamp_now(), 0])

    elif cmd == Constant.CMD_BUY_SUPER_OFFER_PACK:
        town_id = args[0]
        unknown2 = args[1] # this is probably the super offer pack ID?
        items = args[2]
        cash_used = args[3]
        
        map = save["maps"][town_id]

        item_array = items.split(',')
        for item in item_array:
            item_id = int(item)
            length = len(save["privateState"]["gifts"])
            if length <= item_id:
                for i in range(item_id - length + 1):
                    save["privateState"]["gifts"].append(0)
            save["privateState"]["gifts"][item_id] += 1

        save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - cash_used, 0)#maybe make function for editing resources
        print(f"Used {cash_used} cash to buy super offer pack!")

    elif cmd == Constant.CMD_SET_STRATEGY:
        strategy_type = args[0]
        type_name = get_strategy_type(strategy_type)
        save["privateState"]["strategy"] = strategy_type
        print(f"Set defense strategy type to {type_name}")

    elif cmd == Constant.CMD_START_QUEST:
        quest_id = args[0]
        town_id = args[1]
        print(f"Start quest {quest_id}")

    elif cmd == Constant.CMD_END_QUEST:
        data = json.loads(args[0])
        town_id = data["map"]
        gold_gained = data["resources"]["g"]
        xp_gained = data["resources"]["x"]
        units = data["units"]
        win = data["win"] == 1
        duration_sec = data["duration"]
        voluntary_end = data["voluntary_end"] == 1
        quest_id = int(data["quest_id"])
        item_rewards = data["item_rewards"] if "item_rewards" in data else None
        activators_left = data["activators_left"] if "activators_left" in data else None
        difficulty = data["difficulty"]

        # Resources
        save["maps"][town_id]["coins"] += int(gold_gained)
        save["maps"][town_id]["xp"] += int(xp_gained)

        # Update quests data
        save["privateState"]["unlockedQuestIndex"] = max(quest_id + 1, save["privateState"]["unlockedQuestIndex"], 0)
        # save["privateState"]["questsRank"] = TODO 
        # save["maps"]["questTimes"] [quest_id] = TODO min (... , duration_sec)
        # save["maps"]["lastQuestTimes"] [quest_id] = TODO min (... , duration_sec)

        print(f"Ended quest {quest_id}.")

    elif cmd == Constant.CMD_UPGRADE:
        _yukselt(save, args)

    elif cmd == Constant.CMD_TRADE_RESOURCE:
        _pazar(save, args)

    elif cmd == Constant.CMD_SET_RESOURCES_TRADED:
        veri = _json_veri(args)
        if veri is None and len(args) >= 2:
            veri = {args[0]: _tam(args[1])}
        if isinstance(veri, dict):
            harita = save["maps"][_harita_sec(save, args)]
            harita["resourcesTraded"] = {
                str(k): int(v) for k, v in veri.items() if _tam(v) is not None
            }
            print("Pazar sayaclari guncellendi:", harita["resourcesTraded"])
        else:
            print(" ! SET_RESOURCES_TRADED: veri cozulemedi", args)

    elif cmd in (Constant.CMD_ADD_ITEMS_TO_STORE, Constant.CMD_STORE_ADD_ITEMS):
        veri = _json_veri(args)
        if veri is not None:
            _depoya_ekle(save, veri)
        else:
            sayilar = _tamsayilar(args)
            if len(sayilar) >= 2:
                _gift_ekle(save, sayilar[0], sayilar[1])
            elif sayilar:
                _gift_ekle(save, sayilar[0], 1)
            else:
                print(" ! Depo: gecersiz args", args)
                return
        print("Depoya esya eklendi.")

    elif cmd == Constant.CMD_PLACE_STORED_ITEM:
        veri = _json_veri(args)
        if isinstance(veri, dict):
            esya_id = _tam(veri.get("id") or veri.get("item"))
            x = _tam(veri.get("x")) or 0
            y = _tam(veri.get("y")) or 0
            town_id = _tam(veri.get("map") or veri.get("town")) or 0
        else:
            sayilar = _tamsayilar(args)
            esya_id = sayilar[0] if sayilar else None
            x = sayilar[1] if len(sayilar) > 1 else 0
            y = sayilar[2] if len(sayilar) > 2 else 0
            town_id = sayilar[3] if len(sayilar) > 3 else 0
        if esya_id is None or not _gift_cikar(save, esya_id):
            print(" ! Depoda esya yok:", args)
            return
        save["maps"][town_id]["items"].append([esya_id, x, y, 0, timestamp_now(), 0])
        print("Depodan yerlestirildi:", esya_id, (x, y))

    elif cmd == Constant.CMD_SELL_STORED:
        sayilar = _tamsayilar(args)
        esya_id = sayilar[0] if sayilar else None
        town_id = sayilar[1] if len(sayilar) > 1 else 0
        if esya_id is None or not _gift_cikar(save, esya_id):
            print(" ! Depoda esya yok:", args)
            return
        if get_attribute_from_item_id(esya_id, "cost_type") != "c":
            apply_cost(save["playerInfo"], save["maps"][town_id], esya_id, -0.05)
        print("Depodaki esya satildi:", esya_id)

    elif cmd == Constant.CMD_BUY_STORED_ITEM_CASH:
        sayilar = _tamsayilar(args)
        esya_id = sayilar[0] if sayilar else None
        if esya_id is None:
            print(" ! BUY_STORED_ITEM_CASH: gecersiz args", args)
            return
        fiyat = int(get_attribute_from_item_id(esya_id, "cost") or 0)
        if get_attribute_from_item_id(esya_id, "cost_type") != "c":
            fiyat = 0  # yalnızca cash ile satılan depo eşyaları
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"]) - fiyat, 0)
        _gift_ekle(save, esya_id, 1)
        print(f"Depoya esya satin alindi: {esya_id} ({fiyat} cash)")

    elif cmd == Constant.CMD_HIRE_WORKER:
        # İşçi sistemi: kayıtta hangi alanın güncellendiği henüz doğrulanmadı.
        # Yanlış alanı bozmamak için şimdilik yalnızca günlüğe yazıyoruz.
        print(" ! HIRE_WORKER: protokol henuz cozulmedi, args =", args)

    elif cmd == Constant.CMD_INCREASE_POPULATION:
        print(" ! INCREASE_POPULATION: protokol henuz cozulmedi, args =", args)

    elif cmd == Constant.CMD_ATTACK_PLAYER:
        _saldiri_baslat(save, args)

    elif cmd == Constant.CMD_END_ATTACK:
        _saldiri_bitir(save, args)

    elif cmd == Constant.CMD_CLEAN_ATTACKS:
        raporlar = _liste_al(save.setdefault("privateState", {}), "attacksReceived")
        adet = _tam(args[0]) if args else None
        if adet and adet > 0:
            del raporlar[:adet]
        else:
            raporlar.clear()
        print("Saldiri raporlari temizlendi, kalan:", len(raporlar))

    elif cmd == Constant.CMD_SET_ATTACK_TEAM:
        veri = _json_veri(args)
        takim = veri if veri is not None else args
        ps = save.setdefault("privateState", {})
        takimlar = ps.get("teams")
        if not isinstance(takimlar, dict):
            takimlar = {}
            ps["teams"] = takimlar
        takimlar["attack"] = takim
        print("Saldiri takimi kaydedildi:", str(takim)[:120])

    elif cmd == Constant.CMD_SPY:
        print("Casusluk komutu (kayitta degisiklik yok):", args)

    elif cmd == Constant.CMD_WIN_TROPHY:
        print("Kupa komutu (kayitta degisiklik yok):", args)

    elif cmd == Constant.CMD_ADD_COLLECTABLE:
        collection_id = args[0]
        collectible_id = args[1]
        # TODO 

    else:
        print(f"Unhandled command '{cmd}' -> args", args)
        return
    

