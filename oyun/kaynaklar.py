"""Oyun varlıklarının indirildiği koruma deposu ve sabitlenmiş commit'i.

Varlıklar AcidCaos/socialemperors deposunun assets/ klasöründen iner. Dal adı (main) değişebilir; dosyalar
sessizce değişmesin diye sürüm 0.04a'nın commit'ine sabitlenir (KYN-03). Bu modül yan etkisizdir:
sunucuyu başlatmadan betiklerden de içe aktarılabilir.
"""

DEPO = "AcidCaos/socialemperors"
# 0.04a, 26.09.2025 ("Bump to 0.04a. Bundle build script. Update readme."); çatalımızın tabanı
COMMIT = "f642e0bae5a341f48e73b58f2e6d33a8436992c1"
DEPO_URL = f"https://github.com/{DEPO}.git"
HAM_KOK = f"https://raw.githubusercontent.com/{DEPO}/{COMMIT}/"
HAM_VARLIK = HAM_KOK + "assets/{path}"
