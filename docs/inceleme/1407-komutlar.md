# SocialEmpires1.4.07sec_fixed.swf: istemci komutları ve sunucu işleyicileri

Bu dosya `araclar/komut_imzalari.py` ile üretilir; elle düzenlenmez.

- İstemci: `SocialEmpires1.4.07sec_fixed.swf`, SHA-256 `0e4cc17893b1f266b920213d75b0c943f32c3c0d4cf9b994f6a88cab25c76a15`.
- Sunucu: `oyun/komutlar.py` (`@komut` işleyicileri, AST ile okunur).

## Özet

| Ölçü | Değer |
|---|---|
| G: istemcinin gönderdiği komut (çağrı yerinden) | 158 |
| `addCommand` çağrı yeri | 288 |
| `Constants.CMD_*` sabiti / farklı değer | 185 / 183 |
| Kodda okunan `CMD_*` sabiti | 157 |
| Komut adı çözülemeyen çağrı | 0 |
| H: sunucunun işlediği komut | 130 |
| G ∩ H | 129 |
| **G ∖ H** (eksik) | **29** |
| İmza uyumsuzluğu (sunucu, istemcinin göndermediği sırayı okuyor) | 0 |
| H ∖ G (istemcinin bu sürümde göndermediği) | 1 |

Kapılar (`docs/YOL_HARITASI_1407.md` §2.1): `|G ∖ H| = 0` ve imza uyumsuzluğu 0.

## Sürüm farkı (SocialEmpires0926bsec.swf → SocialEmpires1.4.07sec_fixed.swf)

- Yeni komut (28): `begin_attack_new`, `buy_first_purchase`, `buy_graveyard_capacity`, `buy_powerups`, `buy_shield`, `buy_unit_pack`, `buy_viral_offer_all`, `buy_viral_offer_friend`, `clean_attack_log`, `collect_game_add_item`, `collect_game_buy_all`, `collect_game_reward_given`, `collect_game_speed_up`, `collect_game_update_timestamp`, `end_attack_new`, `end_tournament_match`, `finish_si_recruitment`, `get_enemy_new`, `pop_queue_unit`, `push_queue_unit`, `reply_attack`, `reset_potions_received`, `reset_shield`, `reward_viral_offer`, `set_first_purchase_timestamp`, `speed_up_queue`, `start_quest_new`, `unqueue_unit`
- Kalkan komut (1): `exchange_cash_new`
- Argüman sayısı değişen (1):

| Komut | Eski | Yeni |
|---|---|---|
| `set_attack_team` | [2] | [3] |

## Komutlar

Durum: **var** işleyici var ve imza uyumlu; **eksik** işleyici yok; **imza** sunucu fazla sıra okuyor.
Argüman sayısı: o komutun çağrı yerlerinde görülen farklı sayılar. Sunucu sırası: işleyicinin okuduğu
en büyük argüman sırası (0'dan; -1 hiç okumaz, ? bilinemez).

| Komut | Durum | Çağrı yeri | Arg. sayısı | Sunucu işlevi | Belge | Sunucu sırası | Örnek çağrı |
|---|---|---|---|---|---|---|---|
| `accept_collect_help` | var | 1 | 5 | `accept_collect_help` (441) | 5/5 | 4 | IsoElement/collectHurryUp@372: [this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID, this.iID, ?.fbid] |
| `activate` | var | 2 | 5 | `activate` (429) | 5/5 | 4 | PopupCollect$/setShit@142: [yerel1.buildingReference.tx, yerel1.buildingReference.ty, Base.Main.townID, yerel1.buildingReference.building.id, yerel2] |
| `activate_dragon` | var | 1 | 1 | `activate_dragon` (1033) | 1/1 | 0 | PopupInactiveNest/goBuy@509: [yerel3] |
| `activate_monster` | var | 1 | 1 | `activate_monster` (1039) | 1/1 | 0 | PopupInactiveNest/goBuy@548: [yerel3] |
| `add_collectable` | var | 1 | 2 | `add_collectable` (1199) | 2/2 | 1 | CollectableManager$/addCollectible@123: [yerel1, yerel2] |
| `add_items_store` | var | 1 | 2 | `add_items_store` (325) | 2/2 | 1 | PopupArabicDeals/onBuy@270: [JSON.encode(this.currentUnits), this.cashOffer.value] |
| `add_survival_vida_extra` | var | 1 | 1 | `add_survival_vida_extra` (900) | 1/1 | 0 | PopupSurvival/buyLifeWithCash@112: [yerel2] |
| `add_unit_warehouse` | var | 1 | 4 | `add_unit_warehouse` (546) | 4/4 | 3 | IsoBuilding/pushUnitToWarehause@137: [yerel1.iLastPosSentToServerX, yerel1.iLastPosSentToServerY, Base.Main.townID, yerel1.buildingReference.building.id] |
| `admin_add_animal` | var | 1 | 2 | `admin_add_animal` (577) | 2/2 | 1 | MapInitializer$/spawnAnimals@267: [?, ?] |
| `apply_rewards_ranking` | var | 1 | 3 | `apply_rewards_ranking` (762) | 3/3 | 2 | PopupNextIslandAttack/givePrizes@243: [this.currentLevel, this.cash, JSON.encode(this.items)] |
| `assist_neighbor` | var | 1 | 3 | `assist_neighbor` (1241) | 3/3 | 2 | FauxBar2/update@347: [this.friend.pid, Base.Main.lastIdAssist, Base.Main.townID] |
| `assist_neighbor_new` | var | 1 | 3 | `assist_neighbor_new` (1251) | 3/3 | 2 | NeighbourManager$/sendCurrentNeighbourAssist@215: [yerel1, 0, JSON.encode(yerel2)] |
| `assist_receive` | var | 1 | 2 | `assist_receive` (1272) | 2/2 | 1 | IACartAlly/removeBoxThrown@105: [Base.Main.townID, yerel1.building.id] |
| `assist_send_feed` | var | 1 | 5 | `assist_send_feed` (450) | 5/5 | 4 | PopupSocialFeeds/onPost@236: [this.eBuilding.buildingReference.tx, this.eBuilding.buildingReference.ty, Base.Main.townID, this.eBuilding.buildingReference.building.id, yerel3] |
| `attack_player` | var | 3 | 1 | `attack_player` (1396) | — | -1 | Assault$/assaultEnemy@121: [yerel1] |
| `begin_attack_new` | eksik | 1 | 1 | — | — | — | PVPManager/loadMap@51: [Base.Main.clientTimestamp()] |
| `buy` | var | 14 | 8 | `buy` (239) | 8/8 | 6 | IsoElement/tick@1324: [yerel6, this.buildingReference.tx, this.buildingReference.ty, 1, Base.Main.townID, 0, 1, this.buildingReference.building.type] |
| `buy_attacks_pack` | var | 1 | ? | `buy_attacks_pack` (1324) | — | -1 | PopUpBuyAssault/onBuyAttack@64: [''] |
| `buy_cash` | var | 2 | 5 | `buy_cash` (586) | 5/5 | 4 | PopupHeroes/onBuyItem@253: [yerel4.building.id, yerel4.tx, yerel4.ty, yerel4.frame, Base.Main.townID] |
| `buy_first_purchase` | var | 2 | 0 | `buy_first_purchase` (821) | 0/0 | -1 | AdminPanel/giveFP@35: [] |
| `buy_graveyard_capacity` | eksik | 1 | 0 | — | — | — | PopupBuyGraveyardCapacity/onBuy@88: [] |
| `buy_magic` | var | 2 | 3 | `buy_magic` (959) | 3/3 | 2 | SelectedMagic/onBuyWithGold@100: [this.spell.id, Base.Main.townID, 0] |
| `buy_mana_new` | var | 2 | 2 | `buy_mana_new` (948) | 2/2 | 1 | PopupBuyMana/onBuyWithCash@147: [Base.Main.townID, 1] |
| `buy_map` | var | 2 | 4 | `buy_map` (371) | 4/4 | 3 | PopupRaceSelector/onUnlockCash@219: [1, 1, this.sRace, Base.Main.townID] |
| `buy_monster_step_cash` | var | 1 | 1 | `buy_monster_step_cash` (1095) | 1/1 | 0 | PopupMonstersNest/clickGetnow@124: [yerel2] |
| `buy_offer_pack` | var | 2 | 2, 3 | `buy_offer_pack` (774) | 2/3 | ? | PromotionPacks$/buyPack@599: [Base.Main.townID, yerel1, yerel6] |
| `buy_powerups` | eksik | 1 | 1 | — | — | — | PopupSoulMixer/sendPowerUps@76: [yerel2] |
| `buy_pvp_territory` | var | 1 | 1 | `buy_pvp_territory` (1344) | 1/1 | 0 | PopupBuyTerritoryPvp/onBuy@98: [this.position] |
| `buy_shield` | eksik | 1 | 1 | — | — | — | ShieldManager/buyShield@297: [yerel2.id] |
| `buy_si_help` | var | 4 | 4, 5 | `buy_si_help` (1292) | 4/5 | 4 | Base/countAllBuildings@686: [yerel6.tx, yerel6.ty, Base.Main.townID, yerel2, 1] |
| `buy_spyings_pack` | var | 1 | ? | `buy_spyings_pack` (1330) | — | -1 | PopUpBuyAssault/onBuyAttack@198: [''] |
| `buy_step_cash` | var | 1 | 1 | `buy_step_cash` (1088) | 1/1 | 0 | PopupDragons/clickGetnow@116: [yerel2] |
| `buy_stored_item_cash` | var | 1 | 3 | `buy_stored_item_cash` (318) | 3/3 | 2 | PopupAllUnits/buyUnit@191: [Base.Main.townID, yerel2.id, this.tooltip.cost.value] |
| `buy_super_offer_pack` | var | 1 | 4 | `buy_super_offer_pack` (795) | 6/6 | 3 | PromotionPacks$/buySuperPack@1110: [Base.Main.townID, yerel1, yerel7.join(','), yerel3] |
| `buy_survival_map` | var | 1 | 2 | `buy_survival_map` (908) | 2/2 | 1 | PopupSurvival/onUnlock@159: [yerel2, yerel4] |
| `buy_temple_step_cash` | var | 1 | 1 | `buy_temple_step_cash` (1143) | 1/1 | 0 | PopupBahamutSupremeInvocationTemple$/clickGetnow@113: [CASH_PRICE_TIME.value] |
| `buy_time_packet` | eksik | 1 | 1 | — | — | — | PopupSelectTime/onBuy@294: [yerel4] |
| `buy_unit_pack` | eksik | 1 | 2 | — | — | — | UnitPacksManager/buyPack@432: [yerel1, yerel2] |
| `buy_viral_offer_all` | eksik | 1 | 1 | — | — | — | SpecialDayOfferManager/buyAll@38: [yerel1] |
| `buy_viral_offer_friend` | eksik | 2 | 1 | — | — | — | SpecialDayOfferManager/buyFriend@48: [yerel1] |
| `buy_warehouse_capacity_single` | var | 1 | 1 | `buy_warehouse_capacity_single` (1336) | 1/1 | 0 | PopupUnitWarehouse/onBuyMoreSlots@228: [Base.Main.townID] |
| `clean_attack_log` | eksik | 1 | 0 | — | — | — | AdminPanel/cleanAttackLog@35: [] |
| `clean_attacks` | var | 1 | 0 | `clean_attacks` (1406) | 0/0 | -1 | Assault$/cleanAssaults@35: [] |
| `clean_received_assists` | var | 1 | 2 | `clean_received_assists` (1283) | 2/2 | 1 | NeighbourManager$/removeNeighbourAssist@36: [yerel1, Base.Main.townID] |
| `clear_message` | var | 1 | 0 | `clear_message` (694) | — | -1 | yontem1486@19: [] |
| `clear_tiles_area` | var | 1 | 6 | `kayitsiz` (230) | — | -1 | MapInitializer$/cleanAllMapTiles@309: [Base.Main.townID, 0, 0, decrement(Config.EI_MAP_WIDTH), decrement(Config.EI_MAP_HEIGHT), ''] |
| `collect_game_add_item` | eksik | 1 | 2 | — | — | — | CollectGameManager/addItem@109: [yerel4.id, 1] |
| `collect_game_buy_all` | eksik | 1 | 1 | — | — | — | CollectGameManager/buyAll@67: [1] |
| `collect_game_reward_given` | eksik | 1 | 1 | — | — | — | CollectGameManager/giveReward@48: [yerel1.reward.id] |
| `collect_game_speed_up` | eksik | 1 | 1 | — | — | — | CollectGameManager/buySpeedup@88: [yerel1.id] |
| `collect_game_update_timestamp` | eksik | 1 | 1 | — | — | — | CollectGameManager/collectItem@66: [yerel2.id] |
| `collect_new` | var | 4 | 4, 7 | `collect_new` (416) | 4/5 | 6 | IsoElement/tick@2192: [yerel16, yerel17, Base.Main.townID, this.buildingReference.building.id, <IsoBuilding>.IsoBuilding(this).iUnitsContainedWhenHarvested, Base.Iso.getResourceMultiplier(this), 0] |
| `collect_treasure` | var | 2 | 6 | `collect_treasure` (754) | 6/6 | 5 | MapInitializer$/setCorrectQuest@274: [0, 0, Base.Main.currentQuestId, 0, 0, Base.Main.townID] |
| `comeback_reward` | var | 1 | 3 | `comeback_reward` (747) | 3/3 | 2 | ComebackBonusPopUp/_collectClickHandler@466: [yerel3.type, yerel3.value, this.day] |
| `complete_mission` | var | 2 | 1, 2 | `complete_mission` (639) | 2/2 | 1 | AbstractGoal/checkComplete@198: [this.id, 0] |
| `complete_tutorial` | var | 3 | 1 | `complete_tutorial` (608) | 1/1 | 0 | Base/completarTutorial@60: [?] |
| `cross_promotion_finished` | var | 1 | 1 | `cross_promotion_finished` (710) | 1/1 | 0 | PopupCrossPromotion/_onGetReward@147: [yerel2] |
| `darts_new_free` | var | 1 | 0 | `darts_new_free` (1168) | — | -1 | PopupDarts$/newFree@56: [] |
| `darts_reset` | var | 1 | 1 | `darts_reset` (1159) | 1/1 | 0 | PopupDarts$/resetDartGame@137: [Base.Player.dartsRandomSeed] |
| `darts_shoot_balloon` | var | 1 | 3 | `darts_shoot_balloon` (1173) | 3/3 | 2 | PopupDarts/hitBalloon@334: [yerel2, 0, 1] |
| `desactivate_dragon` | var | 1 | 0 | `desactivate_dragon` (1045) | — | -1 | PopupDragons/desactivateNest@35: [] |
| `desactivate_monster` | var | 1 | 0 | `desactivate_monster` (1051) | — | -1 | PopupMonstersNest/desactivateNest@35: [] |
| `end_attack` | var | 2 | 1, 2 | `end_attack` (1401) | — | -1 | Assault$/sendAssaultResults@343: [JSON.encode({'attacker': {'name': Base.Player.playerInfo.name, 'level': Base.Player.iLevel, 'user_id': Base.Commands.sessionID, 'world_id': Base.Player.worldId, 'map': Base.Main.townID, 'race': Base.Player.currentRace}, 'victim': opponentPlayer, 'resources': {'g': 0, 'w': 0, 's': 0, 'f': 0, 'x': 0}, 'resources_victim': {'g': 0}, 'attacker_units': arPlayerUnits, 'victim_units': arEnemyUnits, 'win': 1, 'duration': Math.round(((tEndAssault - tIniAssault) / 1000)), 'voluntary_end': 1, 'townhall_gold': townHallGold, 'honor': 0})] |
| `end_attack_new` | eksik | 1 | 14 | — | — | — | PVPManager/sendEnd@463: [Base.PVP.stolenGold, Base.PVP.stolenFood, Base.PVP.stolenWood, Base.PVP.stolenStone, yerel2.user_id, PvpPlayerManager.me.player.name, PvpPlayerManager.me.player.level, Base.Main.clientTimestamp(), Base.Commands.sessionID, 1, yerel4, yerel5, (this.percentage * 100), Assault.iXPGained] |
| `end_quest` | var | 17 | 1 | `end_quest` (854) | 1/1 | 0 | QuestBossGolem/sendResults@295: [JSON.encode({'map': Base.Main.townID, 'resources': {'g': Quest.iGoldGained, 'x': Quest.iXPGained}, 'units': Quest.arPlayerUnits, 'win': 1, 'duration': Math.round(((Quest.tEndAssault - Quest.tIniAssault) / 1000)), 'voluntary_end': 1, 'quest_id': Constants.QUEST_BOSS_GOLEM, 'item_rewards': {537: 1}, 'difficulty': difficulty, 'set_unlocked_index': 1})] |
| `end_survival` | var | 1 | 3 | `end_survival` (889) | 3/3 | 2 | PopupSurvivalResults/givePrizes@215: [this.currentMap, this.time, JSON.encode(this.items)] |
| `end_tournament_match` | eksik | 1 | 1 | — | — | — | TournamentManager$/shutMatch@192: [1] |
| `expand` | var | 1 | 3 | `expand` (349) | 3/3 | 2 | Base/purchaseLand@606: [yerel1, 'cash', this.townID] |
| `fast_forward` | var | 3 | 1 | `kayitsiz` (230) | — | -1 | AdminPanel/fastForward@403: [yerel5] |
| `finish_collection` | var | 3 | 1, 3 | `finish_collection` (1215) | 1/2 | 2 | AdminPanel/completeHeartCollection@58: [23] |
| `finish_dragon_help` | var | 1 | 1 | `finish_dragon_help` (1102) | — | -1 | PopupDragons/closeHireResults@196: [JSON.encode(yerel2)] |
| `finish_si` | var | 4 | 4, 7 | `finish_si` (1308) | 4/4 | 3 | IsoElement/collect@503: [this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID, this.iID] |
| `finish_si_recruitment` | eksik | 1 | 5 | — | — | — | PopupRecruitment/onOpenBuilding@110: [this.eBuilding.buildingReference.tx, this.eBuilding.buildingReference.ty, Base.Main.townID, this.eBuilding.iID, yerel3.id] |
| `game_status` | var | 5 | 1, 3 | `kayitsiz` (230) | — | -1 | Base/init@1382: ['MapLoaded', 'INIT', this.spRefCat] |
| `get_enemy_new` | eksik | 1 | 2 | — | — | — | PVPManager/searchEnemy@44: [yerel1, this.searchesBeforeAttack] |
| `gold_statue_conversion` | var | 1 | 1 | `kayitsiz` (230) | — | -1 | IsoGoldenDynastyDragon/convertToGoldOnce@95: [this.GOLD_PER_STATUE] |
| `graveyard_buy_potions` | var | 1 | 0 | `graveyard_buy_potions` (983) | — | -1 | PopupBuyGraveyardPotion/onBuy@84: [] |
| `increase_population` | var | 1 | 1 | `increase_population` (597) | 1/1 | 0 | PopupRecruitmentPopulation/onRecruitComplete@102: [Base.Main.townID] |
| `kill` | var | 3 | 5 | `kill` (281) | 5/5 | 3 | IsoElement/collect@3675: [this.buildingReference.tx, this.buildingReference.ty, this.buildingReference.building.id, Base.Main.townID, this.buildingReference.building.type] |
| `load_map` | var | 5 | 1 | `kayitsiz` (230) | — | -1 | AdminPanel/loadMap@58: [yerel1[1]] |
| `modify_position_univers` | var | 1 | 2 | `modify_position_univers` (1390) | 2/2 | 0 | ExplorationsManager/evalUserPositionNotConquered@376: [yerel6, yerel5] |
| `move` | var | 5 | 8 | `move` (250) | 8/8 | 6 | Base/mouseUsed@2077: [this.selectedItem.otx, this.selectedItem.oty, this.selectedItem.building.id, <int>.int((yerel1 % Config.EI_MAP_WIDTH)), <int>.int((yerel1 / Config.EI_MAP_WIDTH)), this.selectedItem.frame, this.townID, 'mouseUsed'] |
| `name_map` | var | 1 | 2 | `name_map` (365) | 2/2 | 1 | EnterNamePopUp/setTownName@60: [Base.Main.townID, inputText.text] |
| `next_dragon` | var | 2 | 1 | `next_dragon` (1075) | — | -1 | PopupDragons/evalStepsDragon@132: ['0'] |
| `next_monster` | var | 2 | 1 | `next_monster` (1081) | — | -1 | PopupMonstersNest/evalStepsMonster@132: ['0'] |
| `next_monster_step` | var | 1 | 1 | `next_monster_step` (1066) | 1/1 | 0 | PopupMonstersNest/clickAction@97: [this._stepCash.value] |
| `next_step` | var | 2 | 1 | `next_step` (1057) | 1/1 | 0 | MapInitializer$/spawnDragonNest@190: ['0'] |
| `next_temple_step` | var | 1 | 2 | `next_temple_step` (1131) | 2/2 | 1 | PopupBahamutSupremeInvocationTemple/doAction@1139: [JSON.encode({'collection': this._configTemple[this.currentInvocationStep.value]['data']}), this.currentInvocationStep.value] |
| `orient` | var | 1 | 4 | `orient` (258) | 4/4 | 3 | IsoElement/changeDirection@136: [this.buildingReference.tx, this.buildingReference.ty, this.buildingReference.frame, Base.Main.townID] |
| `perform_city_quest` | var | 2 | 4 | `kayitsiz` (230) | — | -1 | IsoElement/collect@4198: [this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID, this.buildingReference.loaded.quest_id] |
| `ping` | var | 1 | 0 | `kayitsiz` (230) | — | -1 | yontem14@70: [] |
| `place_gift` | var | 1 | 5 | `place_gift` (302) | 5/5 | 4 | Base/sendPlaceItemCmd@262: [this.selectedBuilding.id, (yerel1 % Config.EI_MAP_WIDTH), <int>.int((yerel1 / Config.EI_MAP_WIDTH)), this.selectedBuilding.frame, this.townID] |
| `place_iphone` | var | 1 | 5 | `place_iphone` (1363) | 5/5 | 4 | Base/sendPlaceItemCmd@345: [this.selectedBuilding.id, (yerel1 % Config.EI_MAP_WIDTH), <int>.int((yerel1 / Config.EI_MAP_WIDTH)), this.selectedBuilding.frame, this.townID] |
| `place_stored_item` | var | 1 | 5 | `place_gift` (302) | 5/5 | 4 | Base/sendPlaceItemCmd@405: [this.selectedBuilding.id, (yerel1 % Config.EI_MAP_WIDTH), <int>.int((yerel1 / Config.EI_MAP_WIDTH)), this.selectedBuilding.frame, this.townID] |
| `place_warehoused_item` | var | 1 | 5 | `place_warehoused_item` (557) | 5/5 | 4 | PopupUnitWarehouse/onUseClick@391: [yerel2.sd.id, yerel4.tx, yerel4.ty, 0, Base.Main.townID] |
| `pop_queue_unit` | eksik | 1 | 4 | — | — | — | IsoBuilding/OnTrainingTimer@562: [buildingReference.loaded.attrs['bq'], (yerel3 % Config.EI_MAP_WIDTH), <int>.int((yerel3 / Config.EI_MAP_WIDTH)), iID] |
| `pop_sell` | var | 1 | 5 | `pop_sell` (529) | 5/5 | 4 | IsoBuilding/PopSell@197: [this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID, this.buildingReference.building.id, yerel1.buildingReference.building.id] |
| `pop_unit` | var | 4 | 4, 7 | `pop_unit` (517) | 4/5 | ? | IsoBuilding/PopUnit@304: [this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID, yerel1.buildingReference.building.id, yerel5.tx, yerel5.ty, yerel1.buildingReference.frame] |
| `push_queue_unit` | eksik | 1 | 6 | — | — | — | BuildingQueueManager/addUnit@259: [yerel5.building.buildingReference.tx, yerel5.building.buildingReference.ty, yerel5.building.iID, yerel2.id, <parseInt>.parseInt(yerel5.building.buildingReference.loaded.attrs['bq']), 1] |
| `push_unit` | var | 1 | 6 | `push_unit` (503) | 6/6 | 5 | IsoBuilding/PushUnit@201: [yerel1.iLastPosSentToServerX, yerel1.iLastPosSentToServerY, yerel1.buildingReference.building.id, this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID] |
| `put_graveyard` | var | 1 | 1 | `put_graveyard` (999) | 1/1 | 0 | PhoenixEggDelegate/onPhoenixEggDie@159: [this.phoenixUnit] |
| `reply_attack` | eksik | 1 | 1 | — | — | — | PVPManager/loadMap@137: [yerel3] |
| `reset` | var | 1 | 0 | `kayitsiz` (230) | — | -1 | AdminPanel/onReset@34: [] |
| `reset_completed_missions` | var | 1 | 0 | `reset_completed_missions` (660) | — | -1 | GoalsManager/resetGoals@123: [] |
| `reset_dragon` | eksik | 1 | 1 | — | — | — | AdminPanel/resetPopupDragon@35: [0] |
| `reset_heavy_siege` | var | 1 | 2 | `reset_heavy_siege` (920) | 2/2 | 1 | MapInitializer$/resetHeavySiege@424: [1, yerel4] |
| `reset_position_univers` | var | 1 | 0 | `kayitsiz` (230) | — | -1 | ExplorationsManager/doRelocate@48: [] |
| `reset_potions_received` | eksik | 1 | 0 | — | — | — | PopupGraveyard/onFrameConstructed@123: [] |
| `reset_shield` | eksik | 3 | 0 | — | — | — | AdminPanel/resetShieldState@34: [] |
| `reset_temple` | var | 2 | 0 | `reset_temple` (1150) | — | -1 | AdminPanel/resetBahamutTemple@85: [] |
| `reset_warehouse` | var | 2 | 1 | `reset_warehouse` (568) | 1/1 | 0 | Base/storeItem@453: [Base.Main.townID] |
| `reset_world_change` | var | 1 | 0 | `reset_world_change` (699) | — | -1 | ExplorationsManager/onContinentLoaded@431: [] |
| `resurrect_hero` | var | 2 | 4, 5 | `resurrect_hero` (1005) | 4/5 | 4 | PopupGraveyard/onBuyItem@395: [yerel5.building.id, yerel7.tx, yerel7.ty, Base.Main.townID, '1'] |
| `reward_mission` | var | 2 | 2 | `reward_mission` (647) | 2/2 | 1 | AbstractGoal/rewardMission@104: [Base.Main.townID, this.id] |
| `reward_viral_offer` | eksik | 2 | 5 | — | — | — | SpecialDayOfferManager/giveReward@223: [yerel1, yerel3.tx, yerel3.ty, Constants.ORIENTATION_DOWN_RIGHT, Base.Main.townID] |
| `rider_buy_step_cash` | var | 1 | 1 | `rider_buy_step_cash` (1107) | 1/1 | 0 | PopupDragonRiderTraining/clickGetNow@83: [this.cashRider] |
| `rider_next_step` | var | 1 | 1 | `rider_next_step` (1114) | — | -1 | PopupDragonRiderTraining/onGameSuccess@72: ['1'] |
| `rider_select` | var | 2 | 1 | `rider_select` (1121) | 1/1 | 0 | PopupDragonRiderTraining/onTrainClick@112: ['0'] |
| `rt_level_up` | var | 1 | 1 | `rt_level_up` (616) | 1/1 | 0 | PlayerStatus/checkForLevelUp@161: [this.iLevel] |
| `rt_publish_achievement_unit` | var | 1 | 1 | `kayitsiz` (230) | — | -1 | IsoEngine/addElement@1813: [yerel1.buildingReference.building.id] |
| `rt_publish_score` | var | 1 | 1 | `rt_publish_score` (627) | 1/1 | 0 | Base/UpdateGame3@654: [Base.Player.iExperience] |
| `save_map` | var | 5 | 1 | `kayitsiz` (230) | — | -1 | AdminPanel/saveMap@58: [yerel1[1]] |
| `sell` | var | 18 | 6, 7 | `sell` (266) | 6/7 | 6 | Base/removeElement@181: [this.buildingArray[yerel4].tx, this.buildingArray[yerel4].ty, this.buildingArray[yerel4].building.id, this.townID, 0, yerel3] |
| `sell_gift` | var | 3 | 2 | `sell_gift` (310) | 2/2 | 1 | AdminPanel/removeStoreItems@150: [yerel4.id, Base.Main.townID] |
| `sell_iphone_item` | var | 2 | 2 | `sell_iphone_item` (1370) | 2/2 | 1 | AdminPanel/removeStoreItems@214: [yerel4.id, Base.Main.townID] |
| `sell_stored_item` | var | 3 | 2 | `sell_gift` (310) | 2/2 | 1 | AdminPanel/removeStoreItems@251: [yerel4.id, Base.Main.townID] |
| `set_attack_team` | var | 1 | 3 | `set_attack_team` (1381) | 2/2 | 1 | SelectionTeamWindow/saveTeamOnServer@152: [this.currentSelectionMode.name, JSON.encode(yerel1), this.formation] |
| `set_fake_neighbors` | var | 1 | 3 | `set_fake_neighbors` (704) | 3/3 | -1 | Base/testABFakeNeighbours@272: [yerel1[0], yerel1[1], yerel1[2]] |
| `set_first_purchase_timestamp` | var | 3 | 0, 1 | `set_first_purchase_timestamp` (811) | 0/0 | ? | AdminPanel/setFP@37: [0] |
| `set_help_map` | var | 4 | 1 | `set_help_map` (672) | 1/1 | 0 | PopupHelpIsland/<kurucu>@542: [this.popup_type] |
| `set_info_showed` | var | 1 | 2 | `set_info_showed` (682) | 2/2 | 1 | PlayerStatus/setInfoShowed@49: [yerel1, yerel2] |
| `set_quest_var` | var | 2 | 3 | `set_quest_var` (870) | 3/3 | 2 | CustomQuestNew$/cleanQuestStatus@135: [Base.Main.townID, yerel2, JSON.encode({'spawned': False, 'activators': [], 'boss': [], 'treasure': []}[yerel2])] |
| `set_resource_allies` | var | 3 | 5 | `set_resource_allies` (458) | 5/5 | 4 | IsoElement/collect@563: [Base.Main.resourceAlliesMarket, this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID, this.iID] |
| `set_skin` | var | 2 | 2 | `set_skin` (391) | 2/2 | 1 | PopupWeather/onApply@130: [Base.Main.townID, <String>.String(yerel2)] |
| `set_strategy` | var | 1 | 1 | `set_strategy` (666) | 1/1 | 0 | PopUpBattleOptions/closeWindow@90: [this.defensiveStrategy] |
| `set_variables` | var | 7 | 8 | `kayitsiz` (230) | — | -1 | AdminPanel/giveResources@475: [Base.Player.iGold, Base.Player.iCash, Base.Player.iExperience, Base.Player.iLevel, Base.Player.iStone, Base.Player.iWood, Base.Player.iFood, Base.Main.townID] |
| `speed_up_queue` | eksik | 1 | 1 | — | — | — | BuildingQueueData/speedUp@115: [this._building.buildingReference.loaded.attrs['bq']] |
| `spy_player` | var | 1 | 1 | `kayitsiz` (230) | — | -1 | ExplorationsManager/doSpy@68: [this.current_player.user_id] |
| `start_heavy_siege` | var | 1 | 0 | `start_heavy_siege` (915) | — | -1 | MapInitializer$/attacksInit@149: [] |
| `start_quest` | var | 1 | 2 | `kayitsiz` (230) | — | -1 | Quest$/start@58: [idQuest, Base.Main.townID] |
| `start_quest_new` | eksik | 1 | 0 | — | — | — | Quest$/start@81: [] |
| `start_survival` | var | 1 | 0 | `start_survival` (876) | — | -1 | PopupLoadingSurvival/startSurvival@40: [] |
| `store_add_items` | var | 1 | 1 | `store_add_items` (333) | 1/1 | 0 | Base/storeItem@194: [JSON.encode([yerel1.building.id])] |
| `store_item` | var | 1 | 4 | `store_item` (291) | 4/4 | 3 | Base/storeItem@305: [yerel1.tx, yerel1.ty, this.townID, yerel1.building.id] |
| `store_item_frombug` | var | 1 | 4 | `store_item` (291) | 4/4 | 3 | Base/storeItem@244: [yerel1.tx, yerel1.ty, this.townID, yerel1.building.id] |
| `system_set_count_hack` | var | 1 | 0 | `kayitsiz` (230) | — | -1 | Base/UpdateGame@251: [] |
| `time_ff` | eksik | 1 | 1 | — | — | — | PopupSelectTime/onUse@209: [yerel4] |
| `tournament_refund_resources` | var | 1 | 2 | `tournament_refund_resources` (938) | 2/2 | 1 | TournamentManager$/evalRefundTournament@268: [yerel4, yerel5] |
| `tournament_substract_resources` | var | 4 | 4 | `tournament_substract_resources` (932) | 4/4 | 1 | TournamentManager$/createTournament@154: ['g', yerel3['gold'], yerel1, 1] |
| `trade_resource_b` | var | 1 | 4 | `trade_resource_b` (469) | 4/4 | 3 | ButtonMarket/onTrade@531: [Base.Main.townID, this.resource, 1, this.amount] |
| `unit_collections_completed` | var | 1 | 1 | `unit_collections_completed` (1189) | 1/1 | 0 | PopupAllUnits/getCollectionReward@222: [yerel3] |
| `unlock_building` | var | 1 | 1 | `unlock_building` (404) | 1/1 | 0 | PopupUnlockBuilding/onYes@142: [<String>.String(this.sd.id)] |
| `unlock_skin` | var | 1 | 1 | `unlock_skin` (397) | 1/1 | 0 | PopupWeather/onUnlock@150: [<String>.String(yerel2)] |
| `unqueue_unit` | eksik | 1 | 2 | — | — | — | BuildingQueueData/removeUnit@138: [this._building.buildingReference.loaded.attrs['bq'], this._building.iID] |
| `upgrade` | var | 1 | 3 | `upgrade` (340) | 3/3 | 2 | IsoInteractiveElement/doUpgrade@94: [this.buildingReference.tx, this.buildingReference.ty, Base.Main.townID] |
| `use_magic` | var | 1 | 1 | `use_magic` (975) | 1/1 | 0 | MagicManager/castMagic@289: [yerel4.id] |
| `weekly_reward` | var | 1 | 2 | `weekly_reward` (740) | 2/2 | 1 | MondayBonusPopUp/_collectClickHandler@491: [yerel3.type, yerel3.value] |
| `win_bonus` | var | 1 | 5 | `win_bonus` (720) | 5/5 | 4 | PopupNewDaily/onGetPrize@676: [this.pastaGanada, Base.Main.townID, this.heroID.value, (yerel5 + 1), this.cashWon] |

## H ∖ G: sunucuda olup bu istemcinin göndermediği

`exchange_cash_new`

## Kodda okunmayan `CMD_*` sabitleri (28)

`CMD_ALLY_ASSIST` = `ally_assist`, `CMD_BAHAMUT_SUPREME_INVOCATION_TEMPLE_ADD_UNIT` = `add_unit_temple`, `CMD_BUY_ATTACKS` = `buy_attacks`, `CMD_BUY_OFFER` = `buy_offer`, `CMD_BUY_SPYINGS` = `buy_spyings`, `CMD_BUY_WAREHOUSE_CAPACITY` = `buy_warehouse_capacity`, `CMD_BUY_WONDER_FRIENDS` = `buy_wonder_friends`, `CMD_DEFAULT_TOWN` = `set_default_town`, `CMD_END_SURVIVAL` = `end_survival`, `CMD_EXCHANGE_CASH` = `exchange_cash_new`, `CMD_EXPLORE` = `explore`, `CMD_GIVE_BONUS_REWARD` = `give_bonus_reward`, `CMD_HIRE_WORKER` = `hire_worker`, `CMD_KOMPU_HURRY_UP` = `kompu_hurry_up`, `CMD_PAY_WONDER` = `pay_wonder`, `CMD_PVP_BUY_ISLAND` = `buy_pvp_island`, `CMD_REPORT_BUG` = `report_bug`, `CMD_RESET_DRAGON` = `reset_dragon`, `CMD_RESET_MONSTER` = `reset_monster`, `CMD_RESET_RIDER` = `rider_reset`, `CMD_SET_DEFAULT_MAP` = `set_default_map`, `CMD_SET_IPHONE_BOX_POPUP_SHOWED` = `set_iphone_box_popup_showed`, `CMD_SET_RESOURCES_TRADED` = `set_resources_traded`, `CMD_START_CAMPAIGN` = `start_campaign`, `CMD_TIME_MACHINE_FF` = `time_ff`, `CMD_TOURNAMENT_WIN_REWARD` = `win_reward_tournament`, `CMD_UNIT_COLLECTION_REMOVE` = `remove_unit_collection`, `CMD_WIN_TROPHY` = `win_trophy`
