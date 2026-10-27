# -*- coding: utf-8 -*-
"""Günlük otomatik kayıt yedeği.

Sunucu açıkken saatte bir kontrol eder; her gün için `saves/gunluk_yedek/
YYYY-AA-GG/` klasörüne o günkü ilk kayıtları kopyalar. Son 14 gün saklanır.
"""

import os
import shutil
import threading
import time
from datetime import date

from bundle import SAVES_DIR
from sessions import all_saves_userid

YEDEK_KOK = os.path.join(SAVES_DIR, "gunluk_yedek")
SAKLAMA_GUN = 14
KONTROL_ARALIGI = 3600  # saniye


def gunluk_yedek_al():
    bugun = date.today().isoformat()
    klasor = os.path.join(YEDEK_KOK, bugun)
    try:
        os.makedirs(klasor, exist_ok=True)
    except OSError as hata:
        print(f" ! Gunluk yedek klasoru olusturulamadi: {hata}")
        return

    alinan = 0
    for uid in all_saves_userid():
        kaynak = os.path.join(SAVES_DIR, f"{uid}.save.json")
        hedef = os.path.join(klasor, f"{uid}.save.json")
        if os.path.exists(kaynak) and not os.path.exists(hedef):
            try:
                shutil.copy2(kaynak, hedef)
                alinan += 1
            except OSError as hata:
                print(f" ! Yedek alinamadi ({uid}): {hata}")

    if alinan:
        print(f" [+] Gunluk yedek: {alinan} kayit -> {klasor}")
    _eskileri_sil()


def _eskileri_sil():
    try:
        klasorler = sorted(
            d for d in os.listdir(YEDEK_KOK)
            if os.path.isdir(os.path.join(YEDEK_KOK, d))
        )
    except OSError:
        return
    for eski in klasorler[:-SAKLAMA_GUN]:
        try:
            shutil.rmtree(os.path.join(YEDEK_KOK, eski))
        except OSError:
            pass


def _dongu():
    while True:
        try:
            gunluk_yedek_al()
        except Exception as hata:  # yedek hatası oyunu durdurmasın
            print(f" ! Gunluk yedek hatasi: {hata}")
        time.sleep(KONTROL_ARALIGI)


def baslat():
    """Arka planda yedekleme iş parçacığını başlatır (bir kez çağrılır)."""
    is_parcacigi = threading.Thread(target=_dongu, name="gunluk-yedek", daemon=True)
    is_parcacigi.start()
    print(" [+] Gunluk yedekleme etkin (saves/gunluk_yedek)")
