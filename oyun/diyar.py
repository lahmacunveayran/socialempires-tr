"""Oyun sayfasının yan panelleri: Diyar Haberleri şeridi ve Şeref Kürsüsü.

Şerit Server-Sent Events yerine 15 saniyede bir yoklar: her açık SSE
bağlantısı Waitress'in 8 iş parçacığından birini sürekli tutar ve oyun
varlıklarının inmesini yavaşlatır.
"""

import threading
import time

from flask import request, session

from oyun import dunya as Dunya
from oyun.kayit import all_saves_userid, session as kayit_oturumu
from oyun.sunucu import app

VARSAYILAN_PORTRE = "/img/profile/1025.png"


def portre(kayit):
    """Oyuncunun portresi (botların gerçek portreleri var)."""
    resim = str(kayit.get("playerInfo", {}).get("pic") or "")
    return resim if resim.startswith("/img/") else VARSAYILAN_PORTRE


KURSU_SURESI = 60  # saniye: 100 kayıt dosyası her istekte taranmasın
KURSU_BOYU = 10
YOKLAMA_SANIYE = 15

_kursu = {"zaman": 0, "liste": []}
_kursu_kilidi = threading.Lock()


def _siralama():
    sira = []
    for uid in all_saves_userid():
        kayit = kayit_oturumu(uid)
        if not kayit:
            continue
        harita = kayit["maps"][0]
        sira.append({
            "id": str(uid),
            "ad": kayit["playerInfo"].get("name", "İmparatorluk"),
            "seviye": int(harita.get("level", 1)),
            "xp": int(harita.get("xp", 0)),
            "bot": bool(kayit["playerInfo"].get("bot")),
            "resim": portre(kayit),
        })
    sira.sort(key=lambda o: (-o["seviye"], -o["xp"]))
    for i, o in enumerate(sira, 1):
        o["sira"] = i
        o["rutbe"] = Dunya.rutbe(o["seviye"])
    return sira


def kursu(simdi=None):
    simdi = time.time() if simdi is None else simdi
    with _kursu_kilidi:
        if simdi - _kursu["zaman"] >= KURSU_SURESI:
            _kursu["liste"] = _siralama()
            _kursu["zaman"] = simdi
        return _kursu["liste"]


@app.route("/dunya/kursu")
def kursu_ucu():
    liste = kursu()
    uid = session.get("USERID")
    ben = next((o for o in liste if o["id"] == uid), None)
    return {"ilk": [dict(o, ben=o["id"] == uid) for o in liste[:KURSU_BOYU]],
            "ben": ben, "toplam": len(liste)}


@app.route("/dunya/olaylar")
def olaylar_ucu():
    try:
        sonra = max(0, int(request.args.get("sonra", 0)))
    except ValueError:
        sonra = 0
    dunya = Dunya.etkin
    olaylar = dunya.olaylar_sonra(sonra) if dunya else []
    son = olaylar[-1]["id"] if olaylar else sonra
    return {"olaylar": olaylar, "son": son, "yoklama": YOKLAMA_SANIYE}


@app.route("/dunya/hafta")
def hafta_ucu():
    """Haftalık turnuva tablosu (ilk 10 ödül alır) ve oyuncunun Elo reytingi."""
    from oyun import elo, turnuva
    turnuva.haftayi_guncelle()
    tablo = elo.tablo(turnuva.bot_reytingleri())
    for satir in tablo[:elo.ODULLU_SIRA + 1]:
        satir["resim"] = portre(kayit_oturumu(satir["id"]) or {})
    uid = session.get("USERID")
    kayit = kayit_oturumu(uid) if uid else None
    reyting = (kayit or {}).get("privateState", {}).get("elo", {}).get("puan", elo.BASLANGIC)
    return {"ilk": tablo[:elo.ODULLU_SIRA], "ben": next((o for o in tablo if o["id"] == uid), None),
            "reyting": round(float(reyting)), "hafta": elo.hafta(elo.turkiye_saati())}


@app.route("/dunya/takvim")
def takvim_ucu():
    from oyun import takvim
    return {"etkinlikler": takvim.etkinlikler(), "acik_setler": takvim.acik_setler()}
