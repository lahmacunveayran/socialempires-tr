# Social Empires Türkçe: çalışma kuralları

## Görseller: yalnızca oyunun kendi resimleri

Sayfaya ya da oyuna **kendi ürettiğin hiçbir görsel girmez**: çizim, SVG
illüstrasyon, yapay zekâyla üretilmiş resim, emoji ya da CSS ile çizilmiş
figür (güneş, bulut, karakter, simge...) yok. Oyunun ruhunu bozar.
Gerekirse en fazla **oyunun kendi görselleri** kullanılır: oyun varlıkları
(`/default01.static.socialpointgames.com/static/socialempires/...`, ör.
`images_new/`, `externalized/`, `buildingthumbs/`) ve depodaki
`templates/img/` resimleri. Bunlar da yeniden çizilmez, olduğu gibi kullanılır.

## Kararlar

- Oyun görsellerindeki İngilizce yazılar (BUILD, TRAIN, ADD ALLY, haber
  afişleri) yeniden çizilmez.
- Sunucu tek kişilik ve çevrimdışı. Çok oyunculu özellik eklenmez.
- Günlük ödül yalnızca oyunun kendi günlük ödülüdür; sayfada ayrı bir
  hediye sistemi yoktur.

## Commit ve PR metinleri

- Commit mesajlarına, PR açıklamalarına ve depo dosyalarına model adı ya da etiketi (ör. "Claude Opus",
  `Co-Authored-By: Claude ...`) **yazılmaz**. Sahibi istemedi (30 Ekim 2026).

## Geliştirme

- Testler: `python -m unittest discover -s tests`
- Tarayıcı JS testleri: `node --test tests/js/*.test.js`
- Ayrıntılar: `docs/GELISTIRME.md`, yol haritası durumu: `docs/YOL_HARITASI_DURUM.md`
- Yeni konteynerde testlerden önce: `pip install -q --ignore-installed blinker -r requirements.txt`

## Görev kitabı ve devir notu

İşler sonradan denetlenebilsin diye kitap gibi tutulur (`lahmacunveayran/Lyraska` ile aynı yöntem):

- Her oturumun başında `docs/gorev/00-CEKIRDEK.md`, `docs/gorev/BULGULAR.json` (`devam_noktasi`),
  `docs/gorev/SORUN_COZUM.md` ve son `docs/devlog/` notu okunur.
- Karşılaşılan ya da çözülen her ortam, araç ve çalışma sorunu `docs/gorev/SORUN_COZUM.md`'ye yazılır.
- 1.4.07'ye tam geçiş kararlaştırıldı (KAR-08); aşamalar ve kabul kapıları `docs/YOL_HARITASI_1407.md`.
- Bulunan, düzeltilen, çürütülen ya da karara bağlanan her şey `BULGULAR.json`'a kanıtı ve işaretiyle
  (✔ çalıştırıldı, ◐ dolaylı, ? doğrulanmadı) yazılır; maddeler silinmez. `tests/test_gorev.py` şemayı denetler.
- Her PR o günün devir notundaki "Durum" ve "Sıradaki adım"ı günceller; oturum sonunda
  `docs/devlog/YYYY-AA-GG.md` yazılır (aynı gün ikinci oturumsa `-2`).
