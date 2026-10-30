# Tarama 1: socialempires-tr ile AcidCaos/socialemperors karşılaştırması

Tarih: 30 Ekim 2026. Bizim depo yalnızca okundu; hiçbir dosyası değişmedi (`git status` boş).

İşaretler: **✔** okunarak ya da çalıştırılarak doğrulandı, **◐** dolaylı kanıt, **?** doğrulanmadı.

Kısaltmalar:
- **NR**: `origin/nerroth-rewrite` (54df29e, 2026-08-16).
- **main**: `origin/main` (f642e0b, 0.04a etiketi, 2025-09-26).
- **bizim**: bizim master (HEAD b5c08f5) ya da klondaki `bizim` dalı (236916e, "temiz başlangıç").

Çalışma dosyaları `scratchpad/tarama/` altında:
- `betik/swfanaliz.py`, `betik/sabitler.py`, `betik/tarih.py`, `betik/yama_dene.py`, `betik/yama_ayrinti.py`
- `swf/*.json`, `komutlar.json`, `sinif_farki.json`, `swf_tarih_sirali.txt`
- `bizim_yamali_config.json`, `nr_yamali_config.json`, `rewrite_log.txt`

---

## 1. Temel sürüm: çatal hangi upstream durumundan alındı?

**Sonuç: upstream `main` ucu, yani 0.04a etiketi (f642e0b, 2025-09-26).** ✔

Yöntem: blob özetleri karşılaştırıldı (`git ls-tree -r`, yol+özet eşleşmesi; blob indirmeye gerek yok).
`main` ve `nerroth` geçmişindeki her commit, bizim temiz başlangıç ağacıyla (236916e, 204 dosya) sınandı. ✔

| Upstream durumu | Bizimle birebir aynı dosya (yol+özet) |
| --- | --- |
| **f642e0b (0.04a = main ucu)** | **84** |
| 0b65a50 (vahzco, "patches for 1.4.07 load") | 82 |
| 8822f51 / 9b028ac (2025-09-26) | 80 / 79 |
| 0.03a | 56 |
| 0.02a / 0.01a | 8 / 7 |
| `origin/nerroth` ucu | 23 |
| `origin/nerroth-rewrite` ucu | 21 |

- `config/patch/` altındaki 11 yamanın tamamı 0.04a ile aynı.
  - Bunların arasında 0b65a50'de değişen `viral_icons.json` ve `level_up_tips.json` da var.
  - `config/game_config_*.json` ve `villages/` (35 görev haritası, Arthur30-32, AcidCaos, initial) da birebir aynı. ✔
- Bizim temel ağaçta 0.04a'dan farklı ya da yeni olan dosyalar:
  - `quests.py`, `sessions.py`, `command.py`, `server.py`, `get_game_config.py`, `version.py`, `templates/*`, `en_*` yazı tipleri
  - Türkçe modüller: `turkce.py`, `world.py`, `turnuva.py`...
  - `config/patch/yeni_icerik.json`, bot portreleri
- Liste: `tarama/` içindeki karşılaştırma. ✔
- Oyun SWF'si aynı dosya:
  - Bizim `download_assets/assets/flash/SocialEmpires0926bsec.swf` özeti `b37df272…`.
  - Bu, upstream `main` ve NR'deki `assets/flash/SocialEmpires0926bsec.swf` ile aynı (3.780.932 bayt). ✔
- Bugünkü HEAD (240 izlenen dosya):
  - 75 dosya hâlâ 0.04a ile aynı. Bunlar yalnızca veri ve belge: `config/` (4), `config/patch/` (10), `villages/` (39), `templates/img/` (11), lisans ve belgeler, `distr/`.
  - **Hiçbir `.py` dosyası upstream ile aynı değil.** Kod `oyun/` paketine Türkçe adlarla yeniden yazılmış. ✔
  - NR ile aynı dosya 21 tane; hepsi görsel, belge ya da config. ✔
- Upstream dal ilişkisi ✔:
  - `nerroth`, NR'nin atası (`merge-base --is-ancestor`).
  - NR = main + 429 commit (426 Nerroth, 3 NeutralTheGreat) = nerroth + 137 commit.
  - Commit dağılımı: 2025-10'da 290, 2026-05'te 31, 2026-07'de 29; son commit 2026-08-16.

---

## 2. Upstream'de olup bizde olmayanlar (özellikle nerroth-rewrite)

### 2.1 Mimari

- **Çok sürümlü sunucu** ✔ (`engine.py:231 get_version_settings`):
  - Oturumdaki `GAMEVERSION`'a göre `new_goals` (≥1.0.10), `new_daily` ve `show_offers` (≥1.4) açılır.
  - Giriş sayfası iki istemci sunar: `SocialEmpires1.4.07sec_fixed.swf` ("Latest") ve `SocialEmpires0926bsec.swf` (`templates/login.html:76-78`).
  - Yani NR 0.9.26b'yi de hedefliyor: "darts (old version only)", "survival maps (old versions only)", "chapters (old version only)" işleyicileri.
- **Config tabanı aynı, 1.4.07 yamalarla geliyor** ✔:
  - `config/main.json`, veri olarak `game_config_20120826.json` ile **birebir aynı**. Bunu `json.load` karşılaştırmasıyla doğruladım.
  - 1.4.07 içeriği üç yamadan geliyor:
    - `0-language_en.json`: `localization_strings`'i bütünüyle değiştirir.
    - `1-mega_patch.json`: 51 işlem.
    - `2-unit_patch.json`: `items` ve `globals`'i değiştirir.
  - Eski yamalar `patch_ignore` ile kapatılıyor (`get_game_config.py:28`).
- **`server_config.json` / `server_config.py`** ✔: tek dosyadan ayarlanıyor.
  - Sunucu: ip, port, günlük, kayıt yeniden yükleme.
  - PvP: kalkan süresi, kaynak çalma, çarpan 25, arama ayarları.
  - Mağaza: rotasyon saati, fraksiyon sayısı, spooktober.
  - Diğer: günlük ödül tekrarı, mezarlık sınırı, yasaklı eşyalar, rastgele avatar.
  - Etkinlikler.
- **HMAC** ✔ (`server_hmac.py`):
  - Yanıtların hepsi `construct_hash_and_payload` ile `<hmac>;<json>` biçiminde: player_info, game_config, quest...
  - PvP isteklerinin imzası denetleniyor (`check_hmac`).
  - Anahtar `3m0d3pwiupoetn7ysa02`, bizim `Config.SERVER_KEY` ile aynı (iki SWF'de de aynı sabit; §4).
- **Komut işleyici** ✔ (`command.py`):
  - 123 komut gerçekten işleniyor.
  - Hata ya da başarısızlıkta 403 "desync detected" dönüyor ve `CMDERR` bayrağıyla istemcinin komutları yeniden oynatması engelleniyor (c94b59e, 2026-05-17).
  - Bilinmeyen komut sessizce geçiyor (`NOT_IMPLEMENTED` → durum 1, zincir sürer).
  - Bizim felsefemizin tersi: biz "istemciyi taklit et, reddetme" diyoruz (`docs/GELISTIRME.md`). ✔
- **Flask[async]**, `logging` ile dosyaya günlük (fea033e, 6cc0037). ✔
- **Mod sistemi** ✔ (`mods.py`, 4e6eb08):
  - Modda zorunlu meta alanlar var (`name`, `author`, `game`, `supports:["rewrite"]`, `data`).
  - Uygulanmadan önce doğrulanıyor.
  - Bizdeki mod yükleyici 0.04a'nın düz jsonpatch hâli. ◐
- **Kayıt göçü** ✔ (`version.py:331 migrate_loaded_save`):
  - Sürüm numarası yerine her açılışta alan alan "eksikse ekle, türü yanlışsa düzelt" (`fix_variable`).
  - Yaklaşık 70 alan denetleniyor.
- **Hata ayıklama menüsü** ✔: `resetGoals OK` yazınca hedefler sıfırlanıyor (009810d).
  - Not: `spdebug` flashvar dizesi 1.4.07'de yok, 0926b'de var. Hata ayıklamanın açılışı sürümler arasında farklı. ✔

### 2.2 Oynanış özellikleri ve olgunlukları

Olgunluk: **Olgun** (çok düzeltme, aylarca bakım) / **Orta** / **Ham** (WIP ya da kısmi). Kanıt: commit geçmişi ve kod okuması. ◐

| Özellik | Ne yapıyor | İstemci | Olgunluk |
| --- | --- | --- | --- |
| **Arthur hedefleri (goals)** | `config/goals.json` 206 hedef ve 43 tür (`built_id` 69, `trained_id` 16, `complete_quest` 16...); `goals.gproj` düzenleyici projesi; ödül verme, kilitlenme düzeltmesi, sıfırlama | ≥1.0.10 (GoalsManager) | Orta-olgun. 2026-07'de yoğun iş, 970738e "(WIP)", 54df29e "Fix Build 20 Walls goal" ✔ |
| **Etkinlik sistemi** | `event_system.py`: EASTER_DRAGON, HELL_FORGE_ISLAND, IVORY_CHALLENGE(_DUPLICATE), NIGHT_FORGE; tarih ve gün sayısıyla `viral_offers` / `collect_game` açılıp kapanıyor; en fazla 3 etkinlik | 1.4.x (`viral_offer` komutları yeni) | Orta ✔ |
| **Hell's Forge Island** | `collect_game_*` 5 komut, eşyalar 1530 ve 2262-2266, "hepsini al" fiyatı, SWF düzeltmeleri (34a7b6f, 8dffb42) | yalnız 1.4.07 (CollectGameManager) | Orta ✔ |
| **Mağaza rotasyonu** | `shop_rotation.json`: 14 fraksiyon, 48 saatte bir en fazla 2 fraksiyon, sınırlı eşyaların süresi, spooktober, `always_enabled` | sürümden bağımsız ◐ | Orta ✔ |
| **Yeni günlük ödül** | `daily_bonus.py`, 5 günlük ödül, tekrar seçeneği; eski `win_bonus` da var | yeni ödül 1.4.x | Orta ✔ |
| **Dart** | `darts.py`: `darts_items` tarihlerini haftalık kaydırıyor; config'te 2012 tarihleri var | 0.9.26b ve eski | Orta ✔ |
| **Soul Mixer** | kuyruk, hızlandırma, güçlendirme (`buy_powerups`), `tools/fusion_builder.py` | yalnız 1.4.07 (PopupSoulMixer) | Olgun (2025-09'dan 2026-07'ye kadar düzeltme) ✔ |
| **Birim paketleri** | `get_up_data.php`, `buy_unit_pack`, paket verisi, SWF'de veri bozulması düzeltmesi | yalnız 1.4.07 (UnitPacksManager) | Orta ✔ |
| **PvP (1.4.07)** | `pvp/web/app.php/pvp/{enemy,attack/begin,attack/end}`, saves/enemy havuzu, arama bedeli, kalkanlar (al/sıfırla, bekleme süresi), onur puanı, kaynak çalma, saldırı günlüğü, intikam, `/pvp/ranking` sayfası | yalnız 1.4.07 (PVPManager, ShieldManager) | Olgun ✔. `pvp/pool/{add,check,del}` uçları rotalanmamış ◐ |
| **Mezarlık** | kapasite, iksir, "arkadaştan iksir iste" sayfası (`/graveyard/potions`), birim başı sınır | kısmen 0926b; satın alma ve iksir isteme 1.4.07 | Orta ✔ |
| **Müttefik pazarı, Yuvarlak Masa, Recruitment Prizes, Supreme Bahamut Temple, Zaman ve Hava Makinesi, yuvalar, binici, Troll İmparatorluğu (başlangıç), Survival** | işleyiciler `op.py` içinde | karışık | Orta ✔ (Troll c3aafcf "Initial") |
| **Arkadaş işe alma (SI)** | binalara arkadaşları kendiliğinden yerleştirme, talimat sayfası | ikisi de | Orta ✔ |
| **Avatarlar** | `config/avatars.json` (oyunun birim portreleri), imparatorluk kurarken seçim, rastgele atama | 1.4.07'de ImageManager yönlendirmesi gerekli | Orta ✔ |
| **ExternalInterface sayfaları** | PvP sıralaması, iksir isteme, işe alma (a25bdd5) | 1.4.07 | Ham-orta ✔ |
| **Turnuvalar** | `tournaments/*.php` uçlarının **hepsi** `_api_not_implemented` (404) | | Yok ✔ (`server.py:748-773`) |
| **Büyücü iksirleri (kompu)** | `kompu_try` ve `kompu_hurry_up` 404; mega yama `kompu_offers: []` | | Yok ✔ |
| **Dünya haritası** | `get_continent.php` ve `get_user_world.php` 404; `get_continent_ranking` sabit taslak | | Yok ✔ |

### 2.3 İstemci SWF düzeltmeleri (1.4.07sec_fixed)

`SocialEmpires1.4.07sec_fixed.swf` 15 commit'te değişmiş (eb4f947 → 70e7f5d). ✔ Yapılanlar:
- Birim paketi verisindeki bozulma giderildi.
- ImageManager resimleri sunucudan çekiyor; avatarlar oyunda görünüyor.
- Komşu yardımı donması giderildi.
- A* yol bulma iyileştirildi; 0.9.26b'deki hedefleme davranışı geri getirildi.
- Forge Island: `dragonBG.png` yükleniyor, gereksiz bir `if` kaldırıldı.
- `P_MINI_FIREBALL`, `p.fireBall_02`'ye bağlandı.
- Golden Bahamut mermisi (iki kez düzeltilmiş).
- Demirci ve üniversite indirimleri çalışıyor.
- **Zorla orta kalite** ayarı kaldırıldı.
- Süreli "müttefik lazım" penceresi kapatıldı.
- Ent Ancient Dragon'un 2. yeteneği düzeltildi.

Dize farkı JPEXS/FFDec ile yeniden derlemenin izlerini taşıyor ✔:
- `_loc1_`…`_loc12_`, `param1`…`param6` adları.
- `AStar.as$22`, `ImageManager.as$249` gibi derleme birimi adları.
- `SERVER_URL`, `graph.facebook.com/`, `meow` dizeleri.

Sınıf sayısı (1.932) değişmedi; yalnızca 230 dize eklendi. ✔

### 2.4 Varlıklar

- NR'de `assets/` main'e göre **347 eklenen ve 1 silinen** dosya içeriyor; toplam 1.292,9 MB'tan 1.340,7 MB'a çıkıyor (yaklaşık +48 MB). ✔
- Yeni dosyalar:
  - `assets/img/countdown/` (181)
  - `externalized/` (64'ten 129'a)
  - `images_new/` (401'den 483'e)
  - `swf/` (22'den 27'ye; zaman makinesi, kalkan, kazanma ve kaybetme animasyonları)
  - 44 avatar (`templates/img/profile/user/`)
- **Bizim indirme kaynağımız** `raw.githubusercontent.com/AcidCaos/socialemperors/main/assets/` (`oyun/varliklar.py:30`). Yani bu 347 dosya bize hiç gelmez. ✔

### 2.5 Upstream'de gördüğüm zayıflıklar (taşırken dikkat)

- Testler ve CI:
  - NR ağacında `tests/` ve `.github/` yok.
  - `unittest` ya da `pytest` kullanılmıyor. ✔
- `app.secret_key = 'SECRET_KEY'` sabit yazılmış (`server.py:796`). ✔
- Sunucu Flask geliştirme sunucusu. ✔
- Kayıt dosyası atomik yazılmıyor, `.bak` yok (`sessions.py:848-858`, `open(...,'w')` ile doğrudan `json.dump`). ✔
- Ruffle `https://unpkg.com/@ruffle-rs/ruffle/ruffle.js`'ten **sürümsüz** yükleniyor ve "Experimental" olarak işaretli (`templates/ruffle.html:11`, `login.html`). ✔
  - Bizde bu sorun F0-02'de çözüldü (0.7.1 sabit, yerel).
- Statik varlık yedeği bozuk:
  - `server.py:268` ve `:272`'de `send_from_directory("{ASSETS_DIR}/../download_assets/assets", path)` yazıyor; başında `f` yok.
  - Bu yüzden CDN'den inen dosyalar sunulamaz; NR depodaki varlıklara bağımlı. ✔ (okuma)
- Aynı uç, isteğin yolunu ayıklamadan `os.makedirs` ve `urlretrieve` ile diske yazıyor. Yol geçişi riski olabilir. ?

---

## 3. Bizde olup onlarda olmayanlar

Hepsi bizim depoda okunarak doğrulandı ✔. NR'de karşılığı yok ✔.

| Özellik | Bizde nerede | NR'de |
| --- | --- | --- |
| **Türkçe config metinleri** | `ceviri/tr.json`: 4.222 anahtar (`loc:` 1.626, `item:` 1.885, `mission:` 458, `level:` 100...); `oyun/turkce.py` | yalnız İngilizce `0-language_en` |
| **SWF içi Türkçe** | `oyun/swf_yama.py`: DefineEditText 455 anahtar, DefineText 50 satır, AS3 sabit havuzu dizeleri (`as3_dizeleri`: Cargando → Yükleniyor) | yok |
| **Yazı tipine Türkçe harf** | `oyun/swf_font.py`, `assets/fonts/tr_*.swf`; gömülü fontlara ğĞİşŞ… eklenir, glifler yeniden eşlenir | yok |
| **Android uygulaması** | `android/` (Chaquopy ve WebView, sunucu cihazın içinde, 929 satır), `araclar/android_paketi.py`, emülatör sınaması | yok |
| **Bot dünya simülasyonu** | `oyun/dunya.py` (832 satır): 50 bot, kişilik, öfke hafızası, ittifak, intikam seferleri | yok. NR'de PvP havuzu yalnızca saves/enemy klasörlerinden |
| **Diyar Haberleri, Şeref Kürsüsü** | `oyun/diyar.py` (`/dunya/olaylar`, `/dunya/kursu`) | yok |
| **Turnuvalar** | `oyun/turnuva.py` (4 kişilik oda, bot doldurma), `oyun/elo.py` (haftalık Elo) | 404 |
| **Büyücünün İksirleri** | `kompu_try` ve `kompu_hurry_up`, `config/patch/kompu.json` | 404 |
| **Dünya haritası ve fetih** | `oyun/ada.py`, `get_user_world.php` | 404 |
| **İmparatorluk günlüğü** | `oyun/gunluk.py` (`/gunluk`) | yok |
| **Etkinlik takvimi** | `oyun/takvim.py`, `config/takvim.json` (Diyanet bayramları, tema setleri) | NR'de el ile tarih girilen `events` |
| **Çevrimdışı paket** | `oyun/onindirme.py`, `config/onindirme.tsv` (temel yaklaşık 175 MB, tam yaklaşık 1,1 GB) | yok (varlıklar depoda) |
| **Wi-Fi ile taşıma** | `oyun/tasima.py`, `oyun/aktarim.py` (6 haneli kod) | yok |
| **Profil fotoğrafı** | `oyun/profil.py` | NR'de hazır avatar listesi |
| **Kayıt dayanıklılığı** | atomik yazım, `.bak`, `.bozuk` ayırma, günlük yedek (`oyun/kayit.py:95-145,318-400`), indir/yükle ve SHA-256 (`oyun/kayit_yedek.py`) | yok |
| **Güvenlik** | CSRF, DNS yeniden bağlama, yol denetimi (BULGULAR DNT-01, GUV-01..03), `SE_SECRET_KEY` | yok |
| **Ruffle sabit ve yerel** | `oyun/ruffle.py` (0.7.1) | unpkg, sürümsüz |
| **Eksik efekt türetme** | `oyun/fx_yama.py` (`p.miniFireball2` → `p.fireBall`) | NR'de yalnız 1.4.07 için SWF içinde |
| **Testler ve CI** | 197 Python test fonksiyonu (2.519 satır), 4 JS test, `.github/workflows` (testler, Windows paketi, Android) | yok |
| **Windows paketi, PWA, ev ağı** | `araclar/windows_paketi.py`, manifest | NR'de PyInstaller `build/*.bat` |
| **Hile paneli** | `oyun/hile.py` (`/cheat`) | yok (oyunun debug menüsü) |

Kod büyüklüğü ✔:
- Bizim izlenen Python (testler hariç) 8.832 satır, testler 2.519 satır.
- NR Python (tools hariç) 9.575 satır.

---

## 4. İstemci sürüm farkı: 0926bsec ile 1.4.07

### 4.1 Tarih: 0926b gerçekten eski mi?

Her SWF'nin ProductInfo etiketindeki (41) derleme zamanı okundu. ✔ (`tarama/swf_tarih_sirali.txt`, 69 dosya)

| SWF | Derleme (UTC) |
| --- | --- |
| SocialEmpires0914bsec | 2012-10-10 |
| **SocialEmpires0926bsec** (bizim) | **2012-12-05 12:21** |
| SocialEmpires1.0.1sec | 2012-12-13 |
| SocialEmpires1.0.10sec (GoalsManager'ın ilk göründüğü) | 2013-02-08 |
| SocialEmpires1.1.5sec | 2013-04-29 |
| SocialEmpires1.4.05sec | 2013-10-30 |
| **SocialEmpires1.4.07sec** (ve `_fixed`) | **2014-01-31 10:55** |

- 0926b, 0.9 serisinin son derlemesi. 1.4.07'den **yaklaşık 14 ay eski**.
- Arşivde ondan sonra **56 yeni derleme** var (1.0.1-1.0.19, 1.1.0-1.1.9, 1.2.0-1.2.9, 1.3.0-1.3.9 (1.3.7 yok), 1.4.0, 1.4.01-1.4.07). ✔
- Not: bizim de kullandığımız `game_config_20120826.json`, 0926b'den bile eski (Ağustos 2012). ✔
  - NR de bu tabanı kullanıyor; 1.4.07 verisini yamalarla ekliyor.
  - Görevleri ise "daha yeni" olduğu için Çin (4399) config'inden yeniden kurmuş (063a500).

### 4.2 Boyut ve yapı

`betik/swfanaliz.py` ile ölçüldü ✔:

| | 0926b | 1.4.07 | 1.4.07_fixed |
| --- | --- | --- | --- |
| Dosya (CWS, SWF v10) | 3.780.932 | 4.233.956 | 4.288.777 |
| Açılmış | 5.414.065 | 6.176.177 | 6.186.828 |
| DoABC (tek, "frame1") | 2.254.442 | 2.704.123 | 2.714.774 |
| AS3 dize havuzu | 19.587 | 24.052 | 24.282 |
| Sınıf | 1.507 | 1.932 | 1.932 |
| Yöntem | 13.766 | 16.948 | 16.949 |
| DefineEditText (37) | 885 | 1.026 | 1.026 |
| DefineSprite (39) | 1.397 | 1.084 | 1.084 |
| DefineText (11) | 81 | 73 | 73 |

- Kullanılan `flash.*` paketleri aynı (12 paket).
- İkisinde de Stage3D, Worker ve Socket yok.
- 1.4.07'de `fl.*` bileşen çatısının sınıfları eklenmiş: UIComponent, UILoader, BaseButton, LabelButton, FocusManager, StyleManager. ✔

### 4.3 Oyunda neler değişti?

Sınıf farkı: **+570 / −145** (`tarama/sinif_farki.json`). Silinenlerin çoğu yeniden numaralanmış sembol sınıfları (ör. `ButtonOk_178` → `ButtonOk_878`). ✔ Yeni sistemler:
- **Hedefler**:
  - `GoalsManager` ve yaklaşık 60 `Goal*` sınıfı.
  - `MissionsManager` kaldırılmış.
  - 1.0.9'da `MissionsManager` var; 1.0.10'da `GoalsManager` ve `built_id` var. Geçiş 1.0.10'da. ✔
- **PvP**: `PVPManager`, `ShieldManager`, `PopupPvp`, `PopupBuyShields`, `PopupAttackLog`, `PvpPlayerData`, `HudSpyEnemy`.
- Diğer yöneticiler: `UnitPacksManager`, `PopupSoulMixer`, `CollectGameManager` (Hell Forge), `PopupIslandForge`, `PopupNightForgeOffer`, `PopupIvoryOffer`, `DailyBonusManager` ve `PopupNewDailyBonus`, `NestsManager`, `NotificationsManager`, `SpecialDayOfferManager`, `PopupFirstBuy`, `RecruitmentTavernButton`, `PopupCrossDCi` (Dragon City), `LevelUpTip`.
- Birlik ve mezarlık: `BuildingQueueManager` (birlik kuyruğu), `PopupBuyGraveyardCapacity` ve `PopupBuyGraveyardPotion`.
- Durum makinesi: `StateMachine`, `StateAssault`, `StateSpy`, `StateTournament`.
- **Yaklaşık 80 yeni ejderha ve tanrıça davranış sınıfı**: `Iso*DragonUnit` ve `*Delegate`. Örnekler: Ancient, Epic, Savage, Armor, Djinn, Forge ejderhaları, Genesis Colossus, Elemental Goddess.

Komut sabitleri ✔ (`betik/sabitler.py`, `tarama/komutlar.json`):
- `CMD_*` sayısı 156'dan **185**'e çıkmış (farklı değer 154'ten 183'e).
- **Hiçbir komutun adı değişmemiş, hiçbiri kaldırılmamış.**
- Eklenen 29 komut:
  - Kuyruk: `push_queue_unit`, `pop_queue_unit`, `unqueue_unit`, `speed_up_queue`
  - Soul Mixer: `buy_powerups`
  - PvP: `buy_shield`, `reset_shield`, `get_enemy_new`, `begin_attack_new`, `end_attack_new`, `clean_attack_log`, `reply_attack`
  - Mezarlık: `buy_graveyard_capacity`, `reset_potions_received`
  - Hell Forge: `collect_game_*` (5 komut)
  - Viral teklif: `buy_viral_offer_friend`, `buy_viral_offer_all`, `reward_viral_offer`
  - İlk alım: `buy_first_purchase`, `set_first_purchase_timestamp`
  - Diğer: `buy_unit_pack`, `finish_si_recruitment`, `start_quest_new`, `end_tournament_match`, `give_bonus_reward`
- `Config.SERVER_KEY` iki sürümde de `3m0d3pwiupoetn7ysa02`. `URL_SERVER_DVP` değişmiş, ama sunucu adresi flashvar ile verildiği için önemsiz. ◐
- Sunucu uçları: 0926b'deki 25 `.php` ucunun hepsi 1.4.07'de de var. Yeni uçlar:
  - `get_up_data.php`
  - `pvp/web/app.php/pvp/{enemy, attack/begin, attack/end, pool/add, pool/check, pool/del}`

  Turnuva ve kompu uçları yerinde duruyor. ✔
- `skiphash12341` (imza atlama) iki sürümde de var. ✔
- "Cargando" dizesi iki sürümde de tek tane. ✔

---

## 5. Config, kayıt ve protokol uyumluluğu

### 5.1 Config

- Etkin config'ler karşılaştırıldı: bizim yamalar uygulanmış hâli ile NR'nin üç yaması uygulanmış hâli. ✔
  - Eşya sayısı: bizde 1.787, NR'de 1.786. 0.04a'nın `unit_patch.json`'ı 1.4.07 birimlerini zaten getiriyor.
  - Yalnız bizde olan 6 eşya: 9001-9003 (Büyük Ev, Değirmen, Kule), 9101-9103 (Süper birimler).
  - Yalnız NR'de olan 5 eşya: Hell Forge süsleri 2262-2266.
  - Ortak eşyalardan 855'inin alanları farklı: `training_time` 771, Soul Mixer alanları (`pack_*`, `sm_training_time`) 437, `in_store` 62...
- Yalnız NR'de olan config anahtarları ✔:
  - `collect_game`, `collect_game_items`, `pvp_shields`, `recruitment_prices`, `tournament_formations`, `unit_packs`
  - 22 `globals` anahtarı (`PVP_*`, `HONOR_POINT_*`, `SOUL_MIXER_*`, `TOWNHALL_HOUSE_LIMIT`, `QUEST_GOLD_REWARD*`, `GRAVEYARD_CAPACITY`...)
- Bizde `goals` yalnızca 2 kayıtlık bir taslak (`mission_goals.json`). NR `goals.json`'u (206 kayıt) ayrıca yüklüyor. ✔
- Config metinlerinin kapsamı ✔:
  - NR'deki 1.942 `loc` adının 1.514'ü bizim `tr.json`'da var; **428 ad eksik**.
  - Yerine 206 hedefin metni gelir: başlık ve açıklama toplam yaklaşık 23.500 karakter.
  - `0-language_en` metinleri bütünüyle değiştirdiği için, aynı adlı kayıtların İngilizce metni de değişmiş olabilir. ?

### 5.2 Kayıt

- Dosya düzeni aynı: `saves/<uuid>.save.json`. ✔

**Bizim kayıt NR'de**:
- Yüklenir. ◐ (kod okuması; çalıştırılamadı, aşağıya bakın)
- NR, `"version"` alanı olan kaydı "çok eski" sayıyor ve şunları yapıyor (`version.py:338, 498-507`):
  - **Tüm eşyaların zaman damgasını şimdiye çeker** (`_fix_map_items`): üretim ve inşaat sayaçları sıfırlanır.
  - Mezarlığı boşaltır (`_reset_graveyard`).
  - Seviye manasını bir kez daha ekler.
  - `version` alanını siler. ✔ (okuma)
- `playerInfo` içindeki `coins/xp/level/wood/food/stone` alanlarını silip kendi düzenine çevirir. Bizim 53 kaydımızın hepsinde bu alanlar var. ✔
- `gifts` dizisini sözlüğe çevirir (`array_to_dict`). ✔
- Bot alanları (`bot`, `bot_kisi`, `bot_hafiza`) korunur. ◐
- Botlar NR'de sıradan oyuncu gibi giriş listesine ve PvP havuzuna düşer. ◐
- 9001-9103 eşyaları NR config'inde yok; istemcide çökme ya da görünmezlik olur. ?

**NR kaydı bizde**:
- **Kırılır.** ✔ (okuma)
- NR `privateState.gifts`'i `{"id": adet}` sözlüğü olarak tutuyor. Bizim `depo_ekle` / `depo_cikar` ise listeye göre yazılmış (`oyun/komutlar.py:135-151`: `gifts.extend`, `gifts.pop`).
  - Depoya eşya düşen her komutta `AttributeError` beklenir.
- `version` olmadığı için bizim göç zinciri 0.01a'dan başlar: `maps[0].timestamp` sıfırlanır, dart tohumu değişir. ◐
- Hell Forge eşyaları (1530, 2262-2266) bizim config'te yok. ✔

### 5.3 Protokol

- Aynı taşıma: `command.php`, `data=<64 hex hmac>;<json>`. JSON alanları `ts`, `first_number`, `accessToken`, `tries`, `publishActions`, `commands[{cmd,args}]`. Anahtar aynı. ✔
- Fark: NR her yanıtı imzalıyor; biz `get_player_info`'yu düz JSON veriyoruz (`oyun/istemci.py:66-79`).
  - İki istemci de `skiphash12341` bayrağını tanıyor, flashvar iki tarafta da var. ◐
- Komut kapsamı ✔:
  - Biz 0926b'nin 154 farklı komut değerinden 128'ini kaydediyoruz.
  - Kaydetmediğimiz 26 komut (`ally_assist`, `buy_attacks`, `explore`, `hire_worker`, `set_default_town`, `time_ff`...) bizim testteki "istemcinin gerçekten gönderdikleri" listesinde de yok. ◐
  - NR 1.4.07'nin 183 komutundan 123'ünü işliyor; 29 yeni komutun 24'ünü kapsıyor.
- NR'nin işlemediği ama bizim işlediğimiz 35 komut:
  - Eski PvP: `attack_player`, `spy_player`, `buy_attacks_pack`, `buy_spyings_pack`, `buy_pvp_territory`, `clean_attacks`
  - Turnuva kaynakları ve ödülleri: `tournament_*`, `weekly_reward`, `apply_rewards_ranking`
  - `upgrade`, `unlock_building`, `start_heavy_siege`, `set_info_showed`...

  Bunların bir kısmı 1.4.07'de de sabit olarak duruyor. ✔

---

## 6. Göç maliyeti ve riski

### Seçenek A: 0926b'de kal (önerilen ana yol)

- Bütün Türkçe yığın, Android, botlar, turnuva ve kompu olduğu gibi çalışmayı sürdürür. ✔
- 0926b'de çalışan upstream işleri taşınabilir ◐:
  - **Dart tarih kaydırması.** Bizim `darts_items` hâlâ 2012-01-31 → 2012-09-09 tarihli (✔). İstemcinin bunu nasıl gösterdiği ?
  - **Mağazada sınırlı eşya rotasyonu.** Bizim takvim yaklaşımıyla birleştirilebilir.
  - Mod meta doğrulaması.
  - 0926b'yi de ilgilendiren hata düzeltmeleri. Sınanacak adaylar:
    - Baskın köylüleri ve öldürmede desync (2d39fb4, d76d1ae)
    - Ejderha yuvası istismarı (e989ba1)
    - Konak ev sınırları (6f9d792)
    - Dart `0/1` ve `true/false` notu (`version.py`: "false becomes true in the client"). Bizim `darts_*` işleyicileri JSON boolean yazıyor. ?
- 1.4.07 sınıflarına bağlı özellikler bu istemciyle **yapılamaz** ✔ (§4.3): hedefler, Soul Mixer arayüzü, birim paketleri, yeni PvP ve kalkanlar, Hell Forge, yeni günlük ödül, viral teklifler.
  - Bu, bizim ICR-01 yargımızla örtüşüyor: 0926b'de `GoalsManager` yok, `built_id` yok. ✔

### Seçenek B: 1.4.07_fixed'e geç

Bilinen engeller ve iş kalemleri:
1. **Türkçe SWF yaması.** Çalıştırıldı ✔:
   - `swf_yama.turkcelestir` 1.4.07_fixed'te hatasız çalıştı: 521 değişim (0926b'de 582), çıktı 4.291.853 bayt.
   - Bellekte yapıldı, diske ve depoya yazılmadı.
   - DefineEditText: sözlüğün 455 anahtarından **404'ü** hâlâ eşleşiyor.
   - **51 anahtar** 1.4.07'de yok: "Cancel", "Yes", "No", "Save", "Edit", "You win!", turnuva ve savaş sonucu ekranları... Arayüz yeniden yapılmış.
   - DefineText: 50 satırdan 44'ü eşleşiyor.
   - Gömülü yazı tiplerine harf ekleme her iki SWF'de 4 font etiketini değiştirdi.
   - Yeni, harf içeren ve çevrilmemiş **136 aday metin** var (`tarama/yama_ayrinti.json`). Bir kısmı geliştirici dolgusu ("asdfasdf", "Line1", İspanyolca "¿Quieres comprar una poción?").
   - **Yamalı 1.4.07'nin Ruffle'da açılıp açılmadığı denenmedi.** ?
2. **Ruffle uyumu.** ?
   - Upstream bile "Ruffle (Experimental)" diyor.
   - API yüzeyi aynı (§4.2), ama FFDec ile yeniden derlenmiş bayt kodu ve `fl.*` bileşenleri ek risk.
   - NR sunucusunu (bir kopyası, port 5099, yerel Ruffle 0.7.1) çalıştırıp sınamak istedim; izin sistemi upstream kodunun çalıştırılmasını reddetti. Bu nedenle **en büyük belirsizlik doğrulanamadı**.
3. **Sunucu.**
   - 29 yeni komut ve yeni uçlar: `get_up_data`, 6 PvP ucu.
   - Var olan 128 işleyicinin argüman sırası 0926b bayt kodundan çıkarılmıştı. **1.4.07'nin `addCommand` çağrılarından yeniden çıkarılmalı** (adlar aynı, argümanlar değişmiş olabilir). ?
   - Hedefler (206) ve etkinlikler sunucu verisi olarak gerekir.
   - Eğitim sırası farklı: `initial1407.json`, 70e7f5d "Fix tutorial in 1.4.07".
4. **Kayıt göçü.**
   - Yaklaşık 30 yeni `privateState` alanı: `barracksQueues`, `unitPacks`, `collectGame`, `viralOffers`, `shieldEndTime`, `purchasedShields`, `PVPattacksReceived`, `graveyardCapacity`, `potionsReceived`, `collections`...
   - NR'nin `migrate_loaded_save` mantığı örnek alınabilir. Ancak NR, `version` alanı olan kayıtta zaman damgalarını ve mezarlığı sıfırladığı için o kod **olduğu gibi alınmamalı**. ✔
5. **Varlıklar.**
   - İndirme kaynağı main'den NR'ye (sabit SHA ile) taşınmalı: +347 dosya, yaklaşık +48 MB. ✔
   - Çevrimdışı paket listesi (`config/onindirme.tsv`) yeniden üretilmeli. ◐
   - APK'ya Social Point varlığı konmadığı için APK boyutu yalnız SWF farkı kadar değişir (yaklaşık +0,5 MB). ✔ (`araclar/android_paketi.py` belge dizesi)
6. **Çeviri yükü.**
   - 428 yeni `loc` adı ve 206 hedef (yaklaşık 23,5 bin karakter).
   - Yaklaşık 50-90 gerçek SWF metni (136 adayın dolgu olmayanları). ◐
7. **Sürekli değişen ikili.** `_fixed` SWF 15 kez değişti ve yeniden derleniyor. Her güncellemede yama sözlüğümüzün yeniden sınanması gerekir. ✔

Kaba maliyet ◐: Ruffle'da açılış sınaması olumluysa çok haftalık bir iş. Olumsuzsa Ruffle'da bu istemcinin düzeltilmesi gerekir (bilinmeyen süre).

### Seçenek C: ikisini birden sun (NR gibi)

- Sunucuyu `GAMEVERSION`'a göre dallandırmak (NR modeli) en esnek yol. Ama test ve çeviri yükü ikiye katlanır.
- Kararlarımızla da çelişir: "sunucu 0.9.26b'ye sabit", DAG-12, `test_oyun_surumu_sabit`. ✔

### Öneri

1. 0926b ana yol olarak kalsın (A).
2. Önce kısa bir **1.4.07 keşif denemesi** yapılsın. İzin gerekir:
   - Yamalı `1.4.07_fixed`, Ruffle 0.7.1'de bir NR kopyası ya da bizim sunucunun bir kopyasıyla 5050 dışı bir portta açılsın.
   - Ana menüye, haritaya, savaşa ve hedef penceresine ulaşılıyor mu bakılsın.
3. Sonuca göre B'ye ayrı bir dalda karar verilsin.
4. Bu arada A kapsamındaki taşınabilir düzeltmeler ve dart rotasyonu küçük PR'larla alınsın.

---

## 7. Yan bulgular (bizim depo)

- **Bayat belge.** ✔
  - VAR-01 `duzeltildi` (`oyun/fx_yama.py` `p.miniFireball2`'yi türetiyor).
  - Ama `docs/YOL_HARITASI_DURUM.md:119` ("Açık işler"), `docs/GELISTIRME.md:140` ve `docs/FAZ0_OLCUMLER.md:32` hâlâ "arşivde yok, eklenmeli" diyor.
- `README.md`'deki "120'den fazla komutun tamamını" ifadesi:
  - Kayıtlı ad sayısı 128.
  - 0926b'deki 154 komut değerinin 26'sı kayıtlı değil (§5.3); bunlar istemcinin gönderdiği listede yok. ◐
- `docs/YOL_HARITASI_DURUM.md` ve ICR-01'deki "mission_goals daha yeni bir istemciye ait" yargısı doğru:
  - Tür dizeleri 1.0.10'da ortaya çıkıyor.
  - 1.4.07'de 43 türün 43'ü de var, 0926b'de yalnız 6 genel kelime. ✔

---

## 8. Doğrulanamayanlar ve açık sorular

- 1.4.07_fixed'in (yamalı ya da yamasız) Ruffle 0.7.1'de oynanabilirliği: ? (çalıştırma izni reddedildi)
- NR'nin bizim kayıtlarımızı gerçekten yükleyip yüklemediği, 9001-9103 eşyalarına istemcinin tepkisi: ?
- 1.4.07'de mevcut komutların argüman sıraları: ?
- `pvp/pool/*` uçlarının NR'de rotasız olmasının etkisi: ?
- NR statik varlık ucunda yol geçişi riski: ?
