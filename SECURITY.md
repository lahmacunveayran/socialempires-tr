# Güvenlik Politikası

## Desteklenen sürüm

Yalnızca `master` dalındaki en güncel sürüm desteklenir.

## Güvenlik açığı bildirimi

Lütfen güvenlik açıklarını **herkese açık issue olarak açmayın**.

- GitHub üzerinden **Private vulnerability reporting** kullanın:
  <https://github.com/lahmacunveayran/socialempires-tr/security/advisories/new>
- Mümkünse etki, yeniden üretim adımları ve önerilen düzeltmeyi ekleyin.

## Kapsam

Bu proje, Social Empires oyununu yerel olarak çalıştıran bir topluluk
sunucusudur. Social Point ile bağlantılı değildir. Bildirimlerde özellikle
şunlar incelenir:

- Kayıt dosyası yolu kaçışı / yetkisiz dosya erişimi
- Kimlik doğrulama ve oturum sorunları
- Uzaktan kod çalıştırma veya komut enjeksiyonu
- Yerel ağa açıkken veri sızıntısı

## Uygulanan önlemler

- `USERID` için katı karakter/uzunluk doğrulaması ve Windows aygıt adı engeli
- Atomik kayıt yazımı (`.tmp` + `os.replace`) ve `.bak` yedeği
- Gizli anahtarın ortam değişkeninden okunması (`SE_SECRET_KEY`)
- GitHub secret scanning, push protection, Dependabot ve CodeQL
- Korumalı `master` dalı; zorla push ve dal silme kapalı
