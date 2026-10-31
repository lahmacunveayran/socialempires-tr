"""1.4.07 istemcisinin kayıttan okuduğu yeni privateState alanları (GEC-04).

Liste, istemcinin bayt kodundan çıkarıldı (`araclar/kayit_alanlari.py`, `docs/inceleme/1407-kayit-alanlari.json`):
0926'nın okumadığı, 1.4.07'nin `privateState.<ad>` diye okuduğu 18 alan. Ek olarak `attacksWon`: 0926 da okuyordu, ama
kayıtlarda hiç yok ve 1.4.07'nin saldırı hedefleri ilerlemesini ondan alıyor. Her alanın türü, istemcinin onu nasıl
kullandığından.

Göçün ilkesi: göç, istemcinin bugünkü davranışını değiştirmez. Bir alan yalnızca yokluğu istemciyi bozuyorsa
(`undefined.indexOf` hatası, NaN, olmayan sıraya erişim) eklenir; eklenen değer "hiç yok" anlamındaki boş değerdir.
Yokluğu bir özelliği kapalı tutan alanlar (günlük ödül, ilk alım teklifi, Ada Ocağı...) eklenmez; onları işleyen
komutlarla birlikte açılırlar (GEC-03, GEC-05).
"""

# ad: (tür, boş değer ya da None, istemcide okuyan yöntem ve yokluğunun sonucu)
# Boş değeri None olan alan göçte eklenmez.
ALANLAR = {
    "purchasedShields": (list, [], "ShieldManager/isShieldAvailable, buyShield: _purchasedShields.indexOf; yoksa hata"),
    "shieldEndTime": (int, 0, "ShieldManager/setPlayerShieldState: 0 → -1 (kalkan yok); yoksa buyShield NaN hesaplar"),
    "shieldCooldown": (int, 0, "ShieldManager/setPlayerShieldState: 0 → -1; yoksa bekleme süresi NaN"),
    "recruitmentPrices": (list, [], "PopupRecruitment$/canOpen: playerRecruitmentPrices.indexOf; yoksa hata"),
    "potionsReceived": (int, 0, "Base/loadGraveyardState parseInt; yoksa NaN, pencerede 'NaNx' yazar"),
    "tournamentFormation": (int, 0, "SelectionTeamWindow/init: tournament_formations[diziliş]; yoksa olmayan sıra"),
    "attacksWon": (int, None, "GoalAssaultsWon: hedef ilerlemesi; yoksa NaN, saldırı hedefleri bitmez (göçte "
                              "saldırı raporlarından sayılır)"),
    "attacksLost": (int, None, "GoalAssaultsStarted: attacksWon + attacksLost; yoksa NaN (göçte raporlardan)"),
    "PVPattacksReceived": (dict, None, "PlayerStatus/Init → attacksLog, for-in; yokluğu boş günlük gibi (GEC-05)"),
    "barracksQueues": (dict, None, "BuildingQueueManager/init for-in; yokluğu boş kuyruk gibi (GEC-03)"),
    "collectGame": (dict, None, "CollectGameManager/initIslandPlayerData for-in; Ada Ocağı (GEC-03)"),
    "collectGameGivenPrizes": (list, None, "Utils.inArray dizi değilse false döner; Ada Ocağı (GEC-03)"),
    "unitPacks": (dict, None, "UnitPacksManager/initPlayerData for-in; yokluğu boş gibi (GEC-03)"),
    "viralOffers": (dict, None, "SpecialDayOfferManager/setPlayerInfo for-in; yokluğu boş gibi"),
    "resurrectableUnits": (list, None, "Base/loadGraveyardState for-in; yokluğu boş mezarlık gibi (GEC-03)"),
    "graveyardCapacity": (int, None, "Base/loadGraveyardState parseInt; Main.graveyardCapacity başka yerde okunmuyor"),
    "firstPurchaseTimestamp": (int, None, "FirstOfferButton/isActive; yokluğu ilk alım teklifini kapalı tutar"),
    "numDayLogged": (int, None, "DailyBonusManager, FirstOfferButton; yokluğu yeni günlük ödülü kapalı tutar"),
    "showDailyBonus": (int, None, "Base/loadPlayerInfoSuccess, DailyBonusButton; yokluğu düğmeyi kapalı tutar"),
}


def saldiri_sonuclari(ps: dict):
    """(kazanılan, kaybedilen): sonucu bilinen saldırı raporlarından (bot akınlarının raporunda sonuç yok)."""
    raporlar = [r for r in ps.get("attacksSent") or []
                if isinstance(r, dict) and isinstance(r.get("description"), dict)]
    kazanilan = sum(1 for r in raporlar if r["description"].get("win") in (1, "1"))
    return kazanilan, len(raporlar) - kazanilan


def _turu_uyar(deger, tur):
    if tur is int:
        return isinstance(deger, (int, float)) and not isinstance(deger, bool)
    return isinstance(deger, tur)


# Göçün her kayıtta bulunduğunu güvence altına aldığı alanlar
RAPORDAN = ("attacksWon", "attacksLost")
GUVENCE = tuple(ad for ad, (_, bos, _) in ALANLAR.items() if bos is not None) + RAPORDAN


def guvence_hatalari(ps: dict) -> list:
    """Güvencedeki alanlardan eksik olan ya da türü istemcinin beklediği tür olmayanlar."""
    return [ad for ad in GUVENCE if ad not in ps or not _turu_uyar(ps[ad], ALANLAR[ad][0])]


def eksikleri_tamamla(ps: dict) -> list:
    """Güvencedeki alanları ekler, türü yanlış olanı boş değerle değiştirir; değişen adları döndürür.

    Saldırı sayıları yoksa saldırı raporlarından sayılır; varsa (istemci saldırı bitince artırır) dokunulmaz."""
    degisen = []
    hesap = dict(zip(RAPORDAN, saldiri_sonuclari(ps)))
    for ad in GUVENCE:
        tur, deger, _ = ALANLAR[ad]
        deger = hesap.get(ad, deger)
        if ad not in ps or not _turu_uyar(ps[ad], tur):
            ps[ad] = list(deger) if isinstance(deger, list) else deger
            degisen.append(ad)
    return degisen
