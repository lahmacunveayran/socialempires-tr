# Bağımsız denetim (2): Social Empires Türkçe ile AcidCaos/socialemperors'ın yeni işi

Tarih: 30 Ekim 2026 · Yöntem: yalnızca statik okuma ve bayt ayrıştırma · Denetçi: bağımsız (öteki denetçinin işini görmedi)

**İşaretler:**

- ✔ Okunarak ya da kendi betiğimle ölçülerek doğrulandı.
- ◐ Dolaylı kanıt: kod okuması ya da commit mesajı. Çalıştırılarak görülmedi.
- ? Doğrulanmadı ya da tahmin.

**Kurallar:**

- Upstream'in hiçbir kodu çalıştırılmadı.
- Bizim depoda hiçbir şey değiştirilmedi.
- Upstream dosyalarını okuyan Python betikleri `-I` ile çalıştırıldı.
- SWF'ler bizim `oyun/swf_yama.py` okuyucularıyla (`_govde`, `_etiketler`, `_u30_oku`, `_metin_konumu`) ayrıştırıldı.
- Bunların üstüne kendi tam ABC (AVM2) ayrıştırıcımı yazdım: sabit havuzu, sınıflar, özellikler ve yöntem gövdeleri ile işlem kodu yürütme.

Betikler ve ara çıktılar `(oturum çalışma klasörü)/denetim2/` altında:

- `koken.py`: köken eşleme.
- `swfanaliz.py`, `abc2.py`: SWF ve ABC ayrıştırıcıları.
- `kronoloji.py`, `ozellik_zaman.py`: sürüm kronolojisi.
- `fark2.py`, `fixfark.py`: istemci farkları.
- `komut2.py`: komut kapsaması.
- `kapsama.py`: çeviri anahtarı kapsaması.
- `ogeler.py`, `idsabit.py`, `tip.py`: veri ve kayıt karşılaştırmaları.

İndirilen SWF'ler ayrı bir klasörde duruyor: `(oturum çalışma klasörü)/indirilen_swf/`.

---

## 0. Kısa cevap

1. **"Dosyalarımız eski mi?" Yarı yarıya. Ve öncül yanıltıcı.**
   - Upstream'in varsayılan dalı `main` ile son sürümü `0.04a`, 26 Eylül 2025'ten beri **hiç değişmedi**. Bizim çatal tam bu anlık görüntüden türedi (✔).
   - "Yeni iş" `nerroth-rewrite` adlı **yayımlanmamış bir dalda**: 0.04a'dan sonra 429 commit var, sonuncusu 16 Ağustos 2026. 426'sı Nerroth'un.
   - Bu iş ağırlıkla **başka bir oyun istemcisini (1.4.07)** çalıştırmaya yönelik.
   - Bizim istemcimiz `SocialEmpires0926bsec.swf`, upstream'dekiyle **bayt bayt aynı** ve upstream onu hâlâ seçenek olarak sunuyor (✔).
   - "Eski" olan şey dosyalarımız değil, **seçtiğimiz istemci sürümü**:
     - 0.9.26b, 5 Aralık 2012'de derlenmiş.
     - 1.4.07, 31 Ocak 2014'te derlenmiş.
     - Arada 58 derleme ve yaklaşık 14 aylık geliştirme var (✔, SWF'lerin içindeki ProductInfo tarihleri).
2. **Fark ne?**
   - 1.4.07 istemcisinde 570 yeni sınıf var; 145 sınıf kalkmış. Yeni sistemler:
     - veriyle sürülen hedef sistemi (GoalsManager, 58 sınıf)
     - Soul Mixer
     - kalkanlı yeni PvP
     - birim paketleri
     - Forge Island (CollectGame)
     - yeni günlük ödül
     - özel gün teklifleri
     - saldırı günlüğü
     - 51 özel ejderha ya da devasa birim sınıfı
   - Upstream sunucusu bunlar için 29 yeni komut ve 7 yeni uç nokta ekledi.
   - Öte yandan upstream'de bizim yaptıklarımız yok: Türkçe, Android, testler, sağlam kayıt, turnuvalar, dünya haritası, bot dünyası. Turnuva ve dünya uç noktaları upstream'de **"uygulanmadı" saplamaları** olarak duruyor (✔).
3. **Ne yapmalı?**
   - Önerim **(a) 0926'da kalmak**, birkaç somut düzeltmeyle birlikte. Yanına seçici bir **(d)** konabilir: Türkçeleştirme araçları ve kayıt sağlamlığı upstream'e katkı olarak gönderilir.
   - **(b) "yalnızca hedef ve etkinlik sistemini taşımak" 0926'da teknik olarak mümkün değil.** Bu sistemlerin mantığı istemcinin içinde. 0926'da görevler istemci koduna gömülü.
   - **(c) tam göç** büyük bir iş (haftalar ya da aylar, ?). Riski yüksek: upstream'in kendisi stok 1.4.07'yi çevrimdışı çalıştırmak için istemcinin baytlarını yamamak zorunda kaldı.

---

## 1. Köken ve sürüm soyu

### 1.1 Upstream'in durumu (canlı, 30 Ekim 2026)

- `git ls-remote origin`: `HEAD -> refs/heads/main = f642e0b` (✔).
  - Etiketler `0.04` ve `0.04a` aynı commit: f642e0b, 26 Eylül 2025 (✔).
  - 0.04a'dan sonra etiket ya da sürüm yok (✔).
  - `nerroth-rewrite` dalının README'si hâlâ "Latest Release: alpha 0.04a" diyor (✔).
- Dallar (✔):

  | Dal | Uç | Tarih | 0.04a'dan beri commit |
  | --- | --- | --- | --- |
  | `main` | f642e0b | 26.09.2025 | 0 |
  | `nerroth` | 03106b7 | 24.10.2025 | 292 |
  | `nerroth-rewrite` | 54df29e | 16.08.2026 | 429 (`nerroth` bunun atasıdır) |

- Yazarlar: 426 Nerroth, 3 Neutral (✔).
- Aylara göre dağılım (✔):

  | Ay | Commit |
  | --- | --- |
  | 2025-10 | 290 |
  | 2025-11 – 2026-04 | 29 |
  | 2026-05 | 31 |
  | 2026-07 | 29 |
  | 2026-08 | 3 |

  Yani yoğun dönem Ekim 2025'te; 2026'da seyrek ama süren bir çalışma var.
- `version.py` içinde `version_name = "nerroth rewrite - beyond 0.04a"` yazıyor (✔).
- Açık ya da kapalı PR'lar #40–#48 (2025-11 … 2026-10) ne `main`'de ne `nerroth-rewrite`'ta (✔, `merge-base --is-ancestor`).
  - #48 "Kamel" (14 Ekim 2026) `nerroth-rewrite` üstüne kurulu. İçeriği: "Safe saves: atomic writes, backups, lock" ve istemci-sunucu uyumsuzluğu düzeltmeleri.
  - PR'ların durumu GitHub API'ye erişim olmadığı için doğrulanamadı (?).

### 1.2 Bizim çatal hangi anlık görüntüden?

İçerik karşılaştırması yaptım: bizim dosyaların git blob özetlerini, upstream'in tüm dallarının ve etiketlerinin her commit ağacıyla eşledim (`koken.py`, ✔).

- `config/patch/unit_collections.json` (ilk görünüşü 42c07c3, 26.09.2025) ve `viral_icons.json` (0b65a50) bizde **aynen** var. Bu iki dosya yalnızca 0.04a'da ve `main`'de var; `nerroth` dallarında değiştirilmiş ya da silinmiş. **Taban ≥ 0b65a50.**
- Bizim temiz başlangıç commit'imiz `236916e` (yerel `bizim` dalı) ile upstream ağaçlarını karşılaştırdım. Varlıklar hariç birebir aynı dosya sayısı (✔):

  | Upstream ağacı | Birebir aynı dosya |
  | --- | --- |
  | 0.04a | 84 / 98 |
  | 0.03a | 56 / 74 |
  | nerroth | 23 / 140 |
  | nerroth-rewrite | 21 / 193 |

  #42/#43/#45/#46/#47 PR'ları 0.04a'nın üstüne **hiçbir ek eşleşme** getirmiyor. PR'ların hiçbiri alınmamış.
- **Sonuç: taban tam olarak 0.04a = `main` @ f642e0b (✔).**
  - Temiz başlangıçta 0.04a'ya göre 13 dosya değişmiş, 107 eklenmiş; `build/` silinmiş ve `assets/` depodan çıkarılmış.
  - Bugünkü `oyun/*.py` ile 0.04a Python dosyaları arasında birebir aynı "anlamlı satır" (≥25 karakter) oranı yalnızca **%6,0** (211/3540). En çok `kayit.py`, `config.py` ve `surum.py`'de (✔).
  - Upstream rewrite'ın 0.04a ile ortak satır oranı ise **%41,2** (✔).
  - İki proje 0.04a'dan iki ayrı yöne çok uzaklaştı.
- `config/game_config_20120826.json` (bizim temel config) ile upstream rewrite'ın `config/main.json`'u **ayrıştırılınca tamamen aynı** (✔). Upstream yalnızca biçimini açtı (d71a5f0). **İki proje aynı 2012 tarihli temel veriyi kullanıyor**, 1.4.07 için bile.

### 1.3 İstemci sürüm kronolojisi (SWF ProductInfo derleme tarihleri, ✔ `kronoloji.py`)

| İstemci | Derleme (UTC) | Boyut (bayt) | Etiket | Sınıf | Havuz dizesi | Metin alanı (yazılı) |
| --- | --- | --- | --- | --- | --- | --- |
| 0914b | 2012-10-10 | 3 752 361 | 5093 | 1452 | 19139 | 871 |
| 0919b | 2012-10-29 | 3 759 546 | 5091 | 1464 | 19260 | 875 |
| 0922b | 2012-11-16 | 3 771 921 | 5091 | 1494 | 19461 | 875 |
| **0926b (bizim)** | **2012-12-05** | 3 780 932 | 5100 | 1511 | 19587 | 877 |
| 1.0.1 | 2012-12-13 | 3 878 788 | 5221 | 1542 | 20178 | 888 |
| 1.0.10 | 2013-02-08 | 3 092 599 | 4539 | 1682 | 21038 | 914 |
| 1.1.5 | 2013-04-29 | 3 192 938 | 4689 | 1790 | 22221 | 963 |
| 1.2.0 | 2013-05-29 | 3 275 364 | 4792 | 1838 | 22891 | 988 |
| 1.3.9 | 2013-10-02 | 3 986 069 | 5032 | 1926 | 23981 | 1016 |
| 1.4.06 | 2014-01-30 | 4 233 974 | 4983 | 1936 | 24051 | 1018 |
| **1.4.07** | **2014-01-31** | 4 233 956 | 4983 | 1936 | 24052 | 1018 |
| 1.4.07_fixed (rewrite) | aynı | 4 288 777 | 4983 | 1939 | 24282 | 1018 |

- Toplam 70 SWF ayrıştırıldı; liste özettir (tam liste: `kronoloji.out`).
- Bütün dosyalar CWS (zlib), SWF sürümü 10. İçlerinde "Adobe Flex 4 Application" metaverisi var (✔).
- Bizim yerel `SocialEmpires0926bsec.swf`, upstream'in `b37df27` blob'uyla aynı. Bu dosya 2022'den beri her dalda aynı (✔).
- **1.4.07 SWF yeni değil.** 8 Ağustos 2022'de (commit 2f0ff7b, "Add game swf versions") upstream'e girdi ve 0.03a'dan beri her sürümde var (✔).
  - 0.03a'nın giriş sayfası onu "1.4.07 (Broken)" diye sunuyordu (✔).
  - Yeni olan şey, onu çalıştıran **sunucu desteği** ve `_fixed` yaması (Ekim 2025'ten beri).
- Sistemlerin istemciye giriş sürümleri (✔ `ozellik_zaman.py`; sınıfın varlığı esas alındı):

  | Sistem | İlk sürüm |
  | --- | --- |
  | PVPManager, saldırı günlüğü | 1.0.1 |
  | NestsManager | 1.0.3 |
  | **GoalsManager** (MissionsManager kalkar), ShieldManager | **1.0.10** |
  | Soul Mixer | 1.0.13 |
  | Özel gün teklifleri | 1.0.17 |
  | Forge Island (CollectGame) | 1.1.0 |
  | Yeni günlük ödül | 1.1.6 |
  | Birim paketleri | 1.2.0 |

  Upstream'in "goal manager 1.0.10'da eklendi" iddiası istemcinin baytlarıyla **doğrulandı** (✔).
  - Ancak upstream `engine.py`'deki sürüm ayarı kodu bu yoruma uymuyor (✔ okundu).
  - `if major >= 1: settings["new_goals"] = True` satırı 1.0.1–1.0.9'u da "yeni hedef sistemi" sayıyor.
  - Bu küçük bir upstream hatası.

---

## 2. İstemci farkı: 0926b ile 1.4.07 (yalnızca bayt ayrıştırma)

### 2.1 Sayılar (✔ `fark.py`, `fark2.py`)

| Ölçü | 0926b | 1.4.07 | Fark |
| --- | --- | --- | --- |
| Toplam etiket | 5100 | 4983 | −117 (DefineSprite 1397→1084; resimler dışarı alınmış) |
| DoABC | 1 | 1 | |
| AS3 sınıfı | 1511 | 1936 | **+570 / −145** (ortak 1366) |
| Sabit havuzu dizesi | 19 587 | 24 052 | +5264 / −799 |
| DefineEditText etiketi | 885 | 1026 | +141 |
| Benzersiz metin alanı yazısı | 650 | 752 | +167 / −65 |
| SymbolClass adı | 507 | 552 | +180 / −135 |
| Yazı tipleri (DefineFont3) | 4 | 5 | + **Freestyle Script** |
| `core.Constants` `ID_*` sabiti | 1125 | 1284 | +159 (158'i birim ya da bina) |
| İstemci komut sabiti (`CMD_*`) | 156 | 185 | +29, kalkan 0 |
| `.php` uç noktası | — | — | +7 (`get_up_data.php`, `pvp/web/app.php/pvp/{enemy, attack/begin, attack/end, pool/add, pool/check, pool/del}`) |

Yazı tipleri: 0926b'de Arial Narrow, Arial Rounded MT Bold, Curse Casual JVE ve Eras Bold ITC var; 1.4.07 bunlara Freestyle Script'i ekliyor.

### 2.2 Yeni sınıfların paketlere dağılımı (✔)

| Paket | Yeni sınıf | Ne |
| --- | --- | --- |
| `SE_Lib_fla` | 108 | Görsel kütüphane, kalkan 90 |
| `core.isoengine.delegates` | 102 | Yeni birim davranışları |
| `managers.goals` | **58** | Hedef sistemi |
| `core.isoengine.isounits` | 51 | Özel ejderha ve devasa birimler |
| `popups` | 29 | Yeni pencereler |
| `GUI.extendedPortraits` | 19 | |
| `core.attacks.specials` + `damages` | 22 | |

- Yeni ejderha ve devasa birim örnekleri: Abyss, Cerberus, Ent ve Shaman Ancient; Genesis Ice, Iron, Shadow ve Wind Colossus; Easter; Golden, Platinum, Red ve Bull Armor; Forge, Night Forge ve Thunder Forge.
- Yeni pencereler: PopupSoulMixer, PopupBuyShields, PopupPvp, PopupPVPFinished, PopupAttackLog, PopupGoalList, PopupIslandForge, PopupNewDailyBonus, PopupFirstBuy, PopupShowPack, PopupOpenPack, PopupLevelUp, PopupBuyGraveyardCapacity, PopupBuyGraveyardPotion, PopupSpecialDayOffer, PopupIvoryOffer, PopupNightForgeOffer, PopupSelectYourDraggy…
- Yeni yöneticiler: GoalsManager, ShieldManager, PVPManager, PvpPlayerManager, CollectGameManager, UnitPacksManager, DailyBonusManager, NewDailyBonus.DailyBonus, SpecialDayOfferManager, BuildingQueueManager, NotificationsManager, NestsManager.
- Kalkanlar: `managers.MissionsManager`, `popups.PopupAttackFinished`, `PopupBuilding`, `PopupBuyGold`, `SelectYourDragonPopup` ve benzerleri.
- Tam listeler: `siniflar_eklenen.txt`, `siniflar_kalkan.txt`.

### 2.3 Oyunda gerçekten ne yeni?

- **Sistemler (istemci kodu var, 0926'da hiç yok, ✔):**
  - hedef listesi (GoalsManager)
  - Soul Mixer: 0926'da 0 dize, 1.4.07'de 29 dize ve 12 sınıf
  - kalkan satın alma ve PvP havuzu (pvp/web/app.php)
  - birim paketleri
  - Forge Island ve CollectGame adası
  - yeni günlük ödül
  - özel gün ve etkinlik teklifleri: `viral_offers` ile Easter Dragon, Hell's Forge, Ivory, Night Forge
  - üretim kuyrukları (push/pop/unqueue/speed_up_queue)
  - mezarlık kapasitesi satın alma
  - ilk alım teklifi
  - yeniden düzenlenmiş GUI durumları (StateAssault, StateSpy, StateTournament)
- **İçerik (veri):** Öğe listesi neredeyse aynı (✔ `ogeler.py`).
  - Bizim yamalı config'imizde 1787 öğe, upstream'inkinde 1786; ortak kimlik 1781.
  - Yalnız upstream'de 5 Hell's Forge süsü var. Yalnız bizde 6 özel Türkçe öğe var (9001–9103, `yeni_icerik.json`).
  - Ortak öğelerin 855'inde alan farkı var. Fark çoğunlukla 1.4.07'ye özgü alanlarda: `training_time` 771 öğeye eklenmiş; `pack_*` ve `sm_training_time` ise 437 öğede.
  - **1.4.07'ye özgü 158 birim ve bina sabitinden 150'sinin öğesi bizim config'te zaten var**, çünkü upstream 0.04a'nın `unit_patch.json`'u bize de geldi (✔ `idsabit.py`).
  - Ama 0926 istemcisi bu kimlikleri tanımıyor ve özel sınıfları yok. Bu birimler 0926'da ya genel davranışla çalışır ya bozulur (◐).
  - Bunlardan yalnızca **Soul Mixer (1529) mağazada**: `soulmixer_temp.json` `in_store=1`, seviye 8 (✔). 0926'da Soul Mixer kodu yok (✔), yani **mağazamızda büyük olasılıkla işlevsiz bir bina satılıyor** (◐, oyunda bakılmalı).
  - Tema setlerimiz (252 öğe) bu 150 öğenin hiçbirini açmıyor (✔).

### 2.4 Upstream'in `_fixed`'te değiştirdikleri (✔ `fixfark.py`)

- Etiket sayıları, metin alanları ve SymbolClass stokla **aynı**. Yalnızca DoABC değişmiş.
- 13 sınıfta 154 yöntem değişmiş; 7 yöntem ve 3 yardımcı sınıf (`*.SingletonEnforcer`) eklenmiş; 230 dize eklenmiş, hiçbiri silinmemiş.
- Bu, 1936 sınıfın yaklaşık %0,7'si demek.
- `_loc1_` … `_loc12_` gibi yerel adların eklenmesi, kodun bir AS3 decompiler'ıyla yeniden derlendiğini düşündürüyor (◐).
- Değişen sınıflar ve upstream commit'leriyle eşleşmeleri:

  | Sınıf | Değişen yöntem | Upstream commit'i |
  | --- | --- | --- |
  | `managers.CollectGameManager` | 47 | "1.4.07 SWF fix for Forge Island" (8dffb42) |
  | `popups.PopupIslandForge` | 25 | |
  | `managers.UnitPacksManager` | 19 | "Fix SP's unit packs data corruption in SWF" (eb4f947) |
  | `managers.ImageManager` | 15 | "Reroute ImageManager to pull images from server" (9d8a053); `SERVER_URL` ve `graph.facebook.com/` dizeleri eklenmiş |
  | `battle.IA` | 13 | Hedefleme |
  | `com.socialpoint.astar.AStar` | 11 | `sortNodes`; "SWF fix for ASTAR pathfinding and use old targetting system" (33f1fc5) |
  | `managers.NeighbourManager` | 11 | Komşu yardımları (faae12e, 9d9d17a) |
  | GoldenBahamut Dragon ve Draggy delegeleri, `IsoEntAncientDragonUnit` | — | Mermi ön yüklemesi, yetenek 2 |
  | `core.Base` (`mouseUsed`, `tutorialCheck`) | 2 | |
  | `BuildingQueueData.returnCost` | 1 | |
  | `battle.projectiles.ProjectilesNames` | 1 | |

- `_fixed` 15 commit'te değişmiş (6 Ekim 2025 – 15 Ağustos 2026; ✔ `git log`).
- `nerroth` dalındaki eski `_fixed` aynı yamaların ilk 7 sınıflık hâli (141 yöntem, ✔).
- **Önemli:** Stok 1.4.07 çevrimdışı oynanabilir hâle ancak istemci koduna bayt düzeyinde müdahaleyle gelebildi. Bu, (c) seçeneğinin riskini doğrudan gösteriyor.

---

## 3. Veri modeli: görevler ve hedefler

### 3.1 0926b'de (✔ ABC yöntem gövdeleri okunarak)

- Görev **mantığı istemciye gömülü.** `core.Constants.<cinit>` içinde `MISSIONS` tablosu ve 70'ten fazla `MISSION_*` türü sabiti var.
- `managers.MissionsManager` yalnızca bu tabloyu kullanıyor (`checkAllMissions`, `checkMissionCompleted`).
- Config'in `missions` anahtarı yalnızca metin ve ödül sağlıyor: `GameDataManager.missionsList`, alanlar `id`, `title`, `hint`, `description`, `reward`. Bizde 228 kayıt var.
- 0926'nın okumadığı config anahtarları (✔ `kim.py`):
  - `goals`, `viral_offers`, `viral_icons`, `level_up_tips` ve `unit_packs` 0926'da **hiç okunmuyor**.
  - `kompu_offers` ve `missions` okunuyor.
  - `daily_bonus` yalnızca `IsoEngine.<cinit>`'te ad olarak geçiyor (◐).
- **Bizim inherit ettiğimiz şu yamalar 0926 için ölü veri:**
  - `mission_goals.json` (/goals)
  - `viral_offers.json`
  - `viral_icons.json`
  - `new_daily_bonus.json`
  - `level_up_tips.json`'un `/level_up_tips` kısmı: 0926'da "level_up_tip" dizesi bile yok (✔). Bu dosyayı #4'te değiştirmişiz.
  - `soulmixer_temp.json` (bkz. 2.3)

### 3.2 1.4.07'de (✔)

- `core.Base.loadGameConfigSuccess` config'ten şunları okuyup ilgili yöneticilere veriyor:
  - `goals` → `GoalsManager.initMissions`
  - `collect_game`, `collect_game_items` → CollectGameManager
  - `viral_offers` → SpecialDayOfferManager
  - `daily_bonus` → DailyBonusManager
  - `unit_packs`
  - `pvp_shields` → ShieldManager
  - `recruitment_prices`, `level_up_tips`, `honor_levels`
- `AbstractGoal.<iinit>` yalnızca şu alanları okuyor: `id`, `type`, `title`, `description`, `instructions`, `image`, `characters`, `reward`, `orders`, `min_level`. GoalsManager `_load` ise `types`, `orders` ve `params` alanlarını okuyor.
- Hedef türleri 57 istemci sınıfıyla sabit (`initDictionary`). Upstream'in `goals.json`'unda 206 hedef ve 43 tür var (✔).
- Upstream'in hedef verisi büyük ölçüde **topluluk tarafından yeniden kurulmuş**: "Export first 14 goals", "Fill in missing data for goals", `goals.gproj` hedef editörü dosyası (◐ commit mesajları).
- Upstream sunucusu: `get_version_settings(GAMEVERSION)["new_goals"]` doğruysa ödül `get_goal`'dan (goals.json), değilse `get_mission`'dan (missions) alınıyor (`op.py` `cmd_complete_goal` ve `cmd_reward_goal`, ✔).

### 3.3 Yalnızca config ile etkinliğe özel hedef mümkün mü? (istemcinin kendi kodundan doğrulandı)

**Hayır, statik config ile mümkün değil.** Kanıt (✔):

- `GoalsManager.isGoalAvailable` gövdesi `d0 30 26 48`, yani `getlocal0; pushscope; pushtrue; returnvalue`: **her zaman true** döndürüyor.
- `activateGoalsAccordingContext` ve `deactivateGoalsAccordingContext` gövdesi `d0 30 47`: **boş**.
- `displayGoals` da boş.
- Hedef kaydında tarih, süre, etkinlik ya da bağlam alanı **okunmuyor**: tam alan listesi 3.2'de.
- `min_level` okunuyor ama `AbstractGoal.minLevel` hiçbir yerde kullanılmıyor. `minLevel` adını kullanan tek yer `CollectGameManager.initIsland` ve o başka bir nesne. Sonuç: hedeflerde seviye kapısı da yok (◐: dinamik ad erişimi teorik olarak mümkün).
- `MAX_ACTIVE_GOALS = 15` (`GoalsManager.<cinit>`, `pushbyte 15`).
- Upstream `event_system.py` de hedefleri değil, yalnızca `viral_offers`'ın `starts_at` ve `duration` alanlarını tarihe göre açıp kapatıyor (5 etkinlik, en fazla 3 etkin; ✔ okundu).
- **Yapılabilecek tek şey:** sunucunun `get_game_config.php` yanıtındaki `goals` listesini tarihe göre değiştirmesi. Config her yüklemede alınıyor. Bu da yalnızca var olan 57 hedef türüyle, oturum açılışında ve oturum sırasında kaldırma olmadan çalışır (◐).
- Tamamlanma `privateState.completedMissions` ve `rewardedMissions` kimlikleriyle tutulduğu için etkinlik hedeflerine çakışmayan kimlik aralığı ayrılmalı (◐).

---

## 4. Sunucu karşılaştırması

### 4.1 Komut kapsaması (✔ `komut.py`, `komut2.py`)

- İstemci komut kümesi `core.Constants.<cinit>` işlem kodundan çıkarıldı.

  | İstemci | `CMD_*` | Bizim işleyiciler (128 ad) | Upstream rewrite (125 ad) |
  | --- | --- | --- | --- |
  | 0926b | 156 | **128** | 101 |
  | 1.4.07 | 185 | 128 | **125** |

- Yalnız upstream'de olanlar (31), hepsi 1.4.07 sistemleri:
  - `begin_attack_new`, `end_attack_new`, `get_enemy_new`
  - `buy_shield`, `reset_shield`
  - `buy_unit_pack`, `buy_powerups`
  - `collect_game_*` (5 komut)
  - `buy_viral_offer_*`, `reward_viral_offer`
  - `push_queue_unit`, `pop_queue_unit`, `unqueue_unit`, `speed_up_queue`
  - `buy_first_purchase`, `set_first_purchase_timestamp`
  - `finish_si_recruitment`, `start_quest_new`
  - `buy_warehouse_capacity`, `buy_time_packet`, `add_unit_temple`
  - `reset_dragon`, `reset_monster`, `rider_reset`, `reset_potions_received`, `time_ff`
- Yalnız bizde olanlar (34):
  - `attack_player`, `spy_player`, `buy_attacks_pack`, `buy_spyings_pack`, `clean_attacks`
  - `start_heavy_siege`, `reset_heavy_siege`
  - `tournament_substract_resources`, `tournament_refund_resources`
  - `perform_city_quest`, `modify_position_univers`, `reset_position_univers`, `buy_pvp_territory`
  - `upgrade`, `unlock_building`, `put_graveyard`, `weekly_reward`, `comeback_reward`, `apply_rewards_ranking`, `gold_statue_conversion`…

### 4.2 Özellik tablosu

| Özellik | Biz (0926b) | Upstream (`nerroth-rewrite`) | Not |
| --- | --- | --- | --- |
| İstemci | Yalnız 0926b, sabit (`sunucu.OYUN_SWF`) ✔ | 1.4.07_fixed varsayılan, 0926b seçenek ✔ | |
| Görevler ve hedefler | 0926 görevleri; complete, reward, reset ✔ | `goals.json` 206 hedef + 0926 görevleri ✔ | Hedefler istemci 1.0.10+ ister |
| Etkinlikler | `takvim.py`: bayram tarihleri, tema setleri mağazada ✔ | `event_system.py`: 5 viral teklif, tarih ve gün ✔ | Mekanizmaları farklı; ikisi de sunucu tarafında |
| PvP | `pvp.py`, `attack_player` (0926 protokolü), bot rakipler, onur ✔ | PvP havuzu, HMAC'li `pvp/*` uçları, kalkanlar, sıralama sayfası ✔ | 1.4.07 PvP protokolü farklı |
| Turnuvalar | `turnuva.py`, `elo.py`: 4 kişilik oda, bot doldurma, haftalık Elo ✔ | 10 turnuva ucu `_api_not_implemented` ✔ | **Bizim güçlü yanımız** |
| Dünya haritası, kıta | `ada.py`, `get_user_world`, `get_continent_ranking` ✔ | `get_continent` ve `get_user_world` saplama ✔ | |
| Kompu | `kompu_try`, `kompu_hurry_up` ✔ | Saplama ✔ | |
| Bot dünyası | 50 bot, `dunya.py` dakikalık tur ✔ | Statik arkadaş ve düşman köyleri, `hire_friends` ✔ | |
| Haber paneli, Şeref Kürsüsü | `diyar.py` ✔ | Yok ✔ | |
| İmparatorluk günlüğü | `gunluk.py` ✔ | Yok | |
| Soul Mixer, birim paketleri, Forge Island, yeni günlük ödül, kuyruklar, kalkan alma | Yok (0926'da istemci kodu yok) ✔ | Var ✔ | Taşınamaz, bkz. §6 |
| Dart | `darts_*` ✔ | `darts.py` ✔ | |
| Mağaza | Tema setleri takvime göre ✔ | `shop_rotation.json`: 48 saatte bir döner, "spooktober" ✔ | |
| Türkçe | config 4222 çeviri; SWF'de 455 metin alanı, 50 statik yazı, 1 AS3 dizesi; glif ekleme ✔ | Yalnız İngilizce (`0-language_en.json`) ✔ | **Bize özgü** |
| Android | Uygulama, cihazda sunucu ✔ | Yok ✔ | Bize özgü |
| Ruffle | 0.7.1'e sabit, yerelden sunuluyor ✔ | unpkg'den sürümsüz "latest", internet ister ✔ | |
| Çevrimdışı paket | `onindirme.py` ✔ | SP CDN'den isteğe bağlı indirme ✔ | Upstream'de f-string hatası: `send_from_directory("{ASSETS_DIR}/..` (rewrite satır 268 ve 272; 0.04a'da yok) ✔ |
| Wi-Fi taşıma, yedek indirme ve yükleme | `tasima.py`, `kayit_yedek.py` ✔ | Yok | |
| Kayıt sağlamlığı | Atomik yazım, fsync, `.bak`, günlük yedek, bozuk kaydı karantinaya alma ✔ | Düz `open(...,'w')` + `json.dump`, "# TODO" ✔ | PR #48 bunu öneriyor, birleşmemiş |
| Güvenlik | CSRF, DNS yeniden bağlama, `safe_join` ✔ | `send_from_directory`; istek yolundan `os.makedirs` (◐) | |
| Testler | 197 Python + JS, CI ✔ | Test yok ✔ | |
| Sunucu iskeleti | Flask + Waitress | `flask[async]` | |
| HMAC | ? (0926 da anahtarı içeriyor; PvP için kullanılmıyor olabilir) | `server_hmac.py` (anahtar 0926 ve 1407 dizelerinde aynı) ✔ | |
| Profil resmi | Kullanıcı fotoğrafı ✔ | Rastgele avatar (`avatars.py`) ✔ | |

---

## 5. Uyumluluk

### 5.1 Kayıt biçimi (✔ `tip.py` ve okuma)

- Upstream `migrate_loaded_save` kayıtta üst düzey `"version"` anahtarı görürse onu "çok eski kayıt" sayıyor. Bizim kayıtlarımızda bu anahtar `"0.05a"` olarak duruyor (`surum.py`, `kayit.new_village`). Upstream o durumda şunları yapıyor (✔ okundu):
  - **Her haritadaki her öğenin zaman damgasını şimdiye çekiyor:** üretim sayaçları sıfırlanır.
  - Seviyeye göre **mana ekliyor**.
  - **Mezarlığı sıfırlıyor:** `deadHeroes` silinir.
  - `monsterNestActive = 1` yapıyor ve `version` anahtarını siliyor.
  - Bizim kayıtlarımız upstream'e taşınırsa oyuncu kayıp yaşar. Upstream'in göç kodu değil, kendimize ait bir göç gerekir.
- Alan farkları (bizim `initial.json` ile upstream `initial1407.json`):
  - upstream'de fazla `privateState` alanı 16 tane: `barracksQueues`, `collections`, `collectionsCompleted`, `graveyardCapacity`, `resurrectableUnits`, `shieldCooldown`, `shieldEndTime`, `purchasedShields`, `unitPacks`, `iphoneBox`, `PVPattacksReceived`, `tournamentFormation`…
  - `playerInfo`'da fazla 4 alan: `attacks_won`, `attacks_lost`, `honor_points`, `country`.
  - Haritada fazla 5 alan: `store`, `warehousedUnits`, `numTradesDone`, `timestampLastTrade`, `warehouseAditionalCapacitySingle`.
  - `gifts`: bizde liste, upstream'de sözlük. Upstream dönüştürüyor.
  - Tür çakışması (değer sıfırlanır): `maps[].questTimes` bizde liste, upstream'de sözlük.
- Bize özgü alanlar upstream'de silinmez ama yok sayılır: `bot_hafiza`, `kita*`, `shield_until`, `lastUpgrades`, `marketTimestamp`.
- **Ters yön de önemli.** 1.4.07 istemcisi bizim sunucumuza bağlanırsa:
  - 29 yeni komut "bilinmeyen" kalır.
  - PvP ve birim paketi uçları yok.
  - Kayıtta beklenen alanlar eksik.
  - Bu yüzden istemci açılmaz ya da kaynaklar geri gider (◐).

### 5.2 Türkçe SWF yamamız 1.4.07'de (✔ `kapsama.py`)

| Sözlük bölümü | 0926b | 1.4.07 (stok ve `_fixed` aynı) |
| --- | --- | --- |
| `metin_alanlari` anahtarı (455) | 455 (%100) | **404 (%88,8)** |
| `statik_yazilar` (50) | 50 | 44 |
| `as3_dizeleri` (1, "Cargando") | 1 | 1 |

- 1.4.07'de bulunmayan 51 anahtara örnekler: "Cancel", "Battle Result", "My Army", "Enter Tournament", "Last connected:". Bunlar yeni pencerelerde yeniden düzenlenmiş.
- 1.4.07'de çevrilmemiş, harf içeren **230** benzersiz metin alanı kalıyor. Aynı ölçütle 0926'da bugün 100 tane bırakılmış. **Yaklaşık 130 yeni metin** çevrilmeli.
- Yeni yazı tipi Freestyle Script Türkçe glif kaynağımızda yok (`TR_FONTLARI` yalnızca 2 yazı tipi). ğ, ş ve İ orada eksik kalır (◐).
- Yamanın ayrıştırma mantığı genel (etiket ve DefineEditText); 1.4.07'de de çalışması beklenir. Denenmedi (◐).
- Config çevirisi: upstream 1.4.07 `localization_strings`'teki 1942 adın 1514'ü (%78,0) `tr.json`'da karşılanıyor. Yaklaşık 428 yeni dize ve 206 hedefin başlık ve açıklaması (~412 metin) çevrilmeli (✔ ölçüldü).

---

## 6. Seçenekler

| | Emek (?) | Risk | Ne bozulur | Kazanç |
| --- | --- | --- | --- | --- |
| **(a) 0926'da kal, fikir al** | Düşük: düzeltme başına saatler ya da günler | Düşük | Hiçbir şey | Aşağıdaki somut düzeltmeler; mevcut her şey korunur |
| **(b) Yalnızca hedef ve etkinlik sistemini taşı** | — | — | — | **0926'da mümkün değil.** Hedef sistemi (GoalsManager), viral teklifler, Forge Island ve günlük ödülün kodu istemcide ve 0926'da yok (✔ §3). 0926'da yapılabilen: config `missions` ile mevcut görevlerin metnini ve ödülünü değiştirmek; etkinlik mağazası (`takvim.py`) zaten var. Yani (b), (a)'ya ya da (c)'ye indirgenir. |
| **(c) Tam göç: 1.4.07** | Yüksek: haftalar ya da aylar | Yüksek | PvP (protokol farklı), kayıt göçü, SWF çeviri sözlüğü (%11'i ve ~130 yeni metin), yazı tipi, Android emülatör sınaması, testlerin çoğu, belki Ruffle uyumu (upstream Ruffle'ı "deneysel" sayıyor; ?) | Yeni sistemler: hedefler, Soul Mixer, kalkanlar, birim paketleri, Forge Island, 51 özel birim; upstream'in hata düzeltmelerinden yararlanma |
| **(d) Upstream'e katkı ya da birleşme** | Birleşme pratikte imkânsız (ortak kod %6 ile %41; ayrı mimariler). Seçici katkı: orta | Düşük ya da orta | Kendi dalımızda bir şey bozulmaz | Topluluk; Türkçe ve dil yamasının upstream'e girmesi; bizim sağlam kayıt, turnuva ve kompu uçlarının upstream'deki saplamaları doldurması |

### (a) için somut öneriler

1. **Varlık kaynağını sabitle.**
   - `oyun/varliklar.py`, `varliklari_indir.py` ve `araclar/onindirme_listesi.py` şu anda `main` dalından indiriyor; dal değişebilir.
   - `f642e0b` commit'ine sabitlenmesini öneririm. Bugün rewrite yalnızca 347 varlık ekliyor ve 1 tane siliyor (`externalized/DailyBonus/imgs/temp.png`); risk düşük ama tekrarlanabilirlik için (✔).
2. **Mağazadaki Soul Mixer'ı kaldır ya da gizle.**
   - Kaynak: `config/patch/soulmixer_temp.json`, öğe 1529, `in_store=1`. Önce oyunda nasıl davrandığına bakılmalı (◐).
3. **0926'nın okumadığı yamaları işaretle ya da kaldır.**
   - Yamalar: `mission_goals`, `viral_offers`, `viral_icons`, `new_daily_bonus`, `level_up_tips`. Ölü veri ve çeviri emeği (✔).
4. **Upstream rewrite'taki veri düzeltmelerini tek tek değerlendir.**
   - Örnekler: tarlaların yanlış yükseltme yolları (efb753b), üretim binalarının yükseltilebilmesi (1a51219), müttefik binasının ev sayılması (ba02772), Pharaoh's Gold Mine toplama türü (a437e92).
   - Bunlar config öğe verisinde; 0926'yı da ilgilendirebilir (◐).
   - GPLv3 atfıyla alınmalı.

### Öneri

**(a) + seçici (d).**

- 0926, upstream'in de hâlâ "çalışan" diye sunduğu istemci.
- Bizim bütün Türkçe, Android, test ve sağlamlık işimiz ona bağlı.
- 1.4.07'nin kazancı gerçek ama bedeli büyük. Upstream'in kendi 1.4.07 desteği de yayımlanmamış ve istemci yamasına dayanıyor.
- (c) ancak sahibi "hedefler, Soul Mixer, kalkanlar" gibi sistemleri açıkça isterse, ayrı bir dalda ve aşama aşama denenmeli.
  - İlk aşama yalnızca bir "uyumluluk keşfi" olur: 1.4.07_fixed'i bizim sunucuya bağlamadan Ruffle'da açmak.

---

## 7. GPLv3 ve atıf yükümlülükleri

- Bizim `LICENSE` dosyamız GPLv3. README'de "Copyright (C) 2022 The Social Emperors team" notu ve upstream bağlantısı var (✔).
- **§5(a):** Değiştirilmiş sürüm "değiştirildiğine dair belirgin bir not ve ilgili bir tarih" taşımalı. README çatal olduğumuzu söylüyor ama değişikliğin tarihi ve kapsamı yazılı değil (◐). Kısa bir not eklenebilir: "0.04a (f642e0b, 26.09.2025) tabanından değiştirildi".
- Temiz başlangıç squash'ı upstream'in yazar geçmişini sildi. Bu GPL ihlali değil ama atıf için README'de katkıcı listesine bağlantı vermek iyi olur (?).
- **Upstream'den alınacak her kod GPLv3'tür.** Dosyalarında başlık yok, lisans depo düzeyinde. Alındığı commit ve yazar belirtilmeli:
  - Nerroth.
  - `server_hmac.py` dosyasının içindeki "SPECIAL THANKS TO: wireframe_0" teşekkürü korunmalı.
- Bizde zaten upstream'den birebir gelen dosyalar var: `araclar/make_se_unit_patch.py`, `se_unit_patch.csv` ve `unit_templates.json` (0.04a ile aynı blob'lar, ✔).
- APK dağıtımı GPLv3 kapsamında ilgili kaynak kodun sunulmasını gerektirir. Depo açıksa bu karşılanıyor (? doğrulanmadı).
- **Oyun SWF'leri ve varlıkları Social Point'in mülkiyetinde; GPL kapsamında değil.**
  - Biz yamayı çalışma anında, yerelde uyguluyoruz ve yamalı SWF'yi dağıtmıyoruz (◐).
  - (c) seçeneğinde upstream'in `_fixed` dosyasını almak, **değiştirilmiş mülk ikiliği** indirmek olur. Hukuki durumu iki proje için de gri; bu bir hukuk görüşü değildir (?).

---

## 8. Bu denetimin sınırları

- Hiçbir şey çalıştırılmadı. Oyun davranışı (Soul Mixer'ın 0926'daki etkisi, 1.4.07'nin Ruffle'da açılması) gözle görülmedi.
- PR'ların açık ya da kapalı olduğu GitHub API erişimi olmadığı için doğrulanamadı.
- Emek tahminleri (?) bir mühendislik kestirimidir, ölçüm değildir.
- ABC çözümleyicim standart AVM2 işlem kodu tablosunu kullanıyor. Stok 1.4.07'de 16 805 yöntem gövdesi sorunsuz ayrıştırıldı (✔). Gizlenmiş kodda tek tük işlem kodu kaçırılmış olabilir (◐).
