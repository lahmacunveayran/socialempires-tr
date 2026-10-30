"""Proje klasör yolları.

Paketlenmiş (PyInstaller) sürümde veri dosyaları geçici klasöre açılır;
kayıtlar ve modlar ise her zaman programın yanında durur.
"""

import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERI = getattr(sys, "_MEIPASS", KOK)

ASSETS_DIR = os.path.join(_VERI, "assets")
STUB_DIR = os.path.join(_VERI, "stub")
TEMPLATES_DIR = os.path.join(_VERI, "templates")
VILLAGES_DIR = os.path.join(_VERI, "villages")
QUESTS_DIR = os.path.join(VILLAGES_DIR, "quests")
CONFIG_DIR = os.path.join(_VERI, "config")
CONFIG_PATCH_DIR = os.path.join(CONFIG_DIR, "patch")
CEVIRI_DIR = os.path.join(_VERI, "ceviri")

# SE_TABAN_DIZINI: kayıt, mod, ayar ve indirilenlerin yazılabilir klasörü (Android uygulaması kullanır;
# orada oyun dosyaları salt okunur bir klasöre açılır)
BASE_DIR = os.environ.get("SE_TABAN_DIZINI") or (
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else KOK)
MODS_DIR = os.path.join(BASE_DIR, "mods")
# SE_KAYIT_DIZINI: kayıtları başka klasörde tutmak için (testler kullanır)
SAVES_DIR = os.environ.get("SE_KAYIT_DIZINI") or os.path.join(BASE_DIR, "saves")
INDIRILEN_DIR = os.path.join(BASE_DIR, "download_assets")
AYARLAR = os.path.join(BASE_DIR, "ayarlar.json")
