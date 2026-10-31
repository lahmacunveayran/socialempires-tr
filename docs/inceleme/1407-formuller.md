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
