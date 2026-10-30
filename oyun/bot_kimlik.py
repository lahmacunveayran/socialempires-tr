"""Bot köylerinin adı ve portresi: oyunun kendi birimlerinden.

Her bot bir birim ailesinden (şövalye, okçu, büyücü, ejderha...) bir unvan taşır.
Portresi o ailenin oyundaki birim resmidir (buildingthumbs, çevrimdışı temel pakette)
ve bot seviye atladıkça ailenin bir üst birimine geçer: Hafif Şövalye'den
Kraliyet Şövalyesi'ne. Gerçek kişi adı ve fotoğrafı kullanılmaz (sahibi, 30 Ekim 2026).
"""

PORTRE_YOLU = "/default01.static.socialpointgames.com/static/socialempires/buildingthumbs/{}.jpg"
VARSAYILAN_PORTRE = "/img/profile/1025.png"

# Bu seviyelerde portre ailenin bir üst birimine geçer (5 kademe)
KADEMELER = (12, 24, 36, 48)

# Aile: zayıftan güçlüye 5 birim resmi
AILELER = {
    "sovalye": ("caballo1", "caballo2", "caballo3", "caballo4", "caballo5"),
    "piyade": ("infanteriaunidad1", "infanteriaunidad2", "infanteriaunidad3", "infanteriaunidad4", "infanteria5"),
    "okcu": ("arquero1", "arquero2", "arquero3", "arquero4", "arquero5"),
    "atli_okcu": ("caballoarquero1", "caballoarquero", "arquerocaballo3", "arquerocaballo4", "arquerocaballo4"),
    "buyucu": ("mago", "683_mago", "652_magorojo", "706_mage", "706_mage"),
    "trol": ("trol3bueno", "trol1", "trol6", "trol5", "trol8"),
    "ejderha": ("638_draggy", "698_draggy", "651_bluedraggy", "684_dragon", "649_dragonbigred"),
    "elf": ("arqueroelfo", "guerreroelfo", "arqueroelfico", "633_arquero", "elfoblanco"),
    "kuzey": ("vikingo", "vikingolanzahachas", "661_conan", "valkiria", "thor"),
    "col": ("guerreroegipcio2", "camelloguerrero", "momia", "guerreroegipcio1", "guerreroegipcio1"),
    "deniz": ("guerreroatlantis", "arqueroatlantis", "cangrejo", "caballitoatlantis", "neptunoatlante"),
    "goksel": ("701_angelsoldier", "703_angelarquero", "705_lancer", "699_warriorpriest", "704_death"),
    "cehennem": ("644_if_footman", "arqueroinfernounidad", "infernomontado", "infanteria_infernal5",
                 "654_demoniogrande"),
}

# 50 bot (üretim sırası = başlangıç seviyesi sırası); aileler sırayla dağılır, her ailede zayıf ve güçlü köy olur
BOTLAR = [
    ("Kara Şövalye", "sovalye"), ("Kılıç Ağası", "piyade"), ("Okçu Usta", "okcu"), ("Bozkır Atlısı", "atli_okcu"),
    ("Gezgin Büyücü", "buyucu"), ("Dağ Trolü", "trol"), ("Ejder Bekçisi", "ejderha"), ("Orman Korucusu", "elf"),
    ("Kuzeyli Akıncı", "kuzey"), ("Çöl Kervancısı", "col"), ("Deniz Savaşçısı", "deniz"),
    ("Göksel Muhafız", "goksel"), ("Cehennem Şövalyesi", "cehennem"),
    ("Ak Şövalye", "sovalye"), ("Kalkan Beyi", "piyade"), ("Yay Ustası", "okcu"), ("Rüzgâr Atlı", "atli_okcu"),
    ("Ak Sakallı", "buyucu"), ("Mağara Beyi", "trol"), ("Ateş Dili", "ejderha"), ("Yüce Elf", "elf"),
    ("Kızıl Balta", "kuzey"), ("Kum Fırtınası", "col"), ("Dalga Beyi", "deniz"),
    ("Bulut Beyi", "goksel"), ("Kara Alev", "cehennem"),
    ("Demir Şövalye", "sovalye"), ("Mızrakçı Başı", "piyade"), ("Kartal Göz", "okcu"), ("Akıncı Beyi", "atli_okcu"),
    ("Kızıl Kâhin", "buyucu"), ("Balta Trolü", "trol"), ("Kızıl Pul", "ejderha"), ("Yaprak Okçu", "elf"),
    ("Buz Diyarı Beyi", "kuzey"), ("Vaha Beyi", "col"), ("Mercan Beyi", "deniz"),
    ("Işık Kanadı", "goksel"), ("Kor Yürek", "cehennem"),
    ("Gümüş Mızrak", "sovalye"), ("Tunç Kılıç", "piyade"), ("Sadak Beyi", "okcu"), ("Doru Atlı", "atli_okcu"),
    ("Yıldız Bilgini", "buyucu"), ("Yağmacı Reis", "trol"), ("Fırtına Kanadı", "ejderha"),
    ("Ay Ormanı Beyi", "elf"), ("Thor", "kuzey"), ("Şafak Bekçisi", "goksel"), ("Kül Beyi", "cehennem"),
]
ISIMLER = [ad for ad, _ in BOTLAR]
_AILE = dict(BOTLAR)

# İlk sürümlerin tarihî adları, üretim sırasıyla; kayıtlı köyler aynı sıradaki yeni ada geçer
ESKI_ISIMLER = [
    "Kara Han", "Bozkurt Bey", "Demir Yay", "Gökbörü", "Alp Er Tunga",
    "Kül Tigin", "Bilge Kağan", "Tomris Hatun", "Modu Han", "Attila",
    "Balamir", "İlteriş", "Kapgan", "Suyab", "Tardu",
    "Bayan Kağan", "İstemi Yabgu", "Bilge Hatun", "Kür Şad", "Tonyukuk",
    "Vezir Nizam", "Şahin Bey", "Korkut Ata", "Dede Korkut", "Manas",
    "Cengiz Han", "Kubilay", "Timur", "Babür", "Alparslan",
    "Tuğrul Bey", "Melikşah", "Sultan Sencer", "Harzemşah", "Celaleddin",
    "Ertuğrul", "Osman Bey", "Orhan Bey", "Murat Bey", "Yıldırım",
    "Fatih", "Yavuz", "Kanuni", "Sokullu", "Kılıç Arslan",
    "Nurettin", "Selahaddin", "Baybars", "Kutuz", "Berke Han",
]
YENI_AD = dict(zip(ESKI_ISIMLER, ISIMLER))


def portre(ad, seviye):
    """Botun seviyesine göre ailesinin birim resmi; bot listede yoksa varsayılan portre."""
    aile = _AILE.get(ad)
    if not aile:
        return VARSAYILAN_PORTRE
    kademe = sum(1 for esik in KADEMELER if int(seviye or 0) >= esik)
    return PORTRE_YOLU.format(AILELER[aile][kademe])


def _seviye(kayit):
    try:
        return int(kayit["maps"][0].get("level", 1))
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return 1


def adlari_yenile(kayitlar):
    """Eski adlı bot köylerini yeni adlarına geçirir, bot portrelerini seviyelerine göre tazeler.

    Raporlardaki (attacksSent/attacksReceived) eski adlar ve portreler de değişir.
    kayitlar: {uid: kayıt}; değişen kayıtların kimliklerini döndürür (kaydetmek çağıranın işi)."""
    degisen = set()
    for uid, kayit in kayitlar.items():
        if not isinstance(kayit, dict):
            continue
        pi = kayit.get("playerInfo") or {}
        if pi.get("bot"):
            ad = YENI_AD.get(pi.get("name"), pi.get("name"))
            if ad in _AILE:
                yeni = {"name": ad, "pic": portre(ad, _seviye(kayit)), "map_names": [f"{ad} Kalesi"]}
                if any(pi.get(k) != v for k, v in yeni.items()):
                    pi.update(yeni)
                    degisen.add(uid)
        ps = kayit.get("privateState") or {}
        for giris in (ps.get("attacksSent") or []) + (ps.get("attacksReceived") or []):
            rakip = (giris.get("description") or {}).get("oponent") if isinstance(giris, dict) else None
            if isinstance(rakip, dict) and rakip.get("name") in YENI_AD:
                rakip["name"] = YENI_AD[rakip["name"]]
                rakip["pic"] = portre(rakip["name"], rakip.get("level"))
                degisen.add(uid)
    return degisen
