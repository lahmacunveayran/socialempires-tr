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
