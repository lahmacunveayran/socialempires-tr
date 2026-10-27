# -*- coding: utf-8 -*-
"""Ekonomi ve PvP denge ayarları.

3x hızda kaynaklar hızlı biriktiği için ganimet oranı ve tavanı düşürüldü;
yeni oyuncular 24 saat kalkanla başlar.
"""

GANIMET_ORANI = 0.10          # kurbanın kaynağının en fazla %10'u
GANIMET_TAVANI = 50000        # kaynak başına üst sınır
YENI_OYUNCU_KALKANI = 24 * 3600
KUPA_KAZAN = 8
KUPA_KAYIP = 4
SALDIRI_HAKKI = 3
SALDIRI_PERIYODU = 6 * 3600
