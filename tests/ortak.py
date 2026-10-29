"""Testlerin ortak yardımcıları."""

import atexit
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

# Testler gerçek saves/ klasörüne dokunmasın (oyun.* içe aktarılmadan önce).
if not os.environ.get("SE_KAYIT_DIZINI"):
    os.environ["SE_KAYIT_DIZINI"] = tempfile.mkdtemp(prefix="se-test-")
    atexit.register(shutil.rmtree, os.environ["SE_KAYIT_DIZINI"], True)


def bos_kayit(pid="test"):
    return {
        "version": "0.05a",
        "playerInfo": {"pid": pid, "name": "Test", "cash": 100, "default_map": 0,
                       "map_names": ["Test"], "map_sizes": [0]},
        "maps": [{
            "id": 0, "coins": 50000, "wood": 1000, "stone": 1000, "food": 1000,
            "xp": 0, "level": 10, "expansions": [13],
            "items": [[1, 10, 10, 0, 0, 0], [19, 20, 20, 0, 0, 0]],
            "resourcesTraded": {},
        }],
        "privateState": {
            "gifts": [], "completedMissions": [], "rewardedMissions": [],
            "potion": 1, "marketTimestamp": 0, "lastUpgrades": [], "mana": 0,
        },
    }


class KomutTesti(unittest.TestCase):
    """`self.komut(ad, *args)` ile komutu `self.kayit` üzerinde çalıştırır."""

    def setUp(self):
        from oyun import komutlar, pvp
        self.komutlar, self.pvp = komutlar, pvp
        self.kayit = bos_kayit()
        self.kayitlar = {"test": self.kayit}
        self._eski = (komutlar.session, komutlar.save_session, komutlar.neighbor_session,
                      komutlar.all_saves_userid, pvp.neighbor_session, pvp.save_session)
        komutlar.session = self.kayitlar.get
        komutlar.save_session = lambda uid: None
        komutlar.neighbor_session = self.kayitlar.get
        komutlar.all_saves_userid = lambda: list(self.kayitlar)
        pvp.neighbor_session = self.kayitlar.get
        pvp.save_session = lambda uid: None

    def tearDown(self):
        (self.komutlar.session, self.komutlar.save_session, self.komutlar.neighbor_session,
         self.komutlar.all_saves_userid, self.pvp.neighbor_session, self.pvp.save_session) = self._eski

    def komut(self, ad, *args):
        self.komutlar.do_command("test", ad, list(args))

    @property
    def harita(self):
        return self.kayit["maps"][0]

    @property
    def ps(self):
        return self.kayit["privateState"]

    @property
    def cash(self):
        return self.kayit["playerInfo"]["cash"]
