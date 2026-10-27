# Katkı Rehberi

## Gereksinimler

- Windows (desteklenen), Python 3.12+, Flask, jsonpatch
- Flash uyumlu tarayıcı veya Ruffle

## Kurulum

```bat
baslat.bat
```

Sunucu hazır olduğunda <http://127.0.0.1:5050/> açılır. Sağlık kontrolü:
<http://127.0.0.1:5050/saglik>

## Testler

```bat
python tests\test_komutlar.py
python tests\test_http.py
```

- `test_komutlar.py`: oyun komutları, kayıt, PvP, ekonomi, turnuva, ada.
- `test_http.py`: Flask uçtan uca uçlar (canlı kayıtları yazmaz).

## Değişiklik gönderme

1. `master` üzerinden yeni bir dal açın.
2. Değişikliği küçük ve odaklı tutun.
3. Testleri çalıştırın; kırılan test varsa PR açmayın.
4. Açıklamada neyin değiştiğini ve nasıl doğrulandığını yazın.
5. Kullanıcıya ait `saves/` dosyalarını, logları veya tokenları commit etmeyin.

## Kod stili

- Python 3.12, 4 boşluk, UTF-8.
- Kullanıcıya görünen metinler Türkçe; oyun içi metinler `ceviri/` üzerinden.
- Yeni oyun içeriği `config/patch/` altında RFC 6902 JSON yaması olarak eklenir.

## Güvenlik

Açıkları herkese açık issue olarak açmayın; [SECURITY.md](SECURITY.md) izleyin.
