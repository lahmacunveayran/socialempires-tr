![Social Empires](templates/img/logo.png "Social Empires")

# Social Empires Türkçe

[![Testler](https://github.com/lahmacunveayran/socialempires-tr/actions/workflows/tests.yml/badge.svg)](https://github.com/lahmacunveayran/socialempires-tr/actions/workflows/tests.yml)
[![Lisans: GPLv3](https://img.shields.io/badge/lisans-GPLv3-blue.svg)](LICENSE)

Social Empires'ı **Türkçe** oynamak ve yerel olarak geliştirmek için hazırlanmış
bir topluluk çatalı. Oyun, Flash istemcisi ile konuşan bir Python/Flask
sunucusu üzerinde çalışır; Facebook hesabı gerekmez; internet yalnızca oyun varlıklarını ilk kez
indirmek için gerekir.

> Bu proje Social Point ile bağlantılı değildir. Yalnızca kültürel miras
> amaçlı bir koruma çalışmasıdır. Orijinal proje:
> [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors).

---

## Özellikler

- **Tam Türkçe**: eşya, bina, birim, görev, arayüz, yardım ve başarım
  metinleri; resmî Türkçe fontlarla `ş, ğ, İ, ı, ç, ö, ü` desteği.
- **PvP**: 3 saldırı / 6 saat, ganimet, savaş raporları, kalkan, intikam,
  kupalar ve savunma raporları.
- **50 bot köyü** (ilk açılışta otomatik üretilir): gerçek portreler, kişilikler, öfke hafızası ve dünya
  simülasyonu.
- **Turnuvalar**: 4 kişilik odalar, bot doldurma, otomatik bot maçları ve
  ödüller.
- **Ada fetih**: 7 bölgeli adalar, fetih takibi ve ödül (sunucu tarafı).
- **Haftalık sezon**: kupa sıralaması, ödüller ve sezon sıfırlama.
- **Görevler, mağaza, koleksiyonlar, etkinlikler ve başarımlar**.
- **Sosyal döngü**: komşu yardımı ve hediye gönderme (günlük limitli).
- **Yeni içerik**: Büyük Ev, Büyük Değirmen, Büyük Kule; Süper Şövalye,
  Süper Okçu, Süper Kılıçlı ve yeni mağaza paketleri.
- **Güvenli kayıt**: atomik yazım, `.bak` yedeği, günlük yedekler ve
  `USERID` doğrulaması.

---

## Kurulum (Windows)

1. **Python 3.12+** kurulu olsun.
2. Depoyu indirin veya klonlayın:
   ```bat
   git clone https://github.com/lahmacunveayran/socialempires-tr.git
   cd socialempires-tr
   ```
3. `baslat.bat` dosyasını çalıştırın.
   - Gerekli Python paketleri (`flask`, `jsonpatch`) eksikse otomatik kurulur.
   - Sunucu hazır olduğunda tarayıcı otomatik açılır:
     <http://127.0.0.1:5050/>
4. Giriş ekranından bir köy seçin veya yeni imparatorluk kurun.

**Oyun varlıkları (SWF, görsel, müzik):** ~1,3 GB oldukları için depoda
tutulmaz (yalnızca Türkçe fontlar depodadır). İlk açılışta eksik dosyalar
[AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors)
deposundan otomatik indirilip `download_assets/` altında saklanır; bu yüzden
ilk açılış için internet gerekir. Hepsini bir kerede indirip internetsiz
oynamak için:

```bat
python varliklari_indir.py
```

**Bot köyleri:** `saves/` altında hiç bot yoksa sunucu ilk açılışta 50 bot
köyü üretir (PvP, ada fetih ve turnuvalar bunlara ihtiyaç duyar). Yeniden
üretmek için: `python tools\bot_koy_uret.py`.

**Flash desteği:** Flash uyumlu bir tarayıcı ya da Ruffle gerekir.
Ayrıntılar: [FLASH.md](FLASH.md). GNU/Linux: [LINUX.md](LINUX.md).

---

## Oynanış

- Sunucu: `http://127.0.0.1:5050/`
- Sağlık kontrolü: `http://127.0.0.1:5050/saglik`
- Oyunu kapatmak için sunucu penceresinde `Ctrl+C` kullanın.

### Türkçe

Oyun içi metinler `ceviri/oto_tr.json` (makine çevirisi) ve
`ceviri/tr.json` (elle düzeltmeler) dosyalarından gelir. Türkçe fontlar
`assets/fonts` altındadır; istemciye `language=tr` gönderilir.

---

## Geliştirme

```bat
python tests\test_komutlar.py   :: birim testleri
python tests\test_http.py       :: HTTP uçtan uca testleri
```

- Geliştirme notları ve komut protokolü: [docs/GELISTIRME.md](docs/GELISTIRME.md)
- Katkı rehberi: [CONTRIBUTING.md](CONTRIBUTING.md)
- Güvenlik politikası: [SECURITY.md](SECURITY.md)

### Proje yapısı

| Yol | Açıklama |
| --- | --- |
| `server.py` | Flask sunucusu, istemci uçları |
| `command.py` | Oyun içi komutlar |
| `sessions.py` | Kayıt yükleme/kaydetme, yedekler |
| `world.py` | Bot ekonomisi ve dünya simülasyonu |
| `turnuva.py`, `ada.py`, `sezon.py` | Turnuva, ada fetih, haftalık sezon |
| `gorev.py`, `magaza.py`, `koleksiyon.py`, `etkinlik.py`, `basari.py` | Oyun sistemleri |
| `sosyal.py` | Komşu yardımı ve hediyeler |
| `config/` | Oyun yapılandırması ve yamalar |
| `ceviri/` | Türkçe çeviriler |
| `tests/` | Birim ve HTTP testleri |

---

## Veri ve gizlilik

- `saves/` altındaki oyun kayıtları **depoya dahil edilmez**.
- Sunucu yalnızca yerel makinede dinler (`127.0.0.1:5050`).
- Gizli anahtar `SE_SECRET_KEY` ortam değişkeniyle değiştirilebilir.

---

## Lisans

[GNU GPLv3](LICENSE).

```
Social Empires preservation project.
Copyright (C) 2022  The Social Emperors team
See the GNU General Public License <https://www.gnu.org/licenses/>.
```

### Teşekkürler

- [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors) —
  orijinal koruma projesi ve sunucu temeli.
- [Ruffle](https://ruffle.rs/) — Flash çalıştırma.
- [BlueMaxima's Flashpoint](https://bluemaxima.org/flashpoint/) ve
  [Internet Archive](https://archive.org/) — dijital koruma çalışmaları.
- Tüm katkıda bulunanlar.
