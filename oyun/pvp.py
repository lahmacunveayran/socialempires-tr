"""PvP: oyuncuya saldırı (attack_player / end_attack).

Savaş istemcide oynanır ama ganimet istemcide uygulanmaz: savaş bitince
istemci haritayı sunucudan yeniden yükler. Yani saldıranın kazandığı her şey
burada, `end_attack` ile gelen sonuca göre verilir.

end_attack argümanı (istemcinin Assault.sendAssaultResults'ından):
    [json] ya da belediye binası olmayan köyde [json, true]
    {attacker: {user_id, map, ...}, victim: {user_id, level, ...},
     resources: {g, x}, resources_victim: {g},
     attacker_units: [[id, baslangic, olen, kurtarilan], ...],
     victim_units:   [[id, baslangic, olen, kurtarilan], ...],
     win, duration, voluntary_end, townhall_gold, honor}

Kurallar istemcinin Config sabitleriyle aynıdır; kurala uymayan sonuçlar
reddedilmez (savaş zaten oynandı), yalnızca ganimeti sıfırlanır.
"""

import json
import math

from oyun.ada import fetih_kaydet
from oyun.config import get_game_config, get_item_from_id
from oyun.ekonomi import timestamp_now
from oyun.kayit import all_saves_userid, neighbor_session, save_session

SALDIRI_HAKKI = 3                 # Config.ATTACKS_MAX
SALDIRI_PERIYODU = 6 * 3600       # Config.ATTACKS_PERIOD_HOURS
AYNI_HEDEF_SURESI = 4 * 3600      # Config.ATTACKS_SAME_PLAYER_HOURS
BIRIM_BASINA_ALTIN = 200          # Config.MAX_GOLD_FROM_ASSAULT
SAVUNMA_BIRIM_ODULU = 20          # birim değerinin %10'u, en çok 20
GALIBIYET_ASGARI_ALTIN = 25
XP_PAYI = 150                     # duvar vb. 1 XP'lik yıkımlar için pay


def _tam(deger, varsayilan=0):
    try:
        return int(float(deger))
    except (TypeError, ValueError):
        return varsayilan


def _liste(kap, anahtar):
    deger = kap.get(anahtar)
    if not isinstance(deger, list):
        deger = kap[anahtar] = []
    return deger


def _ozet(kayit):
    pi = kayit.get("playerInfo", {})
    harita = (kayit.get("maps") or [{}])[0]
    return {
        "name": pi.get("name") or "Oyuncu",
        "user_id": str(pi.get("pid") or ""),
        "level": harita.get("level", 1),
        "pic": pi.get("pic", ""),
    }


def _olenler(birimler, dahil=None):
    """[[id, baslangic, olen, kurtarilan], ...] -> {id: kalici_kayip}."""
    kayip = {}
    for satir in birimler if isinstance(birimler, list) else []:
        if not isinstance(satir, list) or len(satir) < 3:
            continue
        birim_id = _tam(satir[0])
        olen = max(0, _tam(satir[2]) - (_tam(satir[3]) if len(satir) > 3 else 0))
        if olen and (dahil is None or dahil(birim_id)):
            kayip[birim_id] = kayip.get(birim_id, 0) + olen
    return kayip


def _birimleri_sil(harita, kayiplar):
    """Haritadan yalnızca birimleri (tür 'u') siler; binalara dokunmaz."""
    for birim_id, adet in kayiplar.items():
        if (get_item_from_id(birim_id) or {}).get("type") != "u":
            continue
        for esya in [e for e in harita.get("items", []) if e[0] == birim_id][:adet]:
            harita["items"].remove(esya)


def saldiri_hakki_var(saldiran, simdi):
    """İstemcinin Base.processAttacks hesabı: son saldırıdan geriye 6 saat."""
    ps = saldiran["privateState"]
    if _tam(ps.get("attacksPack")) > 0:
        return True
    sifirlama = _tam(ps.get("tsAttacksReset"))
    zamanlar = [_tam(a.get("time")) for a in _liste(ps, "attacksSent") if isinstance(a, dict)]
    if not zamanlar or simdi - max(zamanlar) >= SALDIRI_PERIYODU:
        return True
    son = max(zamanlar)
    sayi = sum(1 for t in zamanlar if son - t < SALDIRI_PERIYODU and t > sifirlama)
    return sayi < SALDIRI_HAKKI


def saldiri_baslat(saldiran, args):
    """attack_player [kurban_id]: istemci yanıtı kullanmaz; yalnızca günlük."""
    print("Saldiri basladi:", args[0] if args else "?")
    return True


def saldiri_bitir(saldiran, args):
    """end_attack: savaş sonucunu iki tarafa uygular."""
    try:
        veri = args[0] if isinstance(args[0], dict) else json.loads(args[0])
    except (IndexError, TypeError, ValueError):
        print(" ! end_attack: JSON yok:", args)
        return False
    kurban_id = str((veri.get("victim") or {}).get("user_id") or "")
    kendi_id = str(saldiran["playerInfo"].get("pid", ""))
    if not kurban_id or kurban_id == kendi_id:
        print(" ! end_attack: gecersiz hedef", kurban_id)
        return False
    kurban = neighbor_session(kurban_id)
    # Statik komşular (villages/: Arthur, AcidCaos...) herkes için ortaktır;
    # saldırı onları değiştirmez.
    kayitli = kurban is not None and kurban_id in all_saves_userid()

    simdi = timestamp_now()
    ps = saldiran["privateState"]
    belediye_yok = len(args) > 1 and bool(args[1])
    kazandi = _tam(veri.get("win")) == 1
    gonderilen = _liste(ps, "attacksSent")

    # Kurala uymayan saldırı (hak bitti / aynı hedef 4 saat içinde / hedefin
    # kalkanı var) ganimetsiz kaydedilir; kalkanlı hedefe dokunulmaz.
    kalkanli = kayitli and _tam(kurban["privateState"].get("shield_until")) > simdi
    kurala_uygun = not kalkanli and saldiri_hakki_var(saldiran, simdi) and not any(
        isinstance(a, dict) and str(a.get("victim_id")) == kurban_id
        and simdi - _tam(a.get("time")) < AYNI_HEDEF_SURESI for a in gonderilen)
    if _tam(ps.get("attacksPack")) > 0:
        ps["attacksPack"] = _tam(ps["attacksPack"]) - 1

    harita_no = _tam((veri.get("attacker") or {}).get("map"))
    haritalar = saldiran["maps"]
    harita = haritalar[harita_no] if 0 <= harita_no < len(haritalar) else haritalar[0]
    kaynaklar = veri.get("resources") or {}
    kurban_seviye = _tam((veri.get("victim") or {}).get("level"), 1)
    if kurban:
        kurban_seviye = _tam(kurban["maps"][0].get("level"), kurban_seviye)

    altin = xp = 0
    if kurala_uygun and not belediye_yok:
        yikilan = sum(_olenler(veri.get("victim_units")).values())
        altin_tavani = min(int(get_game_config()["globals"].get("MAX_GOLD_ASSAULT", 20000)),
                           BIRIM_BASINA_ALTIN * yikilan + kurban_seviye * 100 + GALIBIYET_ASGARI_ALTIN)
        altin = max(0, min(_tam(kaynaklar.get("g")), altin_tavani))
        xp = max(0, min(_tam(kaynaklar.get("x")), math.ceil(0.05 * altin) + yikilan + XP_PAYI))
    harita["coins"] = int(harita.get("coins", 0)) + altin
    harita["xp"] = int(harita.get("xp", 0)) + xp

    onur = 0 if belediye_yok else max(0, min(10, _tam(veri.get("honor"))))
    ps["honor"] = _tam(ps.get("honor")) + onur
    saldiran["playerInfo"]["honor_points"] = _tam(saldiran["playerInfo"].get("honor_points")) + onur

    _birimleri_sil(harita, _olenler(veri.get("attacker_units")))

    aciklama = dict(veri)
    aciklama["resources"] = {"g": altin, "x": xp}
    gonderilen.append({"time": simdi, "victim_id": kurban_id,
                       "description": dict(aciklama, oponent=(_ozet(kurban) if kurban else veri.get("victim")))})
    del gonderilen[:-50]

    if not kayitli or kalkanli:
        return True
    kps = kurban["privateState"]
    savunma_odulu = 0
    if not kazandi:
        olduren = sum(_olenler(veri.get("attacker_units")).values())
        savunma_odulu = max(0, min(_tam((veri.get("resources_victim") or {}).get("g")),
                                   SAVUNMA_BIRIM_ODULU * olduren))
        kurban["maps"][0]["coins"] = int(kurban["maps"][0].get("coins", 0)) + savunma_odulu
    _birimleri_sil(kurban["maps"][0], _olenler(veri.get("victim_units")))

    aciklama["resources_victim"] = {"g": savunma_odulu}
    alinan = _liste(kps, "attacksReceived")
    alinan.append({"time": simdi, "attacker_id": kendi_id, "viewPending": 1,
                   "description": dict(aciklama, oponent=_ozet(saldiran))})
    del alinan[:-50]

    if kazandi:
        try:
            fetih_kaydet(saldiran, veri.get("victim"))
        except Exception as hata:
            print(" ! Fetih kaydi hatasi:", hata)
    save_session(kurban_id)
    # Bota saldırı: kurbanın ittifakı oyuncuya intikam seferi ilan edebilir (Diyar Haberleri)
    from oyun import dunya
    if dunya.etkin is not None:
        try:
            dunya.etkin.oyuncu_saldirdi(kendi_id, saldiran["playerInfo"].get("name", ""), kurban_id, kurban)
        except Exception as hata:  # haber, savaş sonucunu bozmasın
            print(" ! Intikam seferi ilan edilemedi:", hata)
    print(f"Saldiri bitti: {_ozet(kurban)['name']} - {'kazandi' if kazandi else 'kaybetti'}"
          f" ({altin} altin, {xp} XP{'' if kurala_uygun else ', kural disi: ganimet yok'})")
    return True
