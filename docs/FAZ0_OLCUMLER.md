# Faz 0: Temel ve ölçüm sonuçları

Yol haritasının Faz 0'ı. Ölçümler 30 Ekim 2026'da bu dalda, Chromium
(Playwright, başsız) ve Ruffle 0.7.1 ile yapıldı.

## 1. Harita tıklaması deneyi

**Sonuç: Ruffle'da haritaya tıklama ve sürükleme çalışıyor.** Önceki
"Ruffle'da yere tıklanmıyor" yargısı eğitimdeki imparatorluklarla yapılan
denemelerden geliyordu. Eğitim zorunlu; eğitim sürerken
`Base.startMapDrag`, `tutorialMode` açıkken hiçbir şey yapmadan döner. Yani
oyun o sırada haritayı bilerek kilitler, bu Ruffle'ın bir eksiği değil.

Eğitimi bitmiş (`completed_tutorial = 1`, seviye 16) bir kayıtla:

| Adım | Sonuç |
| --- | --- |
| Ruffle'a ilk tıklama | Yalnızca odağı alır, oyuna ulaşmaz |
| Günlük ödül "Ödülü al", pencere kapatma (X) | Çalışıyor |
| Haritayı sürükleme: fare (−160, −100) px | Harita (−156, −100) px kaydı (`araclar/goruntu_farki.py`) |
| Haritadaki binaya tıklama | Bina seçildi, alt panelde bilgisi açıldı (Kule II) |
| Dokunmatik tek dokunuş (`touchscreen.tap`) | Tıklama gibi işledi |

Bu yüzden Faz 4'ün telefon kısmının yeniden planlanmasına gerek yok.
Köylü yürütme ve mağazadan alınan evi yere bırakma bu turda ayrı ayrı
sınanmadı; ikisi de aynı harita tıklaması yolundan geçiyor.

Ruffle konsolunda (`logLevel: "warn"`) oyunu durduran bir eksik işlev uyarısı
yok. Görülen uyarılar: `Security.allowDomain`, zayıf anahtarlı `Dictionary`,
`describeTypeJSON`, `System.totalMemoryNumber` taslakları ve bilinmeyen cihaz
yazı tipleri (Times New Roman, Calibri, Noto Sans). Tek eksik dosya:
`fx/p.miniFireball2.swf` (404; arşivde karşılığı aranacak).

Deneyi yeniden çalıştırmak için (sunucu açıkken):

```bash
node araclar/harita_deneyi.js <USERID> harita_deneyi
python araclar/goruntu_farki.py harita_deneyi/1_acilis.png harita_deneyi/2_surukleme.png
```

## 2. Ruffle sabitlendi

- Sürüm 0.7.1, npm paketinin SHA-512 özeti doğrulanarak bir kez indirilir
  (`oyun/ruffle.py`) ve `/ruffle/0.7.1/` altından sunucudan verilir.
- Paket 28,5 MB WASM içerdiği için depoya konmadı; oyun varlıkları gibi ilk
  açılışta `download_assets/ruffle/` altına iner. `python varliklari_indir.py`
  hepsini önceden indirir.
- Gece sürümleri yalnızca `/ruffle-deneme.html` sayfasında denenir.
- Sayfa dışarıya hiç istek atmıyor: deneyde sunucu dışındaki tüm istekler
  engellendi, dış istek sayısı 0, oyun açıldı.

## 3. Sunucu

Flask geliştirme sunucusu yerine Waitress (8 iş parçacığı). Waitress kurulu
değilse eski sunucuya düşülür.

## 4. Sıkıştırma ve 5. önbellek başlıkları

| Dosya | Önce | Şimdi |
| --- | --- | --- |
| Oyun yapılandırması | 1.962.070 bayt | gzip 151.075 bayt (13 kat küçük) |
| Ruffle WASM | 14.302.754 bayt | gzip 4.994.112, brotli 3.441.981 bayt |
| İkinci açılışta yapılandırma | yeniden iner | 304 (ETag) |
| İkinci açılışta Ruffle ve varlıklar | yeniden sorulur | hiç istenmez (`immutable`) |

- Değişmeyen varlıklar ve sürümlü Ruffle dosyaları:
  `Cache-Control: public, max-age=31536000, immutable`.
- Sayfalar, yapılandırma, kayıt yanıtları ve Türkçeleştirilmiş oyun SWF'si:
  `no-cache` ve ETag ile 304.
- 404 dönen bir varlık kalıcı önbelleğe girmez.
- Yalnızca JSON, JS, WASM, HTML sıkıştırılır. WASM için brotli (11. düzey)
  önceden, arka planda üretilir; istek sırasında sıkıştırılmaz.
