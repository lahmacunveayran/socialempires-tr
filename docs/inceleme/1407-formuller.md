# 1.4.07 formül defteri (GEC-03)

Sunucunun yeni komutlarda kullandığı her formül, istemcinin bayt kodundan okunur (`SocialEmpires1.4.07sec_fixed.swf`,
`araclar/abc_okur.py`). Her satırda kaynağı olan yöntem yazılı; sabitlerin değerleri istemcinin `Config` ve
`Constants` sınıflarından. Upstream'in sunucusundan ayrılan yerler ayrıca belirtilir.

## Eğitim kuyruğu (`push_queue_unit`, `pop_queue_unit`, `unqueue_unit`, `speed_up_queue`)

Uygulama: `oyun/komutlar.py`, testler: `tests/test_komutlar.py` (`EgitimKuyrugu`).

### Kayıt

`privateState.barracksQueues[qid] = {"ts": t, "amount": n, "unit": birim_id}` (`BuildingQueueManager/init`).

- `qid`: binanın `attrs.bq`'su; istemci `generateQID` ile verir (`lastID + 1`), girişte en büyük `qid`'den sürer.
- `ts`: sıradaki birimin eğitime başladığı an. Sıradakinin bitişi `ts + T` (`BuildingQueueData/setData`).
- Komutlarda kasaba yok: kuyruk her zaman açık kasabada (`Base.Iso`).

### Süre `T`

`T = training_time`, Ruh Karıştırıcı'da (`ID_BUILDING_SOUL_MIXER` = 1529) `sm_training_time`; istemci tam sayıya
keser (`convert_i`). Sunucu, istemciye gönderdiği ölçekli değeri kullanır: `int(float(f"{t / ölçek:.6g}"))`
(`config.get_client_game_config`).

### Bedel (`BuildingQueueManager/addUnit`)

| Adım | Formül |
|---|---|
| Kuyruk sınırı | `remainingUnits < 5` değilse eklenmez |
| Taban | `bedel = cost` |
| Demirci indirimi | birim piyade (78), atlı (79) ya da okçuysa (80) ve haritada demirci (alt kategori 131) varsa `bedel = ceil(bedel × 0.9)` (`REDUCTION_MULTIPLIER_BLACKSMITH`) |
| Üniversite indirimi | birim kuşatmaysa (81) ve haritada üniversite (134) varsa `bedel = ceil(bedel × 0.9)` (`REDUCTION_MULTIPLIER_UNIVERSITY`) |
| Yemek | `yemek = ceil(bedel × 2)` (`FOOD_PER_GOLD_INTRAINING`); köylüde (71) `yemek = 0` |
| Düşülen | `bedel` birimin `cost_type`'ından, `yemek` yemekten |
| Ruh Karıştırıcı | hiçbir şey düşülmez |

### Birimin çıkışı (`IsoBuilding/OnTrainingTimer` → `pop_queue_unit`)

- Argümanlar `[qid, x, y, bina_id]`; `x = konum % EI_MAP_WIDTH`, `y = konum / EI_MAP_WIDTH` (100).
- Birim `(x, y)`'ye konur; Ruh Karıştırıcı değilse kasabanın xp'si birimin `xp`'si kadar artar.
- `amount -= 1`, `ts += T` (sıradaki, öncekinin bitişinde başlar; girişte biten birimler için istemci art arda
  `pop_queue_unit` gönderir). `amount` 0 olunca kuyruk ve binanın `bq`'su silinir.

### Kuyruktan çıkarma (`BuildingQueueData/removeUnit`, `returnCost`)

- Sondaki birim çıkar; `ts` değişmez.
- İstemcinin iadesi bedelin aynı formülüyle: `bedel` (indirimli) `cost_type`'a, `ceil(bedel × 2)` yemeğe. Köylüyü
  ayırmaz (köylü yemeksiz eğitilir ama iadede yemek verir) ve Ruh Karıştırıcı'yı ayırmaz (bedelsiz eğitilir ama iade
  edilir), KYT-04.
- Sunucu, sahibinin kararıyla (KAR-11) yalnızca eğitimde alınanı iade eder: köylüde yemek, Ruh Karıştırıcı'da hiçbir
  şey verilmez. İstemci fazlayı o oturumda gösterir; yeniden yüklenince kayıttaki değer görünür.

### Hızlandırma (`BuildingQueueData/speedUp`, `get remainingSeconds`)

- `kalan = max(0, (ts + T − şimdi) + (amount − 1) × T)`: sıradakinin kalanı ve bekleyenlerin tam süresi.
- `nakit = ceil(kalan / 3600) × 1` (`COST_SPEED_UP_UNIT_QUEUE`); nakit yetmezse istemci göndermez, sunucu da
  uygulamaz.
- Sunucu `ts = şimdi − amount × T` yapar: bütün birimler bitmiş görünür. İstemci ardından her birim için
  `pop_queue_unit` gönderir.
- Upstream'den ayrılık: upstream yalnızca sıradaki birimin kalan süresini ücretlendirir; burada istemcinin
  gösterdiği ve düştüğü bedel (bekleyenler dahil) uygulanır.

## Birlik paketleri (`buy_unit_pack`, `get_up_data.php`)

Uygulama: `oyun/komutlar.py`, `oyun/istemci.py`; testler: `tests/test_komutlar.py` (`BirlikPaketleri`),
`tests/test_http.py`. Karar: KAR-12.

### Alım (`UnitPacksManager/buyPack`)

- Argümanlar `[paket_no, adet]`. Fiyat `unit_packs[].price`'ta: `g` (açık kasabanın altını) ya da `c` (nakit).
- `toplam = int(fiyat × adet)`; `adet ≥ 8` ise `toplam = int(toplam × 0.85 + 0.5)` (`NUM_SECOND_DISCOUNT`,
  `SECOND_DISCOUNT`), değilse `adet ≥ 2` ise `toplam = int(toplam × 0.9 + 0.5)` (`NUM_FIRST_DISCOUNT`, `FIRST_DISCOUNT`).
- Kaynak yetmezse istemci göndermez; sunucu da uygulamaz.
- `max_purchable` 0 değilse toplam alım onu geçemez. Alınan adet `privateState.unitPacks[paket_no]`'da
  (`initPlayerData`).
- `price.p` (paket eşyası 1534 ile ödeme) istemcide var ama 1.4.07'nin config'inde hiçbir paket kullanmıyor; eşya
  1534 config'te yok.

### Birliklerin seçimi (`get_up_data.php`, `onGetRamdomNumbers`, `selectUnits`)

- İstemci `{n: adet × units_given}` gönderir; sunucu `data` olarak n tane `[r0, r1, r2]` döner (0 ≤ r < 1).
- Her üçlü bir birlik seçer: `r0 × 100` paket türünü (`pack_num` ağırlıkları), `r1 × 100` kategoriyi
  (`pack_category` ağırlıkları: `custom` listesi ya da birliklerin `pack_category`'si), `r2` kategoride
  `pack_chance` ağırlıklı rulet. Aynı alımda çıkmış birlik yeniden çıkarsa istemci `Math.random` ile yeniden çeker.
- Seçilen her birlik `Base/storeItem` ile depoya konur; istemci bunu `store_add_items ["[birim_id]"]` komutuyla
  bildirir. Sunucu seçimi yeniden yapmaz (istemcinin yeniden çekişi sunucuda bilinemez).

## Mezarlık (`buy_graveyard_capacity`, `reset_potions_received`)

- `buy_graveyard_capacity []` (`PopupBuyGraveyardCapacity/onBuy`): `GRAVEYARD_CAPACITY.price.c` nakit düşer,
  `privateState.graveyardCapacity += GRAVEYARD_CAPACITY.amount`, en çok `GRAVEYARD_MAX_CAPACITY`. 1.4.07'de bedel
  10.000 nakit, artış 10.000, tavan 10.000; pencerenin kapasite göstergesi zaten tavanı gösterir
  (`PopupGraveyard/get capacity`).
- `reset_potions_received []` (`PopupGraveyard/onFrameConstructed`): arkadaştan gelen iksir bildirimi gösterildi,
  `potionsReceived = 0`.
- Ölen birliklerin mezarlığa girişi yalnızca saldırı kipinde (`IsoFightingElement/kill`); GEC-05'e kaldı.

## Viral teklifler (`buy_viral_offer_friend`, `buy_viral_offer_all`, `reward_viral_offer`)

Kayıt: `privateState.viralOffers[no] = {"id", "friends": [...], "rewarded"}` (`SpecialDayOfferManager/setPlayerInfo`).

- Tek yardımcı: `buy_cost[len(friends)]` nakit, `friends`'e `-1` eklenir (`buyFriend`).
- Hepsi: `buy_all_cost[len(friends)]` nakit, `friends` `num_workers`'a tamamlanır (`buyAll`).
- Ödül: `rewarded = 1`. Birim (`unit_id`) istemcide depoya konur ve `store_add_items` ile ayrıca bildirilir
  (`giveReward` → `Base/storeItem`).
- Düğme yalnızca `starts_at < şimdi` ve `starts_at + duration − şimdi > 0` iken görünür (`checkViralButton`,
  `timeLeft`). 1.4.07'nin config'inde beş teklifin hepsinde ikisi de 0: teklifler kapalı.
