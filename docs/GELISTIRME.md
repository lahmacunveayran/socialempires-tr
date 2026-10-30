# Geliştirme Notları

> İşlerin kaydı ve denetimi için görev kitabı: `docs/gorev/00-CEKIRDEK.md` (bulgular `docs/gorev/BULGULAR.json`,
> kapılar `docs/gorev/KAPILAR.md`, oturum notları `docs/devlog/`).

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

1. **Config metinleri**: `ceviri/tr.json` (`oyun/turkce.py` uygular).
   Eksik metinleri bulmak için `araclar/sozluk_cikar.py`. Üslup:
   oyuncuya "sen" diye hitap edilir, noktalı virgül ve tire kullanılmaz,
   terimler tutarlıdır (Konak, Okçu Ocağı, Bıçkıhane, Nakit, Sefer, Hedef).
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

## Servis istekleri ve imza

Komutlar dışındaki bazı istekler (büyücü iksirleri, turnuvalar, hata
bildirimi) `data` alanında `<imza>;<json>` gönderir ve yanıtı da aynı biçimde
bekler. İmza, istemcideki `Config.SERVER_KEY` ile HMAC-SHA256'dır
(`oyun/istemci.py` içinde `imzali()`). Yanıtın JSON'u `{"result": ..., "data": ...}`
biçimindedir; istemci yalnızca `data`'yı okur.

## İçerik

- `config/tema_setleri.json`: eski etkinliklerin mağazaya açılan setleri.
  Yalnızca sprite ve küçük resmi arşivde eksiksiz olan eşyalar listelenir.
- `config/patch/kompu.json`: Büyücünün İksirleri teklifi (ödüller, büyücü
  bedelleri, metinler). Teklifin kimliği ve başlangıcı 30 günlük döneme göre
  `oyun/config.py` içinde hesaplanır.

## Bilinen eksikler

- Ruffle'da yere tıklama işlenmiyor: birimler yürütülemiyor, binalar
  haritaya bırakılamıyor (orijinal İngilizce SWF'de de aynı). Saldırı ve
  turnuva savaşları bu yüzden Ruffle'da oynanamıyor; Flash Player'da sorun yok.
- Oyuncu fotoğrafları boş görünür (istemci Facebook adresinden yüklüyor).
- Haftalık turnuva (tür 8) kapalı.
- `fx/p.miniFireball2.swf` orijinal arşivde de yok; `oyun/fx_yama.py` onu oyunun
  kendi `p.fireBall` efektinden türetir (VAR-01).

## Görseller

Sayfaya ya da oyuna kendi üretilmiş görsel (çizim, SVG illüstrasyon, yapay
zekâ resmi, emoji, CSS ile çizilmiş figür) eklenmez; oyunun ruhunu bozar.
Gerekirse yalnızca oyunun kendi görselleri olduğu gibi kullanılır (oyun
varlıkları ve `templates/img/`).
