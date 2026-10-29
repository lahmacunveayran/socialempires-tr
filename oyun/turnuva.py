"""Turnuvalar (istemcinin TournamentManager veri modeli).

Bir turnuvada `num_players` (4) oyuncu vardır; herkes diğer herkese bir kez
saldırır (her oyuncunun `matches` listesi, saldıran olduğu maçlardır). Tek
kişilik sunucuda boş koltuklar bot köyleriyle doldurulur ve botların maçları
hemen sonuçlandırılır. Oyuncunun maçları bitince (ya da süre dolunca) turnuva
biter; birinci olan gerçek oyuncuysa ödülü (`tournament_type[...].prize`)
kaydına yazılır.

Durum saves/turnuvalar.json dosyasında tutulur.
"""

import json
import os
import random
import threading
import uuid

from oyun.config import get_game_config, get_item_from_id
from oyun.ekonomi import timestamp_now
from oyun.komutlar import depo_ekle
from oyun.kayit import all_saves_userid, save_session, session
from oyun.yollar import SAVES_DIR

KILIT = threading.RLock()
TAKIM_BOYU = 20
_turnuvalar = None


# ---------------------------------------------------------------------------
# Kalıcılık
# ---------------------------------------------------------------------------

def _dosya():
    return os.path.join(SAVES_DIR, "turnuvalar.json")


def _hepsi():
    global _turnuvalar
    if _turnuvalar is None:
        try:
            with open(_dosya(), encoding="utf-8") as f:
                _turnuvalar = json.load(f)
        except (OSError, ValueError):
            _turnuvalar = {}
    return _turnuvalar


def _kaydet():
    os.makedirs(SAVES_DIR, exist_ok=True)
    gecici = _dosya() + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(_hepsi(), f, ensure_ascii=False)
    os.replace(gecici, _dosya())


def sifirla():
    """Testler için bellekteki durumu unutur."""
    global _turnuvalar
    _turnuvalar = None


# ---------------------------------------------------------------------------
# Oyuncular ve takımlar
# ---------------------------------------------------------------------------

def turler():
    return get_game_config().get("tournament_type", {})


def _tur(tur_id):
    return turler().get(str(tur_id)) or next(iter(turler().values()))


def _savasci_mi(birim_id):
    esya = get_item_from_id(birim_id) or {}
    yasak = get_game_config()["globals"].get("TOURNAMENT_UNITS_NOT_ALLOWED") or []
    return (esya.get("type") == "u" and int(esya.get("attack", 0) or 0) > 0
            and int(birim_id) not in yasak)


def _bot_takimi(kayit):
    birimler = [e[0] for e in kayit["maps"][0].get("items", []) if _savasci_mi(e[0])]
    birimler.sort(key=lambda b: -int((get_item_from_id(b) or {}).get("attack", 0) or 0))
    birimler = birimler[:TAKIM_BOYU]
    return birimler + [0] * (TAKIM_BOYU - len(birimler))


def _oyuncu(uid, kayit, takim):
    takim = [int(x) for x in (takim or [])][:TAKIM_BOYU]
    return {
        "user_id": str(uid),
        "user_name": kayit["playerInfo"].get("name", "Oyuncu"),
        "level": int(kayit["maps"][0].get("level", 1)),
        "country": "TR",
        "abandonned": "0",
        "team": takim + [0] * (TAKIM_BOYU - len(takim)),
        "matches": [],
    }


def _botlar(seviye, adet, haric):
    adaylar = []
    for uid in all_saves_userid():
        kayit = session(uid)
        if kayit and kayit["playerInfo"].get("bot") and uid not in haric:
            adaylar.append((abs(int(kayit["maps"][0].get("level", 1)) - seviye), uid, kayit))
    adaylar.sort(key=lambda a: a[0])
    havuz = adaylar[:max(adet * 3, adet)]
    random.shuffle(havuz)
    return [(uid, kayit) for _, uid, kayit in havuz[:adet]]


# ---------------------------------------------------------------------------
# Turnuva akışı
# ---------------------------------------------------------------------------

def _mac_listelerini_kur(turnuva):
    for oyuncu in turnuva["players"]:
        oyuncu["matches"] = [{
            "attacker_id": oyuncu["user_id"], "victim_id": rakip["user_id"],
            "finished": False, "attacker_won": False, "attacker_points": 0,
            "date_started": 0, "date_finished": 0,
        } for rakip in turnuva["players"] if rakip is not oyuncu]


def _bot_maclarini_oyna(turnuva, simdi):
    """Botların saldırdığı maçlar hemen sonuçlanır (makul puanlarla)."""
    for oyuncu in turnuva["players"]:
        if not oyuncu.get("bot"):
            continue
        for mac in oyuncu["matches"]:
            if mac["finished"]:
                continue
            kazandi = random.random() < 0.5
            mac.update(finished=True, attacker_won=kazandi,
                       attacker_points=round(random.uniform(55, 90) if kazandi else random.uniform(10, 40), 2),
                       date_started=simdi - random.randint(60, 300), date_finished=simdi)


def _mac(turnuva, saldiran_id, kurban_id):
    for oyuncu in turnuva["players"]:
        if oyuncu["user_id"] == str(saldiran_id):
            for mac in oyuncu["matches"]:
                if mac["victim_id"] == str(kurban_id):
                    return mac
    return None


def _puan(oyuncu):
    biten = [m for m in oyuncu["matches"] if m["finished"]]
    return (sum(float(m["attacker_points"]) for m in biten),
            -sum(m["date_finished"] - m["date_started"] for m in biten), len(biten))


def _bitir(turnuva, simdi):
    """Turnuvayı bitirir; birinci gerçek oyuncuysa ödülünü verir."""
    if turnuva.get("date_finished"):
        return
    turnuva["date_finished"] = simdi
    turnuva["match_playing"] = False
    adaylar = [o for o in turnuva["players"] if str(o.get("abandonned")) != "1" and _puan(o)[2]]
    if not adaylar:
        return
    birinci = max(adaylar, key=lambda o: _puan(o)[:2])
    turnuva["winner_id"] = birinci["user_id"]
    kayit = session(birinci["user_id"])
    if not kayit or kayit["playerInfo"].get("bot"):
        return
    oduller = _tur(turnuva["tournament_type_id"]).get("prize") or []
    odul = oduller[turnuva["reward_id"] % len(oduller)] if oduller else {}
    kayit["maps"][0]["coins"] = int(kayit["maps"][0].get("coins", 0)) + int(odul.get("g", 0) or 0)
    kayit["playerInfo"]["cash"] = int(kayit["playerInfo"].get("cash", 0)) + int(odul.get("c", 0) or 0)
    for birim_id, adet in (odul.get("u") or {}).items():
        depo_ekle(kayit, int(birim_id), int(adet))
    save_session(birinci["user_id"])


def _guncelle(turnuva, simdi):
    tur = _tur(turnuva["tournament_type_id"])
    if turnuva.get("date_finished"):
        return
    suresi_doldu = simdi > int(turnuva["date_ready"]) + int(tur.get("duration", 24)) * 3600
    gercekler = [o for o in turnuva["players"] if not o.get("bot") and str(o.get("abandonned")) != "1"]
    hepsi_bitti = all(m["finished"] for o in gercekler for m in o["matches"])
    if suresi_doldu or hepsi_bitti:
        _bitir(turnuva, simdi)


def _kullanicinin(uid):
    for turnuva in _hepsi().values():
        uyeler = {o["user_id"] for o in turnuva["players"]} - set(turnuva.get("temizleyenler", []))
        if str(uid) in uyeler:
            return turnuva
    return None


def _istemci_bicimi(turnuva):
    """İç alanlar (bot, winner_id, temizleyenler) istemciye gitmez."""
    if turnuva is None:
        return None
    kopya = {k: v for k, v in turnuva.items() if k not in ("winner_id", "temizleyenler")}
    kopya["players"] = [{k: v for k, v in o.items() if k != "bot"} for o in turnuva["players"]]
    return kopya


def bilgi(uid):
    """get_tournament_info / create / join yanıtının `data` alanı."""
    with KILIT:
        turnuva = _kullanicinin(uid)
        if turnuva:
            _guncelle(turnuva, timestamp_now())
            _kaydet()
        return {
            "tournament": _istemci_bicimi(turnuva),
            "tournament_friends": [],
            "tournament_reward_id": {str(k): 0 for k in turler()},
            "tournament_weekly": {str(k): {"open": "0", "full": "0", "timeLeft": 0}
                                  for k, t in turler().items() if int(t.get("weekly_tournaments") or 0)},
        }


def katil(uid, tur_id, takim):
    """create_tournament / join_tournament: boş koltuklar botlarla dolar."""
    kayit = session(uid)
    if kayit is None:
        return {"result": "NOK"}
    if not any(int(x or 0) > 0 for x in takim or []):
        return {"result": "NOTEAM"}
    with KILIT:
        if _kullanicinin(uid):
            return bilgi(uid)
        tur = _tur(tur_id)
        simdi = timestamp_now()
        turnuva = {
            "tournament_id": uuid.uuid4().hex[:12],
            "tournament_type_id": int(tur["id"]),
            "reward_id": random.randrange(max(1, len(tur.get("prize") or []))),
            "owner": kayit["playerInfo"].get("name", "Oyuncu"),
            "owner_id": str(uid),
            "private": "0",
            "point_type": 0,
            "date_ready": simdi,
            "date_finished": None,
            "match_playing": False,
            "players": [_oyuncu(uid, kayit, takim)],
        }
        seviye = int(kayit["maps"][0].get("level", 1))
        for bot_uid, bot in _botlar(seviye, int(tur.get("num_players", 4)) - 1, {str(uid)}):
            oyuncu = _oyuncu(bot_uid, bot, _bot_takimi(bot))
            oyuncu["bot"] = True
            turnuva["players"].append(oyuncu)
        _mac_listelerini_kur(turnuva)
        _bot_maclarini_oyna(turnuva, simdi)
        _hepsi()[turnuva["tournament_id"]] = turnuva
        _kaydet()
    return bilgi(uid)


def mac_baslat(uid, kurban_id):
    with KILIT:
        turnuva = _kullanicinin(uid)
        mac = _mac(turnuva, uid, kurban_id) if turnuva else None
        if mac is None or mac["finished"] or turnuva.get("date_finished"):
            return {"result": "NOK"}
        mac["date_started"] = timestamp_now()
        turnuva["match_playing"] = True
        _kaydet()
    return {"result": "OK"}


def mac_bitir(uid, kurban_id, kazandi, puan):
    with KILIT:
        turnuva = _kullanicinin(uid)
        mac = _mac(turnuva, uid, kurban_id) if turnuva else None
        if mac is None or mac["finished"]:
            return {"result": "NOK"}
        simdi = timestamp_now()
        mac.update(finished=True, attacker_won=bool(kazandi), date_finished=simdi,
                   attacker_points=round(max(0.0, min(100.0, float(puan or 0))), 2))
        if not mac["date_started"]:
            mac["date_started"] = simdi
        turnuva["match_playing"] = False
        _guncelle(turnuva, simdi)
        _kaydet()
    return {"result": "OK"}


def _cik(turnuva, uid):
    """Oyuncu turnuvadan çıkar; gerçek oyuncu kalmayınca turnuva silinir."""
    turnuva.setdefault("temizleyenler", []).append(str(uid))
    gercekler = {o["user_id"] for o in turnuva["players"] if not o.get("bot")}
    if gercekler <= set(turnuva["temizleyenler"]):
        _hepsi().pop(turnuva["tournament_id"], None)


def ayril(uid):
    """leave/cancel: oyuncu çekilir (maçları sayılmaz), turnuva biter."""
    with KILIT:
        turnuva = _kullanicinin(uid)
        if turnuva:
            for oyuncu in turnuva["players"]:
                if oyuncu["user_id"] == str(uid):
                    oyuncu["abandonned"] = "1"
            _bitir(turnuva, timestamp_now())
            _cik(turnuva, uid)
            _kaydet()
    return {"result": "OK"}


def temizle(uid):
    """clean_tournament: ödül penceresinden sonra oyuncu turnuvadan ayrılır."""
    with KILIT:
        turnuva = _kullanicinin(uid)
        if turnuva:
            _cik(turnuva, uid)
            _kaydet()
    return {"result": "OK"}
