# Geliştirme Notları

Bu depo, [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors)
projesinin (GPLv3) yerel bir çalışma kopyasıdır. Buradaki değişiklikler
`alpha 0.05` sürümüne hazırlanıyor.

## Bu sürümde yapılanlar

### Hata düzeltmeleri
- **`CMD_RESURRECT_HERO`**: tanımsız `map` ve `id` değişkenleri yüzünden
  kahraman diriltme `NameError` ile çöküyordu; birim artık doğru haritaya
  ekleniyor.
- **Eksik varlık indirme**: `server.py` içindeki CDN yedeğinde f-string
  eksikti; eksik `.swf`/görseller artık `download_assets/` altına
  indirilebiliyor.
- **Atomik kayıt**: `sessions.save_session` önce `.tmp` dosyasına yazıp
  `os.replace` ile taşıyor; önceki sürüm `.bak` olarak saklanıyor. Oyun
  kayıt sırasında çökse bile eski kayıt bozulmuyor.
- **Yedekleme**: `backup_session` artık `saves/backups/` altında zaman
  damgalı kopya tutuyor (oyuncu başına son 10 yedek).
- **Görev tekrarı**: aynı görev birden fazla kez tamamlanıp ödülü birden
  fazla kez alınabiliyordu; `completedMissions` / `rewardedMissions`
  listeleri artık idempotent.
- **Komut izolasyonu**: bir komut hata verirse aynı paketteki diğer
  komutlar ve kayıt yazımı etkilenmiyor; hata ayrıntısı konsola düşüyor.
- **İstek alanları**: `language` ve `spdebug` alanları zorunlu olmaktan
  çıkarıldı (curl/test istekleri 500 vermiyor).
- **Toplama sayacı**: `collect` sonrası eşyanın zaman damgası artık
  güncelleniyor; kayıt yeniden yüklenince bina anında "hazır" görünmüyor.
- **Boş komut paketleri**: istemci bazen `collect_new []` gibi eksik
  argümanlı komut gönderiyor; bu artık hata üretmeden atlanıyor.
- **Komut günlüğü**: her komut için dosya açmak yerine paket başına tek
  yazma yapılıyor (yüzlerce komutluk eğitimde hız kazancı).
- **Maksimum seviye hatası (oyun kilidi)**: `get_level_from_xp`, XP son
  seviyenin eşiğine eşit/aşkın olduğunda 0 dönüyordu. "Maksimum seviye"
  sonrası oyuncu 0. seviyeye düşüp istemci kilitleniyordu. Fonksiyon son
  seviyeyi döndürecek şekilde düzeltildi; ayrıca kayıt yüklenirken
  seviye ile XP uyuşmuyorsa seviye otomatik normalize ediliyor.
- **Beklenmeyen hatalar**: sunucu hataları artık
  `saves/sunucu_hatalari.log` dosyasına yazılıyor; açılış hataları da
  aynı dosyaya düşüyor.

### Yeni komutlar
| Komut | Davranış |
| --- | --- |
| `upgrade` | Binayı `upgrades_to` zincirine göre yükseltir; maliyet ve XP config'ten alınır |
| `trade_resource_b` | Pazar: kaynak alım/satımı, fiyat `MARKET_*` ayarlarına göre hesaplanır |
| `set_resources_traded` | Pazar fiyat sayaçlarını istemciden senkronize eder |
| `add_items_store`, `store_add_items` | Depoya eşya ekler (JSON veya düz argüman) |
| `place_stored_item` | Depodaki eşyayı haritaya yerleştirir |
| `sell_stored_item` | Depodaki eşyayı %5 iade ile satar |
| `buy_stored_item_cash` | Depo eşyasını cash ile satın alır |
| `attack_player` | Hedef oyuncuyu doğrular, saldırıyı başlatır |
| `end_attack` | Savaş sonucunu iki tarafa uygular (ganimet, kayıp, rapor) |
| `clean_attacks` | Savunma raporlarını temizler |
| `set_attack_team` | Saldırı takımını kaydeder |
| `spy_player` | Casusluk komutu (şimdilik yalnızca günlük) |

### Kayıt biçimi
`version.py` 0.05a'ya yükseltildi. 0.04a kayıtları açılışta otomatik
migration'dan geçer:
- `privateState.lastUpgrades` (yoksa `[]`)
- `privateState.marketTimestamp` (yoksa `0`)
- her haritada `resourcesTraded` (yoksa `{}`)

## Protokol notları (önemli)

İstemci (Flash/SWF) komut argümanlarını sıra garanti etmeden gönderiyor.
Bu yüzden sunucu argümanları **değer rolüne göre** eşliyor:

- `upgrade`: argümanlar içinde eşyanın `(id, x, y)` üçlüsü aranır. İstemci
  mevcut bina yerine hedef binanın kimliğini gönderse bile yalnızca
  koordinatlardan bulunur. Fiyat çarpanı gönderilirse (ör. `"0.5"`)
  uygulanır; yoksa `1.0`.
- `trade_resource_b`: JSON nesnesi (`{"resource": "w", "amount": 100,
  "action": "buy"}`) veya düz argümanlar kabul edilir. Fiyat sunucuda
  hesaplanır:
  - alım: `taban * (1 + artış * traded)`
  - satım: `taban * satış_oranı * (1 - artış * -traded)`
  - sayaç `MARKET_PERIOD_HOURS` saatte sıfırlanır.
- Depo komutları JSON (`{"id": 5, "count": 2}`) veya `[id, adet]` çifti
  kabul eder.

**Gerçek argümanları görmek için:** oyun her komutu
`saves/komut_gunlugu.jsonl` dosyasına yazar. Oynarken bu dosyaya bakarak
protokolü doğrulayabilirsiniz.

## Oyun hızı (zaman ölçeği)

Oyunun yavaş hissettiren kısmı üretim/inşaat süreleri. Bunlar istemciye
gönderilen `game_config` içindeki `activation` / `expiration` alanlarından
geliyor; sunucu bu süreleri yönetmiyor.

`zaman_olcegi.json`:

```json
{ "time_scale": 3.0 }
```

- `3.0` → süreler 3 kat kısalır (6 saatlik üretim 2 saat olur)
- `1.0` → normal hız
- `TIME_SCALE` ortam değişkeni dosyadaki değeri ezer.

Değiştirdikten sonra sunucuyu kapatıp `baslat.bat` ile yeniden açın;
config oyun açılışında istemciye gönderiliyor. Sunucudaki ve kayıttaki
değerler değişmez, sadece istemcinin gördüğü süreler bölünür.

### Ek performans iyileştirmeleri

- Flask `threaded=True` ile çalışıyor: Flash'ın aynı anda istediği
  yüzlerce SWF/JPG paralel sunuluyor (tek iş parçacığında sırayla
  sunuluyordu).
- Statik dosyalar 1 gün önbellekleniyor (`SEND_FILE_MAX_AGE_DEFAULT`);
  ikinci açılışta varlıklar yeniden indirilmiyor.
- Kayıt yazımı `save_lock` ile kilitlendi; eşzamanlı komutlar birbirini
  ezmiyor.

## Hile paneli (yalnızca bu bilgisayar)

Sunucu açıkken `http://127.0.0.1:5050/cheat` adresini açın (oyun sayfasındaki
"hile paneli" bağlantısı da oraya gider). Panelden:

- odun / taş / yemek / altın / cash ekleyebilir,
- seviye atlatabilir (maksimuma kadar),
- eğitimi atlayabilir,
- anlık yedek alabilirsiniz.

Güvenlik: yalnızca `127.0.0.1`'den, JSON gövdesiyle ve aynı kökenden gelen
istekler kabul edilir; başka bir web sitesi paneli çağıramaz.

## Otomatik yedekler

Sunucu açıkken `backups_daily` iş parçacığı saatte bir kontrol eder ve her
gün için `saves/gunluk_yedek/YYYY-AA-GG/` klasörüne o günkü kayıtları
kopyalar. Son 14 gün saklanır. Anlık yedek için hile panelindeki
"Şimdi yedek al" düğmesi `saves/backups/` altına zaman damgalı kopya atar.

## PvP (oyuncuya saldırı)

Komşu bir oyuncuya saldırınca istemci `attack_player`, savaş bitince
`end_attack` gönderiyor. Sunucu `end_attack` içindeki JSON'u iki tarafa
uyguluyor:

- saldıran: `resources` içindeki altın/XP kazancı,
- savunan: `resources_victim` kadar kaynak kaybı (mevcut kaynağın üstüne
  çıkamaz),
- savunanın `attacksReceived` listesine saldıranın adı/seviyesiyle rapor,
- saldıranın `attacksSent` listesine hedef kaydı.

Saldırı hakkı config'te `ATTACKS_PERIOD_MAX = 3` / `ATTACKS_PERIOD_HOURS = 6`;
sunucu şimdilik yalnızca uyarı basıyor, engellemiyor.

> Not: `end_attack` gövdesi gerçek oyundan alınan log ile doğrulanmalı.
> Bir komşuya saldırıp `saves/komut_gunlugu.jsonl` dosyasına bakmak yeterli;
> alan adları farklıysa handler'ı ona göre daraltırız.

## Ayrı web paneli hakkında

Ayrı bir `/dunya` paneli denendi; oyunun kendi sanat yönüne ve
atmosferine uymadığı için **kaldırıldı**. Dünya simülasyonu görünmez
şekilde çalışmaya devam ediyor; sonuçları oyun içi saldırı/savunma
raporlarında görünüyor.

## Kardeşlik Loncası (arkadaş işçi çözümü)

Orijinal oyunda bazı binalar (Zeppelin Tower, değirmenler, kiliseler…)
**arkadaşların işçi olarak gelmesini** bekliyor; tek kişilik sunucuda
arkadaş olmadığı için bu binalar yarım kalıyordu. Çözüm iki katmanlı:

- `config/game_config_*.json` içindeki `social_items` listesi bu
  binaların `worker_cost` (gereken işçi) ve `workers` (işçi adları)
  bilgisini veriyor. Örnek: Zeppelin Tower → 5 işçi.
- `buy_si_help`, `finish_si` ve `hire_worker` komutları binayı **anında
  usta işçilerle tamamlanmış** hale getiriyor (kayıt 8 elemanlı, işçi
  listesi dolu).
- `world.py` içindeki **Kardeşlik Loncası** her turda, oyuncunun yarım
  kalmış bir sosyal binasını otomatik tamamlıyor; panele
  “Kardeşlik Loncası … binaya usta işçi gönderdi” olayı düşüyor.

Ayrıca bir bot kaydıyla giriş yapılırsa sunucu o kaydı **oyuncuya
devrediyor** (`playerInfo.bot` silinir). Böylece dünya simülasyonu aynı
kaydı yazarken oluşan çakışma/donma engelleniyor.

## Dünya Gezgini (ada haritası)

Eksik olan uçlar eklendi:

- `get_continent.php` → adadaki **7 bölgeyi** (posicion, user_id, name,
  nivel, pic) döndürür; ada numarası 99.
- `get_user_world.php` → `world_id`, `continentNumber`, `island`.

Böylece World Explorer ekranındaki boş harita yerine bölgeler ve
üzerlerinde oyuncular görünmeli.

> Önemli: Flash istemcisi bu dinamik uçları **POST** ile çağırıyor. İlk
> sürümde uçlar yalnızca GET kabul ettiği için 405 dönüyor ve harita boş
> kalıyordu. Artık `get_continent.php`, `get_user_world.php` ve
> `get_continent_ranking.php` hem GET hem POST kabul ediyor.
> Gelen istek ve dönen gövde `saves/http_gunlugu.jsonl` dosyasına yazılır.

## Bot profil resimleri

49 bot için Wikipedia/Wikimedia Commons'tan **gerçek, AI üretilmemiş**
portre ve tarihî resimler indirildi (`tools/bot_pp_uret.py`). Dosyalar
`templates/img/profile/bot_<ad>.jpg|png` altında; kaynak listesi
[RESIM_KAYNAKLARI.md](RESIM_KAYNAKLARI.md) dosyasında.

Bot üreticisi yeni köylerde mevcut resmi otomatik atar; resmi olmayanlar
varsayılan profile döner.

## PvP kuralları (tamamlandı)

- 6 saatte 3 saldırı, aynı hedefe tekrar saldırı yasağı.
- **İntikam istisnası**: hedef son 24 saatte sana saldırdıysa aynı hedefe
  tekrar saldırabilirsin.
- **Kalkan**: `shield_until` aktifken saldırı reddedilir.
- **Kupalar**: kazanan +10, kaybeden -5 (rapor içindeki `trophies` alanı
  varsa o kullanılır). `win_trophy` komutu da kupa ekler.
- Ganimet kaynak başına 100.000 ile sınırlı; savunanın mevcut
  kaynağından fazlası alınamaz.
- Savunma raporları son 50 kayıtla sınırlı; `clean_attacks` temizler.

## Bot köyleri (PvP için rakip üretme)

PvP listesi boşsa yapay komşular üretilebilir:

```bat
python tools\bot_koy_uret.py 10
```

- Her bot `saves/<uuid>.save.json` olarak yazılır; sunucu açılışında normal
  oyuncu kaydı gibi yüklenir.
- 10 bot: Kara Han, Bozkurt Bey, Demir Yay, Gökbörü, Alp Er Tunga,
  Kül Tigin, Bilge Kağan, Tomris Hatun, Modu Han, Attila.
- Seviyeler 5–45 arasında; sur, kule, kışla ve savunma birlikleri var.
- Komşu listesinde ve kıta sıralamasında görünürler, saldırılabilirler.
- Silmek için `saves` klasöründeki bot `.save.json` dosyalarını silin.
- Yeniden üretmeden önce eski bot dosyalarını silin (aynı isimler yeni
  UUID ile gelir).

## Orijinal PvP kuralları (araştırma notları)

Yaşayan dünya ve PvP davranışı, orijinal oyunun kurallarına göre
ayarlandı. Kaynaklar:

- SuperCheats, “Attacking Other Players”: dünya haritası **6. seviyede**
  açılıyor; **6 saatte 3 saldırı** hakkı var; **aynı imparatorluğa tekrar
  saldırılamıyor**; tüm ordu savaşa gidiyor, hedef Belediye Binası’nı
  yıkmak. <https://www.supercheats.com/guides/social-empires/attacking-other-players>
- Unofficial Social Empires Wiki, “PVP”: kaynak başına ganimet yaklaşık
  **100.000** ile sınırlı; cash yağmalanamıyor; kalkanlar belirli gün
  koruma sağlıyor; saldırı/savunma modları var.
  <https://unofficialsocialempires.fandom.com/wiki/PVP>
- Oyunun kendi `localization_strings` metinleri (birincil kaynak):
  “All of your Army goes to the battle”, “Destroy the Town Hall to WIN”,
  “Attacks left”, “you will get 3 more in #0#”, “Take Revenge!!”,
  “showing only last 10 attacks”, ada fetihleri ve savunma stratejileri.

### Bunlardan koda geçenler

- Botlar ve oyuncu için **6 saatte 3 saldırı** sınırı.
- **Aynı hedefe 6 saat içinde ikinci saldırı** reddediliyor.
- **6. seviyenin altındaki köyler** hedef alınmıyor.
- Ganimet **kaynak başına 100.000** ile sınırlı; cash'e dokunulmuyor.
- Oyuncunun `CMD_SET_STRATEGY` seçimi (Defensive / Mid Defensive /
  Mid Aggressive / Aggressive) savunma gücünü etkiliyor.
- **Kalkan** (`privateState.shield_until`) aktifken botlar oyuncuya
  saldıramıyor; hile panelinden 12 saatlik kalkan verilebiliyor.
- Botların hedef seçimi öfke (grudge) ve güç oranına göre ağırlıklı;
  aynı hedefi tekrar tekrar dövmesini engelleyen hafıza tutuluyor.

## Yaşayan dünya (canlı simülasyon)

Sunucu açıkken bot köyleri boş durmuyor: `world.py` arka planda her
`tick_saniye` saniyede bir dünyayı ilerletiyor.

- Her bot kaynak üretir, ara sıra birlik basar ve seviye atlar.
- Botlar birbirine ve oyuncuya akın düzenler; savaş sonucu iki tarafın
  kayıtlarına işlenir (birlik kaybı, ganimet, `attacksReceived` raporu).
- Oyuncuya gelen saldırılar oyun içindeki savunma raporlarında görünür.
- Tüm değişiklikler normal `.save.json` dosyalarına yazılır.

### Ayar: `dunya.json`

```json
{
  "aktif": true,
  "tick_saniye": 60,
  "saldiri_olasiligi": 0.35,
  "oyuncuya_saldiri": 0.2,
  "olay_saklama": 200
}
```

- `aktif: false` → simülasyon tamamen kapanır.
- `tick_saniye` → tur süresi (sn). Küçültmek dünyayı hızlandırır.
- `saldiri_olasiligi` → bir botun tur başına akın düzenleme olasılığı.
- `oyuncuya_saldiri` → hedefin oyuncu olma olasılığı.

Simülasyon `tick_saniye` aralığıyla kendiliğinden ilerler.

## Türkçe sürüm (devam ediyor)

Sunucu, istemciye gönderdiği `game_config` metinlerini dile göre
değiştirebiliyor. `language=tr` geldiğinde:

- 167 arayüz metni (düğmeler, ipuçları, eğitim, hata mesajları),
- 100 seviye adı (Köle → Fatih),
- 29 kategori adı (Köy, Savunma, Ordu…)

`ceviri/tr.json` içinden Türkçeleştiriliyor. Oyun sayfaları da artık
Türkçe ve Flash değişkeni `language=tr` gönderiyor.

Kapsam dışı (sıradaki adımlar): eşya adları (~1.500), görev metinleri
(~230) ve uzun yardım metinleri. Çeviri eklemek için `ceviri/tr.json`
dosyasına `anahtar: "Türkçe metin"` satırı eklemek yeterli; anahtarlar
`ceviri/sozluk.csv` içinde listeli.

## Turnuvalar (yeni)

`turnuva.py` + `/tournaments/*` uçları:

- 4 koltuklu turnuva; boş koltuklar gerçek bot köyleriyle dolar.
- Herkes herkesle bir maç (6 maç); **bot-bot maçları otomatik** oynanır.
- İnsan oyuncu maçlarını `start_tournament_match` / `finish_tournament_match`
  ile oynar; tüm maçlar bitince turnuva kapanır.
- Kazanan: +30 kupa, +2 cash; ödül yalnızca bir kez verilir.
- İkinci insan oyuncu bekleyen turnuvada bot koltuğuna katılabilir.
- Durum bellektedir; sunucu yeniden başlarsa turnuvalar sıfırlanır.
- İstek/yanıtlar `saves/turnuva_gunlugu.jsonl` dosyasına yazılır.

## Ada fetih (yeni)

`ada.py` + `get_continent.php` / `get_user_world.php`:

- Her adada **7 bölge**, her bölgede bir bot köyü.
- Bölgedeki botu yenince bölge fethedilir (`ada:posicion` anahtarı).
- 7/7 olunca: +1 cash, +50 kupa, sonraki adaya geçiş (ada numarası artar).
- Yanıtlar `ada`, `progress.done/total`, `conquered` ve tüm `continent*`
  alanlarını güncel ada numarasıyla döndürür.
- 7'den az bot varsa ada üretilmez (yanlış fetih sayımı olmaz).

## Haftalık sezon (yeni)

`sezon.py`:

- Hafta başında kupa sıralamasındaki ilk üçe cash ödülü (5/3/1).
- Kupalar %60'a yumuşatılır.
- Durum `saves/sezon.json`; atomik yazılır, yazma başarısızsa ödül verilmez.
- Değişen kayıtlar `save_session` ile diske yazılır.

## İçerik ve sistemler (tamamlandı)

- **Görevler** (`gorev.py`): tamamlama, ödül, sıfırlama; ödül yalnızca
  tamamlanmış görev için ve bir kez. Sıfırlama ödül hakkını geri vermez.
  Haftalık 3 görev seçilir; hepsi bitince 1000 coin + 1 cash.
- **Mağaza** (`magaza.py`): teklif paketleri (iç içe eşya grupları dahil),
  cash ile depo eşyası, cash borsası, saldırı/casusluk hakkı, depo
  kapasitesi (azami sınır), PvP bölge/ada alımı, kilit açma.
  Fiyat çarpanı 0–1 aralığına sıkıştırılır; negatif/ sıfır reddedilir.
- **Koleksiyonlar** (`koleksiyon.py`): `costs` alanı birim bazında uygulanır;
  önce depo, sonra ordu birimleri tüketilir; kategori başına bir kez ödül.
  Birim tamamlama yalnızca geçerli ve sahip olunan birimler için.
- **Etkinlikler** (`etkinlik.py`): günlük bonus (config’ten, günde bir),
  Pazartesi bonusu (haftada bir), geri dönüş (20 saatte bir), hazine
  (günde bir). İstemcinin gönderdiği coin/cash değerlerine güvenilmez.
- **Başarımlar** (`basari.py`): 8 başarım; görev, seviye, inşa, PvP,
  kupa, ada ve koleksiyon koşulları; bir kez ödül.
- Yeni uçlar: `get_achievements.php`, `get_store.php`,
  `get_collections.php`, `get_events.php`.

## Sosyal döngü (tamamlandı)

- Komşu yardımı: günde 20, aynı komşuya günde bir; yardım edene 100 coin + 5 XP,
  alıcının `receivedAssists` listesine kayıt (son 100).
- Hediye: `send_gift.php` (günlük 20, depodan düşer, alıcıya yazılır, son 100).
- `get_social.php` günlük limitleri ve komşu sayısını döndürür.
- Alıcı kayıtları `save_session` ile diske yazılır.

## İstemci uçları

- Turnuva uçları hem `/tournaments/...` hem de istemcinin çağırdığı
  `/dynamic.../srvempires/tournaments/...` altında kayıtlı.
- `get_tournament_info` aktif oda yoksa kilit altında tek bir bekleyen oda açar.
- Ada slotları `ada:uid` anahtarıyla kararlı; `user_id` sayısal, `uid` UUID.
- `get_game_config` istemci `language=en` gelse de Türkçe metin gönderir.

## Türkçe kapsamı (tamamlandı)

- Boş olmayan **tüm** metinler çevrildi: eşya adları + başarım açıklamaları,
  görev başlıkları/açıklamaları, arayüz/yardım, keşif eşyaları, seviye
  ipuçları, sosyal işçi adları, komşu yardımı metinleri.
- `ceviri/oto_tr.json` (makine çevirisi) + `ceviri/tr.json` (elle düzeltme);
  elle çeviri önceliklidir. `turkce.dogrula` yer tutucu/HTML/newline
  bozulursa çeviriyi uygulamaz.

## Sağlamlaştırma (yeni)

- `/saglik` ve `/saglik/hazir` uçları: sürüm, oyuncu sayısı, çalışma süresi,
  dünya tick'i. `baslat.bat` artık tarayıcıyı açmadan önce `/saglik/hazir`
  yanıtını bekler.
- `USERID` doğrulaması: yalnız harf/rakam/`-`/`_`, en fazla 64 karakter;
  `../` gibi yol kaçışları kayıt yazımında reddedilir.
- `tests/test_http.py`: Flask test istemcisiyle 7 uçtan uca test
  (sağlık, giriş, oyun sayfası, Türkçe/ASCII config, ada, turnuva, sosyal).

## Bilinen belirsizlikler

- `collect_new` aslında toplama komutu (`CMD_COLLECT`), `next_step` ise
  ejderha adımı (`CMD_NEXT_DRAGON_STEP`); ikisi de işleniyor. Yalnızca
  `activate` komutunun kayıtta neyi değiştirdiği henüz bilinmiyor.
- `hire_worker` ve `increase_population`: kayıtta hangi alanın
  güncellendiği doğrulanmadığı için şimdilik yalnızca günlüğe yazılıyor.
  Yanlış alanı bozmamak için bilinçli olarak değişiklik yapılmıyor.
- Yükseltme bedeli **hedef binanın maliyeti** varsayımına dayanıyor.
  İstemci farklı bir çarpan gönderirse o kullanılır.
- PvP saldırıları, turnuvalar, kıta sıralaması ve survival hâlâ eksik
  (bkz. ana yol haritası).

## Test

Flask/jsonpatch kurulu olmasa da çalışan birim testleri:

```bat
python tests\test_komutlar.py
```

Kapsam: yükseltme (id/konum/hedef-id varyantları, yetersiz kaynak),
pazar alım-satım ve limitler, depo ekle/yerleştir/sat, kahraman diriltme,
görev idempotency, atomik kayıt + yedek, 0.04a → 0.05a migration.

## Oyunu çalıştırma

En kolay yol: depodaki **`baslat.bat`** dosyasına çift tıklayın. Betik
eksik Python paketlerini kurar, sunucuyu başlatır ve tarayıcıyı açar.

Elle:

```bat
python -m pip install -r requirements.txt
python server.py
```

Sonra Flash destekli bir tarayıcı (FlashBrowser) veya Ruffle ile
`http://127.0.0.1:5050/` adresini açın. Flash içerik için normal Chrome
yetmez; FlashBrowser ya da eski bir Flash Player gerekir.
