# -*- coding: utf-8 -*-
"""Oyun hızı (zaman ölçeği) ayarı.

Oyun istemcisi üretim/inşaat sürelerini `game_config` içindeki
`activation` / `expiration` alanlarından okuyor. Bu alanları istemciye
gönderirken ölçeğe bölerek oyunu hızlandırıyoruz; sunucudaki ve
kayıttaki değerler değişmiyor.

Ayar sırası:
1. `TIME_SCALE` ortam değişkeni
2. `ayarlar.json` içindeki `zaman_olcegi` (ör. 3.0)
3. Varsayılan 1.0 (normal hız)

Örnek: 3.0 => süreler üçte bire iner (6 saatlik üretim 2 saat olur).
"""

import os

from oyun import ayarlar


def zaman_olcegi() -> float:
    ham = os.environ.get("TIME_SCALE")
    if ham is None:
        ham = ayarlar.oku().get("zaman_olcegi")

    if ham is None:
        return 1.0

    try:
        olcek = float(ham)
    except (TypeError, ValueError):
        print(f" ! Gecersiz zaman olcegi: {ham!r}; 1.0 kullanilacak")
        return 1.0

    if not (0.1 <= olcek <= 100):
        print(f" ! Zaman olcegi 0.1-100 araliginda olmali (verilen: {olcek}); 1.0 kullanilacak")
        return 1.0

    return olcek
