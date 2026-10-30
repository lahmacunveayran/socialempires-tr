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

## Geliştirme

- Testler: `python -m unittest discover -s tests`
- Ayrıntılar: `docs/GELISTIRME.md`, yol haritası durumu: `docs/YOL_HARITASI_DURUM.md`
