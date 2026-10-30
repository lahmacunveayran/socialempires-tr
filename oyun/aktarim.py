"""Yanıtların önbellek başlıkları, ETag/304 ve sıkıştırması.

- Değişmeyen oyun varlıkları ve sürümlü Ruffle dosyaları bir yıl, değişmez
  olarak önbelleğe alınır; ikinci açılışta hiçbiri yeniden inmez.
- Sayfalar, yapılandırma ve kayıt yanıtları her seferinde sorulur
  (`no-cache`); değişmemişse ETag ile 304 döner.
- Yalnızca metin türleri (JSON, JS, HTML...) sıkıştırılır. SWF, PNG ve MP3
  zaten sıkıştırılmıştır, yeniden sıkıştırmak %0 ile %2 kazandırır.
"""

import gzip
import hashlib
import threading
from collections import OrderedDict

from flask import request

DEGISMEZ = "public, max-age=31536000, immutable"
GUNLUK = "public, max-age=86400"
SORARAK = "no-cache"

STATIK = "/default01.static.socialpointgames.com/static/socialempires/"
# Türkçeleştirilmiş oyun SWF'si yama güncellenince değişir: her seferinde sorulur.
SORULAN_STATIK = STATIK + "flash/SocialEmpires"

SIKISTIRILAN_TURLER = ("application/json", "text/", "application/javascript",
                       "application/wasm", "image/svg+xml", "application/xml")
EN_KUCUK = 1024

# Aynı gövde (ör. 1,7 MB'lık yapılandırma) her girişte yeniden
# sıkıştırılmasın: ETag -> sıkıştırılmış gövde.
_onbellek = OrderedDict()
_onbellek_kilidi = threading.Lock()
ONBELLEK_BOYU = 8


def onbellek_politikasi(yol):
    if yol.startswith("/ruffle/"):
        return DEGISMEZ
    if yol.startswith(STATIK):
        return SORARAK if yol.startswith(SORULAN_STATIK) else DEGISMEZ
    if yol.startswith(("/img/", "/css/", "/js/")):
        return GUNLUK
    return SORARAK


def _kodlama_sec():
    kabul = request.headers.get("Accept-Encoding", "").lower()
    kodlamalar = {k.split(";")[0].strip() for k in kabul.split(",")}
    if "gzip" in kodlamalar:
        return "gzip"
    return None


def _sikistir(govde, ozet):
    with _onbellek_kilidi:
        if ozet in _onbellek:
            _onbellek.move_to_end(ozet)
            return _onbellek[ozet]
    # 6. düzey: 1,7 MB yapılandırma ~30 ms'de 12 kat küçülür.
    sikisik = gzip.compress(govde, compresslevel=6, mtime=0)
    with _onbellek_kilidi:
        _onbellek[ozet] = sikisik
        while len(_onbellek) > ONBELLEK_BOYU:
            _onbellek.popitem(last=False)
    return sikisik


def _sikistirilabilir(yanit):
    if yanit.direct_passthrough or yanit.is_streamed or "Content-Encoding" in yanit.headers:
        return False
    if yanit.status_code != 200 or not yanit.mimetype:
        return False
    return yanit.mimetype.startswith(SIKISTIRILAN_TURLER)


def yanit_isle(yanit):
    politika = onbellek_politikasi(request.path)
    if yanit.status_code not in (200, 206, 304):
        politika = SORARAK  # eksik varlık kalıcı önbelleğe girmesin
    # send_file kendi max-age değerini yazar; varlıklarda bizim politikamız geçerli.
    if "Cache-Control" not in yanit.headers or politika != GUNLUK:
        yanit.headers["Cache-Control"] = politika

    if not _sikistirilabilir(yanit):
        return yanit

    govde = yanit.get_data()
    ozet = hashlib.sha1(govde).hexdigest()
    kodlama = _kodlama_sec() if len(govde) >= EN_KUCUK else None
    yanit.vary.add("Accept-Encoding")
    if request.method in ("GET", "HEAD") and yanit.headers["Cache-Control"] == SORARAK:
        # Sıkıştırılmış gövde ayrı bir temsil olduğu için ETag'i de ayrıdır.
        etag = ozet + ("-gz" if kodlama else "")
        yanit.set_etag(etag)
        if request.if_none_match.contains(etag):
            yanit.status_code = 304
            yanit.set_data(b"")
            return yanit
    if kodlama:
        yanit.set_data(_sikistir(govde, ozet))
        yanit.headers["Content-Encoding"] = kodlama
    return yanit


def kaydet(app):
    app.after_request(yanit_isle)
