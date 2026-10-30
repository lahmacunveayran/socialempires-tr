"""Android uygulamasının Python girişi: MainActivity `baslat()`ı ayrı bir iş parçacığında çağırır.

Oyun dosyaları (oyun/, templates/, config/...) uygulamayla gelir ve her güncellemede yenilenir. Kayıtlar,
ayarlar, modlar ve indirilen varlıklar HOME altındaki yazılabilir klasörde durur; güncellemede korunur,
uygulama kaldırılınca silinir.
"""

import os
import shutil

KOK = os.path.dirname(os.path.abspath(__file__))
RUFFLE_PAKETI = os.path.join(KOK, "ruffle-paketi.tgz")


def _icerigi_kopyala(kaynak, hedef):
    """Yalnızca içerik: Android, izin ve SELinux özniteliklerinin kopyalanmasını reddeder (copytree/copy2 düşer)."""
    for klasor, _, dosyalar in os.walk(kaynak):
        hedef_klasor = os.path.join(hedef, os.path.relpath(klasor, kaynak))
        os.makedirs(hedef_klasor, exist_ok=True)
        for ad in dosyalar:
            shutil.copyfile(os.path.join(klasor, ad), os.path.join(hedef_klasor, ad))


def hazirla(taban, kok=KOK):
    """Yazılabilir klasörü kurar; ilk açılışta ayarları ve modları oraya kopyalar (var olanlara dokunmaz)."""
    os.makedirs(taban, exist_ok=True)
    # İlk kopya yarıda kesilirse (uygulama kapatıldı) yarım dosya/klasör kalmasın: önce geçici ada, sonra tek adımda yerine
    ayar = os.path.join(taban, "ayarlar.json")
    if not os.path.exists(ayar):
        shutil.copyfile(os.path.join(kok, "ayarlar.json"), ayar + ".tmp")
        os.replace(ayar + ".tmp", ayar)
    modlar = os.path.join(taban, "mods")
    if not os.path.isdir(modlar):
        gecici = modlar + ".tmp"
        shutil.rmtree(gecici, ignore_errors=True)
        _icerigi_kopyala(os.path.join(kok, "mods"), gecici)
        os.replace(gecici, modlar)
    # oyun.yollar bunu içe aktarılırken okur; bu yüzden oyun modüllerinden önce ayarlanır
    os.environ["SE_TABAN_DIZINI"] = taban


def baslat(taban=None, jeton=None):
    """Sunucuyu 127.0.0.1:5050'de açar; dönmez.

    jeton: uygulamanın bu açılış için ürettiği gizli değer; WebView çerez olarak gönderir, başka uygulamalar bilmez."""
    if jeton:
        os.environ["SE_UYGULAMA_JETONU"] = jeton
    hazirla(taban or os.path.join(os.environ["HOME"], "socialempires"))
    from oyun import ruffle
    if not ruffle.hazir_mi() and os.path.exists(RUFFLE_PAKETI):
        with open(RUFFLE_PAKETI, "rb") as f:
            ruffle.hazirla(f.read())  # SHA-512 denetlenir; olmazsa ilk oyunda internetten indirilir
    from oyun.sunucu import calistir
    calistir()
