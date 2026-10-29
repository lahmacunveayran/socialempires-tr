"""PvP: oyuncuya saldırı (attack_player / end_attack).

Savaş istemcide oynanır; `end_attack` ile gelen sonuç burada iki tarafa
uygulanır. Ganimet ve kupa kuralları `denge.py` içindedir.
"""

import json

from oyun import denge
from oyun.ada import fetih_kaydet
from oyun.ekonomi import timestamp_now
from oyun.kayit import all_saves_userid, neighbor_session, save_session


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


def saldiri_baslat(saldiran, args):
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


def saldiri_bitir(saldiran, args):
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

    if int(kurban.get("privateState", {}).get("shield_until", 0) or 0) > timestamp_now():
        print(" ! end_attack: hedefin kalkani aktif, saldiri reddedildi")
        return False

    # Orijinal kural: 6 saatte en fazla 3 saldırı ve aynı hedefe tekrar saldırı yok.
    # Ancak hedef son 24 saatte sana saldırdıysa intikam saldırısına izin verilir.
    simdi_once = timestamp_now()
    intikam = False
    for eski_rapor in (_liste_al(saldiran.get("privateState", {}), "attacksReceived")[-30:]):
        if str(eski_rapor.get("attacker_id")) == kurban_id:
            try:
                if simdi_once - int(eski_rapor.get("time", 0)) < 24 * 3600:
                    intikam = True
                    break
            except (TypeError, ValueError):
                pass

    onceki_saldirilar = [
        a for a in _liste_al(saldiran.setdefault("privateState", {}), "attacksSent")
        if _tam(a.get("time")) and simdi_once - _tam(a.get("time")) < denge.SALDIRI_PERIYODU
    ]
    if len(onceki_saldirilar) >= denge.SALDIRI_HAKKI:
        print(" ! end_attack: 6 saatlik saldiri hakki doldu, reddedildi")
        return False
    if any(str(a.get("victim_id")) == kurban_id for a in onceki_saldirilar) and not intikam:
        print(" ! end_attack: ayni hedefe 6 saat icinde ikinci saldiri, reddedildi")
        return False

    town_id = _tam(veri.get("map")) or 0
    if not (0 <= town_id < len(saldiran.get("maps", []))):
        town_id = 0
    harita = saldiran["maps"][town_id]

    kurban_harita = kurban["maps"][0]
    kazanc = veri.get("resources") if isinstance(veri.get("resources"), dict) else {}
    kayip = veri.get("resources_victim") if isinstance(veri.get("resources_victim"), dict) else {}
    # Sunucu tek miktar üretir; aynı miktar saldırana eklenir, kurbandan düşer.
    for anahtar in KAYNAK_ALANLARI:
        istenen = max(_tam(kazanc.get(anahtar)) or 0, _tam(kayip.get(anahtar)) or 0)
        if istenen <= 0:
            continue
        alan = KAYNAK_ALANLARI[anahtar]
        alinan = min(istenen, denge.GANIMET_TAVANI,
                     int(int(kurban_harita.get(alan, 0)) * denge.GANIMET_ORANI))
        alinan = max(0, min(alinan, int(kurban_harita.get(alan, 0))))
        if alinan:
            harita[alan] = int(harita.get(alan, 0)) + alinan
            kurban_harita[alan] = int(kurban_harita.get(alan, 0)) - alinan
    # XP istemciden gelir ama hedef seviyeyle sınırlıdır.
    hedef_seviye = max(1, int(kurban_harita.get("level", 1)))
    xp_istenen = max(0, _tam(kazanc.get("x")) or 0)
    if xp_istenen:
        harita["xp"] = int(harita.get("xp", 0)) + min(xp_istenen, hedef_seviye * 2)

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
    kazandi = _tam(veri.get("win")) == 1
    kupa = denge.KUPA_KAZAN if kazandi else -denge.KUPA_KAYIP
    saldiran_ps["trophies"] = max(0, int(saldiran_ps.get("trophies", 0)) + kupa)
    kurban_ps["trophies"] = max(0, int(kurban_ps.get("trophies", 0)) - int(kupa / 2))

    raporlar = _liste_al(kurban_ps, "attacksReceived")
    raporlar.append({
        "time": simdi,
        "attacker_id": str(saldiran.get("playerInfo", {}).get("pid", "")),
        "description": rapor,
    })
    if len(raporlar) > 50:
        del raporlar[:-50]

    if kazandi:
        try:
            fetih_kaydet(saldiran, kurban_id)
        except Exception as hata:
            print(" ! Ada fetih kaydi hatasi:", hata)

    # Kurbanın kaydı da diske yazılsın (komut sonunda saldıran yazılıyor).
    # Statik komşular (Arthur, AcidCaos...) kayıtlı oyuncu değil; onlar için yazma yok.
    if kurban_id in all_saves_userid():
        save_session(kurban_id)

    sonuc = "kazandi" if _tam(veri.get("win")) == 1 else "kaybetti"
    print(f"Saldiri bitti: {_oyuncu_ozeti(kurban)['name']} - {sonuc}")
    return True
