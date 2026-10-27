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

## Bilinen belirsizlikler

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

```bat
python -m pip install -r requirements.txt
python server.py
```

Sonra Flash destekli bir tarayıcı (FlashBrowser) veya Ruffle ile
`http://127.0.0.1:5050/` adresini açın.
