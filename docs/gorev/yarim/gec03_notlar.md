# GEC-03 kalanı: alt ajan araştırması (5.11.2026), dal gec03-kalan (f294d92: buy_powerups + KMT-07 yapıldı)

## buy_time_packet / time_ff (doğrulandı: onBuy@69-301, onUse@102-277)
- arg = paket no, globals.TIME_MACHINE[no] = {hours, price}: [0.5/2, 1/4, 4/12, 8/25, 12/40, 24/75]
- buy: canAfford(price cash) → cash -price, privateState.countTimePacket[no] += 1 (liste, sıfırla uzat; PlayerStatus/Init@484 okur)
- use: stok > 0 şartı → countTimePacket[no] -= 1; istemci reloadMap ile her şeyi sunucudan yeniden okur
- time_ff'in kaydırdığı alanlar istemcide YOK (sunucu mantığı) → ◐/? ; oyun yardım metni: kaynaklar, PvP, bölümler, görevler,
  günlük bonus, ejderha yuvası, binici akademisi. Aday alanlar: items[i][4], barracksQueues[*].ts, collectGame[*].timestamp,
  timestampLastTreasure, timestampLastTrade, timestampLastBonus, timeStampTakeCare(Monster), riderTimeStamp, tsAttacksReset,
  tsSpyingsReset, heavy siege, darts. Kalkan/firstPurchase hariç (tasarım kararı). 0/-1/1 gözcü değerler kaydırılmaz.
- Metin kaynağı: config/patch/0-language_en.json ("Dragon Nest" geçiyor)

## finish_si_recruitment (PopupRecruitment/onOpenBuilding@56-362)
- args [x, y, kasaba, 387, odul_id]; odul = game_config recruitment_prices[id] (mega_patch [49])
- units "a,b" her biri depo_ekle (storeItem 3. arg false, komutsuz); attrs.si = si[:min(len,4) - num_recruitments];
  privateState.recruitmentPrices'a odul_id (alınmışsa yok say). Bedel yok.
- Çevrimdışı ulaşılamıyor (si yalnızca showPopupSEHelpSocialItem JS ile dolar, oyun.js'te yok) ama işleyici yazılmalı.

## start_quest_new: kayitsiz (args yok, durum yok). Görev sınırı lastQuestTimes'ı sunucu hiç yazmıyor (karar sahibinde).
## reset_dragon: yalnızca AdminPanel/resetPopupDragon, o da ölü kod → kayitsiz listesine.
