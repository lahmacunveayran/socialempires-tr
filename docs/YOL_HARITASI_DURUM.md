# Yol haritası: durum

"Social Empires TR Yol Haritası" (30 Ekim 2026) belgesindeki beş fazın bu
daldaki durumu. Her fazın sonunda ölçülebilir bir kabul kapısı var; aşağıda
her kapının nasıl sınandığı ve sonucu yazılı.

| Faz | Durum | Kabul kapısı | Sonuç |
| --- | --- | --- | --- |
| 0. Temel ve ölçüm | Bitti | Harita tıklaması belgelendi, internetsiz açılış, testler, 304 | Geçti ([ayrıntı](FAZ0_OLCUMLER.md)) |
| 1. Açılış sahnesi | Bitti | 3 ekranda görüntü, oran 1,2667 ± 0,002, üç gökyüzü | Geçti (Lighthouse ölçülmedi) |
| 2. Canlı dünya | Bitti | Λ 1,2 ile 2 arası, şerit durdurulabilir, kürsü < 50 ms | Geçti |
| 3. Oyun içeriği | Büyük kısmı | 10 bayram tarihi, hafta sonu ödülü yalnız ilk 10'a, yedek bayt bayt | Geçti (testlerle) |
| 4. Dağıtım | Kısmen | Temiz Windows 11'de 60 sn'de açılış, telefon ve iPad | Sınanamadı (Windows ve telefon yok) |

## Faz 1: Açılış sahnesi

- Yeni oyun sayfası `/play.html` (eski Flash eklentili sayfa `/flash.html`).
- Gökyüzü Güneş yüksekliğine göre boyanır (`templates/js/gokyuzu.js`, NOAA
  denklemleri). İstanbul denetimi: 21 Haziran 2026 doğuş 05.33, batış
  20.40; 21 Aralık doğuş 08.26, batış 17.39 (belgedeki değerlerle en fazla
  1 dakika fark). SunCalc kitaplığı yerine aynı denklemler sayfaya gömüldü:
  dışarıdan dosya gerekmesin.
- Ölçüm (`node araclar/sayfa_goruntuleri.js <USERID> klasor --oyna`):

| Ekran | Oyun çerçevesi | Oran | Yatay kaydırma |
| --- | --- | --- | --- |
| 1920×1080 | 1112×878 | 1,2665 | yok |
| 1366×768 | 716×565 | 1,2673 | yok |
| 390×844 | 338×267 | 1,2659 | yok |

  Gökyüzü: 13.00 "gündüz", 20.45 "kızıllık", 23.30 "gece". "Krallığa Gir"e
  basınca oyun açıldı (Ruffle 0.7.1, yerel dosyadan).
- Dağ ve kale silueti şimdilik satır içi SVG; manzara görselinin kimden
  geleceği açık soru olarak duruyor.
- Ruffle'da ilk tıklama yalnızca odağı alıyordu; oyun açılınca odak sayfa
  tarafından verildiği için artık ilk tıklama da oyuna ulaşır.

## Faz 2: Canlı dünya

- `GET /dunya/olaylar?sonra=<id>` (15 sn yoklama), şeritte 5 sn'de en fazla bir
  satır, Durdur düğmesi (WCAG 2.2.2) ve `aria-live="polite"` özeti.
- Bot ekonomisinden turda bir haber eklendi. `python araclar/haber_olcumu.py 30`:
  30 dakikada 49 olay, **Λ = 1,63 olay/dk**, boş dakika olasılığı %20 (önce %68).
- `GET /dunya/kursu`: ilk 10 ve rütbe adları, 60 sn önbellek; yanıt 2-4 ms.
- "Nakit Al" Hazine sayfasına gider; "Ücretsiz Hediyeler" Faz 3'teki sandığı açar.

## Faz 3: Oyun içeriği

- Etkinlik takvimi (`oyun/takvim.py`, `config/takvim.json`): 2026-2030
  Diyanet bayram tablosu, sabit günler, Cadılar Bayramı 31 Ekim haftası.
  Tema setleri yalnızca etkinlikte mağazada (`"magaza_tema_setleri": "takvim"`).
- Haftalık turnuva (`oyun/elo.py`): Elo, K 32/16, bot maçları yarım K, haftada
  3 maç; hafta pazartesi 00.00 (TSİ) kapanır, ödül sonraki istekte yalnızca
  ilk 10'daki oyunculara (1. Yanardağ Ejderhası). Mevcut 4 kişilik odalar
  korunuyor; odalardaki maçlar haftalık tabloya ve reytinge işleniyor.
- Günlük hediye (`oyun/hediye.py`): 7 günlük sandık, kaçırılan gün bir adım geri.
  Hediyeler depoya yazılır; oyun açıksa bir sonraki açılışta görünür.
- Kayıt yedeği (`oyun/kayit_yedek.py`): indir/yükle, SHA-256, şema ve kimlik
  denetimi, `.bak`.

Yapılmayanlar: Arthur'un etkinliğe özel hedefleri; 2030 sonrası için
`hijridate` kurulu değilse ayarlardan elle tarih girilmeli.

## Faz 4: Dağıtım

- `python araclar/windows_paketi.py`: gömülü Python 3.12 + Windows
  tekerlekleri + oyun + Ruffle + `Social Empires.bat` → zip ve `.sha256`.
  Bu ortamda python.org'a erişim kapalı olduğu için yalnızca sahte bir
  gömülü Python zip'iyle (`--python-zip`) kurgu denendi; gerçek Windows'ta
  denenmedi.
- Ev ağı: `ayarlar.json` → `"ev_agi": true` ile sunucu ev ağına açılır ve
  telefon adresini yazar. Oyun adresleri isteğin geldiği adrese göre
  kurulduğu için telefon varlıkları da aynı sunucudan indirir. Hile paneli
  yine yalnızca bu bilgisayardan açılır.
- PWA: `/manifest.webmanifest`, 192 ve 512 px simgeler (bilgisayarda
  "uygulama olarak yükle").
- Dokunmatik: Faz 0 deneyinde Playwright dokunuşu Ruffle'da tıklama gibi işledi.

## Açık işler

- `fx/p.miniFireball2.swf` arşivde yok (404); karşılığı bulunup
  `oyun/varliklar.py` → `ESDEGERLER`'e eklenmeli.
- Yükleyicideki İspanyolca "Cargando" yazısı SELoader'da düz metin olarak
  geçmiyor (glif olarak çizilmiş olabilir). Sayfanın kendi yükleme ekranı bu
  aşamayı Türkçe nasihatlerle örtüyor.
- Lighthouse (LCP, CLS) ölçümü yapılmadı.
- Gerçek Windows 11 sanal makinesi, Android telefon ve iPad ile kabul sınaması.

## Görsel tasarım

Sayfadaki çizimler oyunun kendi görselleridir; oyun varlıklarıyla aynı yoldan
(`/default01.static.socialpointgames.com/...`) iner, depoya konmaz:
çam ağaçları ve giriş manzarası (`externalized/PopupLevelUp/`), iki nöbetçi,
kılıçlı arma ve bayraklar, parşömen ve başlık şeridi, günlük ödül
parşömeni, hazine sandığı, hediyeli köylü kız, Kral Arthur, haftalık turnuva
afişi ve hediye günlerindeki birim resimleri (`buildingthumbs/`). Yalnızca
gökyüzü (Güneş, Ay, bulutlar, yıldızlar) CSS ile çizilir, çünkü Güneş'in
gerçek konumuna göre değişir.

Yazı: başlıklar oyunun kendi başlıkları gibi beyaz dolgu, kalın kahverengi
dış çizgi ve koyu gölgeyle Baloo 2 (800); metin Nunito. İkisi de OFL ve
`templates/fonts/` altında. Seçim ölçülerek yapıldı: Lilita One, Fredoka,
Sniglet, Bowlby One, Changa One ve Bubblegum Sans'ta ğ, İ, ş harfleri yok;
Titan One'da İ yok. Baloo 2, Paytone One, Rubik ve Grandstander tam.

Etkileşimli bileşenler Magic UI, Eldora UI, Kokonut UI ve Animata'daki
React bileşenlerinin (AnimatedList, NumberTicker, MagicCard, ShineBorder,
SparklesText, SplitFlapText) kaynak kodu okunarak saf CSS ve küçük JS ile
yeniden yazıldı; React, Tailwind ya da Framer Motion gerekmez. Yay
hareketi CSS `linear()` eğrisiyle, dönen kenar ışığı `@property` ile.
