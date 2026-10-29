# Geliştirme Notları

Bu depo, [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors)
koruma projesinin (GPLv3) Türkçeleştirilmiş ve geliştirilmiş bir çatalıdır.

## Temel ilke: istemci yönetir, sunucu kaydeder

Oyun mantığı Flash istemcisinde çalışır. İstemci her değişikliği (bina alma,
toplama, satma...) `command.php` ile bir komut olarak bildirir; sunucu aynı
değişikliği oyuncunun kaydına uygular. Kayıt yeniden yüklendiğinde istemcinin
gördüğü durumla birebir aynı olmalıdır.

Bu yüzden `oyun/komutlar.py` içindeki işleyiciler **kendi kurallarını
uygulamaz**, istemcinin yaptığını taklit eder. Sunucunun bir komutu
reddetmesi ya da farklı bir ödül vermesi, oyuncunun kaynaklarının bir sonraki
açılışta "geri gitmesine" yol açar. Kaynaklar yalnızca eksiye düşmemesi için
sınırlanır.

## Komut protokolü nereden geliyor?

Komut adları ve argüman sıraları oyun SWF'sinin (`SocialEmpires0926bsec.swf`)
AVM2 bytecode'undan çıkarılmıştır. İstemcide her komut şu kalıpla kurulur:

```
Base.Commands.addCommand({cmd: Constants.CMD_X, args: [a0, a1, ...]})
```

Her işleyicinin belge dizesinde argüman sırası yazılıdır, örneğin:

```python
@komut("buy")
def buy(save, a):
    """[id, x, y, yon, kasaba, kaynak_dusme(1=bedava), fiyat_carpani, tur]"""
```

`tests/test_komutlar.py` içindeki `test_istemcinin_tum_komutlari_karsilaniyor`
testi, istemcinin gönderdiği tüm komut adlarının kayıtlı olduğunu denetler.

### Yeni komut eklemek

```python
@komut("komut_adi")
def komut_adi(save, a):
    """[arg0, arg1, ...] - istemcideki karşılığı"""
    h = harita(save, a.tam(2))      # kasaba numarası
    kaynak_ekle(save, h, "g", -100)  # g/w/f/s, c (cash), m (mana)
```

`a.tam(i)`, `a.metin(i)`, `a.ondalik(i)`, `a.json(i)` eksik ya da bozuk
argümanda varsayılan değer döndürür.

### Kayıttaki eşya biçimi

```
[id, x, y, yon, toplama_zamani, seviye, [icindeki_birimler], {ozellikler}]
```

`toplama_zamani` mutlak bir zaman damgasıdır; istemci geçen süreyi
`sunucu_zamani - toplama_zamani` olarak hesaplar.

### İstemcinin okuduğu bazı kayıt alanları

| Alan | Biçim |
| --- | --- |
| `privateState.deadHeroes` | `{"birim_id": adet}` (mezarlık) |
| `privateState.unlockedEarlyBuildings`, `unlockedSkins` | `{"id": true}` |
| `privateState.neighborAssists` | `{"u<pid>": zaman}`: komşuya 24 saatte bir yardım |
| `privateState.collections` | `[[tamam, p1, p2, p3, p4, p5], ...]` |
| `privateState.teams` | `{"tournament": [...], "quest": [...]}` |
| `privateState.helpMap` | görülen yardım pencereleri listesi |
| `maps[n].receivedAssists` | `{"u<pid>": [[x, y, id], ...]}` |
| `maps[n].resourcesTraded` | pazar sayaçları `{"w": n, ...}` |
| `maps[n].warehousedUnits` | birim deposundaki birimler |

## Türkçeleştirme

1. **Config metinleri**: `ceviri/oto_tr.json` + `ceviri/tr.json`
   (`oyun/turkce.py` uygular). Eksik metinleri bulmak/çevirmek için
   `araclar/sozluk_cikar.py` ve `araclar/oto_ceviri.py`.
2. **SWF içindeki sabit yazılar**: `ceviri/arayuz_tr.json`.
   - `metin_alanlari`: DefineEditText başlangıç metinleri (HTML etiketleri
     çıkarılmış hâli anahtardır).
   - `statik_yazilar`: DefineText yazıları; satırlar `|` ile ayrılır ve
     satır sayısı korunmalıdır.
   `oyun/swf_yama.py` SWF'yi ilk istekte yamalar ve
   `download_assets/tr/` altında saklar. Sözlük ya da yama kodu değişince
   önbellek kendiliğinden yenilenir (`YAMA_SURUMU`).
3. **Yazı tipleri**: SWF'ye gömülü Arial Rounded / Eras Bold yazı
   tiplerinde `ğ Ğ İ ş Ş` yoktur. `oyun/swf_font.py` bu harfleri
   `assets/fonts/tr_*.swf` içinden ekler ve statik yazıların glif
   numaralarını yeniden eşler.

Resim olarak çizilmiş yazılar ("BUILD", "ADD ALLY", "Add Cash") bu yolla
çevrilemez.

## Ayarlar ve veriler

- `ayarlar.json`: `zaman_olcegi` (oyun hızı) ve `dunya` (bot simülasyonu).
- `oyun/denge.py`: PvP ganimet oranı, kupa ve saldırı hakkı.
- `saves/`: oyuncu ve bot kayıtları (depoya girmez). Hiç bot yoksa sunucu
  ilk açılışta 50 bot üretir (`araclar/bot_koy_uret.py`).
- `download_assets/`: indirilen oyun varlıkları ve Türkçe SWF önbelleği.

## Testler

```bat
python -m unittest discover -s tests
```

`tests/ortak.py`, `SE_KAYIT_DIZINI` ortam değişkeniyle testlerin geçici bir
kayıt klasörü kullanmasını sağlar.

## Bilinen eksikler

- İstemcinin çağırdığı `kompu_try.php`, `kompu_hurry_up.php`,
  `register_found_item.php`, `clean_assaults.php`, `report_error.php` uçları
  henüz yok; istekler `saves/http_gunlugu.jsonl` dosyasına yazılır.
- `get_continent.php` ve turnuva yanıtlarının alan adları istemci koduyla
  doğrulanmadı.
- Ruffle'da birimler yere tıklanarak hareket ettirilemiyor (istemci komut
  göndermiyor; orijinal İngilizce SWF'de de aynı). Flash Player'da bu sorun
  yaşanmaz.
- `fx/p.miniFireball2.swf` orijinal arşivde de yok.
