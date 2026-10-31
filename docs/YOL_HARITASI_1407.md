# Yol haritası: 1.4.07'ye tam geçiş

Tarih: 30 Ekim 2026. Görev kitabı: GEC-01 … GEC-09, OYN-11 … OYN-13, ONR-01 … ONR-04, KAR-08, KAR-09.

İşaretler: **✔** ölçüldü ya da okunarak doğrulandı, **◐** dolaylı kanıt, **?** tahmin ya da ölçülmedi.

## 0. Karar

Sahibinin 30 Ekim 2026 kararları:

- **Tam ve net geçiş.** "Tam ve net geçiş olacak. Hatasız, hesaplamalı, denklemli bir mühendislik çerçevesinde
  sağlam, kaliteli bir iş ortaya konacak."
  - Oyunun tek istemcisi `SocialEmpires1.4.07sec_fixed.swf` olur.
  - 0926 istemcisi ve ona özgü kod kaldırılır.
  - Çift istemcili plan (`docs/inceleme/2026-10-30-1407-gecis-plani.md` §4) bu kararla geçersizdir.
- **Tablet denemesi yeni sürümde.** Sahibi PR #18 APK'sını denemeyecek. Denemeyi geçiş bitince yeni sürümde yapacak.
- **Küçük işler** yol haritasına girer.
- **Önceki dört önerinin hepsi** yol haritasına girer.
- **Görsel kuralı, sahibinin sözleriyle:** "Kesinlikle kendin yapay zekâ üretimi yapmayacaksın. Yeni bir şey
  üretilecekse kesinlikle ve kesinlikle oyunun kendi görselleri, resimleri ve dosyaları kullanılacak."

## 1. Ölçülmüş başlangıç durumu

| Ölçüm | Değer | Kaynak |
|---|---|---|
| 1.4.07 bizim sunucuyla Ruffle 0.7.1'de açılıyor | ✔ yeni imparatorluk 8 sn, sv 59 kayıt 6 sn | KYN-05 |
| İstemcinin komut sayısı | ✔ 183 (0926: 154, +29 yeni) | KYN-05 |
| İstemcinin gerçekten gönderdiği komut (çağrı yerinden) | ✔ 158 (0926: 131); 183 = 158 + 25 hiç okunmayan sabit; yeni 28, kalkan 1 | KYN-06, `docs/inceleme/1407-komutlar.md` |
| Sunucunun işlediği (H), eksik (G ∖ H), imza uyumsuzluğu | ✔ 128, 31, 0 | GEC-01, `araclar/komut_imzalari.py` |
| Çeviri T: SWF metin alanı / sabit yazı / AS3 / config loc / hedef | ✔ 0,633 / 0,759 / 0 / 0,748 / 0 | GEC-01, `docs/inceleme/ceviri-kapsami.md` |
| Yamalarımız 1.4.07 config'inde: gider / kalır / çatışır | ✔ 1 / 1 / 11 | KNF-01, `docs/inceleme/1407-config-hatti.md` |
| GEC-02'den sonra config loc T | ✔ 1976 / 1976 = 1 (hedefler hâlâ 0 / 410) | CEV-02 |
| GEC-02'den sonra açılış | ✔ yeni imparatorluk ve 0.05a'dan göç eden 51 kayıt; konsol hatası 0; 54 kayıtta karşılıksız eşya 0 | GEC-02 |
| Eski görev numarası 1.4.07'de başka hedefe denk | ✔ SV59 deneme hesabında 228'den 86 | GOR-01 |
| Türkçe SWF yamasının 1.4.07'de eşlediği alan | ✔ 521 alan (sözlük anahtarlarının 404/455'i) | KYN-01 |
| Upstream varlık ağacı `54df29e` ile `f642e0b` | ✔ 4.825 / 4.479 dosya | bu oturum, `git ls-tree` |
| Ortak 4.478 dosyanın içerik farkı | ✔ **0** (git blob kimlikleri birebir aynı) | bu oturum |
| `54df29e`'de yeni dosyalar | ✔ 347 dosya: `img` 189, `images_new` 82, `externalized` 66, `swf` 5, `fx` 2, `buildingsprites` 2, `flash` 1 | bu oturum |
| `54df29e`'de silinen | ✔ 1 dosya: `externalized/DailyBonus/imgs/temp.png` | bu oturum |
| Bizim kodda 0926'ya bağlı nokta | ✔ 22 satır, 14 dosya (`grep 0926`; py, js, html, yml, kts, java, sh; belgeler hariç) | bu oturum |

Bu ölçümün sonucu şudur: `54df29e`'deki varlıklar, `f642e0b`'dekilerin içerik olarak birebir üst kümesidir; tek
fark silinen bir geçici resim. Bu yüzden geçişte iki ayrı kaynak gerekmez. Tek kaynak `54df29e`'ye sabitlenir, ilk
adımda yalnızca `oyun/kaynaklar.py`'deki commit değişir. Bu PR'da kaynak, değişebilir `main` dalından `f642e0b`'ye
sabitlendi (KYN-03).

## 2. Mühendislik çerçevesi

Her aşama bir PR'dır ve ölçülebilir bir **kabul kapısıyla** kapanır. Kapı geçmeden sonraki aşamaya geçilmez.

### 2.1 Kapılarda kullanılan ölçüler

- **Komut kapsaması.** G, istemcinin gönderebildiği komutların kümesidir (183 komut, istemcinin sabit havuzundan).
  H, sunucunun işlediği komutlardır. Belgeli bir nedenle bilerek boş bırakılanlar da H'ye sayılır.
  - Kapı: `|G ∖ H| = 0`.
  - Kapı: oynanış betiğinde "bilinmeyen komut" günlüğü 0.
- **Komut imzası.** Her komutun argüman sayısı ve sırası, 0926'dan değil, 1.4.07'nin `addCommand` çağrılarından
  çıkarılır.
  - Kapı: sunucu işleyicisiyle istemci çağrısı arasındaki uyumsuzluk sayısı 0.
- **Formül eşitliği.** Sunucunun hesapladığı her büyüklük (süre, bedel, ödül, kalkan, onur, çalınan kaynak) istemcinin
  bayt kodundan ya da config anahtarından çıkarılır. Her biri `docs/inceleme/1407-formuller.md`'ye denklemiyle ve
  kaynağıyla yazılır.
  - Tamsayı büyüklüklerde kapı: sınır değerlerini de içeren bir sınama ızgarasında `f_sunucu(x) = f_istemci(x)`.
    Sapma payı yoktur.
  - Örnek: hızlandırma bedeli, kuyruk bitiş zamanı `t_bitis = t_baslangic + egitim_suresi / zaman_olcegi`.
- **Kayıt göçü.** g, eski kaydı yeni biçime çeviren işlevdir. I(s), kaydın korunması gereken değerleridir: seviye, XP,
  altın, odun, yemek, taş, nakit, eşya çoklukümesi, birim sayıları, depo, mezarlık, harita sayısı.
  - Değişmezlik: her örnek kayıt s için `I(g(s)) = I(s)`.
  - Eşgüçlülük: `g(g(s)) = g(s)`.
  - Geri dönüş: göçten önce `.bak` ve günlük yedek alınır. Testte, yedekten açılan kaydın baytları eski kayıtla aynı
    çıkmalıdır.
- **Çeviri kapsaması.** T = çevrilen / çevrilmesi gereken. Bu oran SWF metin alanları, AS3 dizeleri, config `loc`
  adları ve 206 hedef için ayrı ayrı ölçülür.
  - Kapı: dördünde de T = 1.
  - Hariç tutulanlar: resimlerdeki yazılar (KAR-01) ve geliştirici dolgu metinleri ("asdfasdf", "Line1"). Bu ikisinin
    listesi belgelenir.
- **Ruffle konsolu.** Açılışta ve oynanış betiğinde hata 0, HTTP 404 0. Belgeli istisnalar ayrı listede tutulur.
- **Süre.** Masaüstünde açılış, yeni imparatorlukta ≤ 8 sn, eski kayıtta ≤ 6 sn olmalıdır. Bunlar KYN-05'te ölçülen
  değerlerdir; kötüleşme payı %20'dir.
  - Android CI emülatör sınaması yeşil olmalıdır.
- **Görsel kuralı.** `tests/js/gorsel_kurali.test.js` yeşil olmalıdır. Yeni bir arayüz parçasının kullandığı her
  resim, oyun dosyasının yoluyla PR açıklamasında listelenir. Çizim, SVG, emoji, CSS figürü ve yapay zekâ resmi
  kullanılmaz.

### 2.2 Doğrulama araçları (Aşama 0'da yazılır)

- **`araclar/abc_okur.py`:** AS3 bayt kodu okuyucusu. Yöntem gövdelerini ve işlem kodlarını çözer, gizlenmiş koddaki
  anlamsız komutları atlar. Bütün `addCommand` çağrılarını argümanlarıyla çıkarır, formül kaynaklarını bulur.
  - Kendi kodumuzdur. Dışarıdan indirilen araç (FFDec) çalıştırılmaz.
- **`araclar/komut_imzalari.py`:** G ve H kümelerini ve argüman uyumunu tablo olarak üretir:
  `docs/inceleme/1407-komutlar.md`.
- **`araclar/ceviri_kapsami.py`:** dört T oranını ve kalan İngilizce listesini üretir.
- **Oynanış betiği** (Playwright + Ruffle): her komut grubunu en az bir kez tetikler. Bunlar inşa, eğitim, kuyruk,
  hızlandırma, hedef, günlük ödül, PvP ve Soul Mixer'dır. Betik sunucu günlüğünü ve Ruffle konsolunu toplar.

### 2.3 Lisans ve kaynak

- Upstream'in (AcidCaos/socialemperors, GPLv3) kodu birebir kopyalanmaz. Davranışı okunur, kendi kodumuzla ve atıfla
  yazılır.
- README'ye GPLv3 5(a) notu eklenir: "0.04a `f642e0b` tabanından değiştirildi."
- Social Point'in SWF'leri GPL kapsamında değildir. Yamalı istemci `54df29e` commit'inden iner. İndirilen dosyanın
  SHA-256 özeti sunucuda denetlenir, özet uyuşmazsa sunulmaz. Yamaların listesi
  `docs/inceleme/2026-10-30-upstream-tarama2.md` §2.4'te.

## 3. Aşamalar

Emek tahmini üç noktalıdır (o: iyimser, m: olası, p: kötümser, iş günü). Beklenen değer `E = (o + 4m + p) / 6`, sapma
`σ = (p − o) / 6`. Tahminler **?**: yöntem nesneldir, girdiler tahmindir.

| Aşama | İş | Kabul kapısı | o / m / p | E |
|---|---|---|---|---|
| **GEC-01** Ölçüm altyapısı | `abc_okur`, `komut_imzalari`, `ceviri_kapsami`; 1.4.07 komut tablosu; config hattının ölçümü (hangi yama kalır, hangisi gider; 0926'nın okumadığı yamalar 1.4.07'de canlanır mı) | Komut tablosu G = 183 ile tutarlı; araçların birim testleri | 1 / 2 / 3 | 2,00 |
| **GEC-02** İstemcinin değişmesi | `OYUN_SWF` = 1.4.07; kaynak `54df29e` ve SHA-256 denetimi; config hattı (upstream veri yamalarının davranışı kendi yamamızla, `goals`); `reward_mission` `goals`'tan; Türkçe SWF yaması ve `fx_yama` 1.4.07'de; kayıt sürüm alanı ve göç öncesi yedek; 0926 kodunun ve testlerinin kaldırılması | Yeni imparatorluk ve 51 örnek kayıt açılır; konsol hata 0; bütün testler yeşil | 1 / 2 / 3 | 2,00 |
| **GEC-03** Yeni komutlar | Kuyruk (4), teklif ve satın alma (8), `collect_game` (5), diğer (5); imza farklarının giderilmesi; her hesap formül defterine | `|G ∖ H| = 0` (PvP hariç); imza uyumsuzluğu 0; formül eşitliği | 3 / 4 / 6 | 4,17 |
| **GEC-04** Kayıt | ~30 yeni `privateState` alanı; şema; göç g; `kaydi_dogrula` uyarlaması | `I(g(s)) = I(s)`, `g(g(s)) = g(s)`; geri dönüş testi | 2 / 3 / 4 | 3,00 |
| **GEC-05** Yeni PvP, botlar, turnuva | 7 PvP komutu ve `/pvp/*` uçları (yalnızca botlara karşı, KAR-02); kalkan, onur, saldırı günlüğü; bot dünyası ve Diyar Haberleri'nin yeni PvP'ye bağlanması; turnuva | PvP dahil `|G ∖ H| = 0`; 404 yok; bot dünya turu süresi ≤ önceki | 2 / 3 / 5 | 3,17 |
| **GEC-06** Türkçe | ~130 yeni SWF metni, 51 kaybolan anahtarın karşılığı, 428 `loc` adı, 206 hedef (23.530 karakter); yazı tiplerinde Türkçe harfler; yeni pencerelerin yazıları | Dört T = 1; ekran görüntüleriyle denetim | 2 / 3 / 5 | 3,17 |
| **GEC-07** Bayram hedefleri | Sunucu, `goals` listesine bayram tarihlerinde hedef ekler; istemci tarih bilmez. Resimler oyunun hedef resimlerinden seçilir (ICR-01) | Takvim testleri: bayram günü hedef var, ertesi gün yok; ödül bir kez | 1 / 1,5 / 2 | 1,50 |
| **GEC-08** Android, çevrimdışı paket, hız | `config/onindirme.tsv`'nin yenilenmesi (+347 dosya); APK; emülatör sınaması; açılış süresi | CI yeşil; süre kapısı; paket listesi eksiksiz | 1 / 2 / 3 | 2,00 |
| **GEC-09** Kabul ve sürüm | Uçtan uca oynanış betiği; sahibinin tablet denemesi; v0.1.0 (sahibinin onayıyla) | Bütün kapılar; sahibinin "tamam"ı | 1 / 1,5 / 3 | 1,67 |
| **Son iş** İmza anahtarı (KAR-09) | Sahibi, bütün işler bittikten sonra Android imza anahtarını üretip GitHub sırrına ekler (`ANDROID.md` "İmza anahtarı") | CI'da "Sahibin anahtarıyla imzalanacak" | — | — |
| **Küçük işler** OYN-11 … OYN-13 | Aşağıda §4 | Her biri kendi testiyle | 1 / 1,5 / 3 | 1,67 |
| **Öneriler** ONR-01 … ONR-04 | Aşağıda §5 | Her biri kendi testiyle | 4 / 7 / 12 (dördünün toplamı) | 7,33 |

Toplamın hesabı:

- Beklenen değer: `ΣE = 136/6 + 10/6 + 44/6 = 190/6 ≈ 31,7` iş günü.
  - Geçişin kendisi (GEC-01 … GEC-09): `136/6 ≈ 22,7` iş günü.
- Sapma (aşamalar bağımsız varsayılarak): `σ = √Σσ² = √1,93 ≈ 1,39`.
  - %90 üst sınır: `ΣE + 1,28σ ≈ 33,4` iş günü.
- Bağımsızlık varsayımı sapmayı küçük gösterir. Bilinmeyen bir Ruffle hatası çıkarsa tahmin yeniden yapılır.

Sıra ve bağımlılıklar:

- GEC-01 → GEC-02 → (GEC-03 ∥ GEC-04) → GEC-05 → GEC-06 → GEC-07 → GEC-08 → GEC-09 → imza anahtarı.
- İmza anahtarı en son iştir (sahibinin kararı, KAR-09). Ondan önceki APK'lar geçici anahtarla imzalanır.
- Küçük işler GEC-02'den sonra herhangi bir arada yapılır.
- Öneriler GEC-05'ten sonra gelir; GEC-09 kabul denemesi hepsini birlikte kapsar.

Her aşamada master oynanabilir kalır. Bir aşamada eksik kalan komut, hata vermeden boş yanıt döner ve listede
"eksik" diye görünür.

## 4. Küçük işler

| Madde | İş | Not |
|---|---|---|
| OYN-11 | Günlük ödül penceresinin boş başlığı, sığmayan "250 altın" | 1.4.07'nin 5 günlük yeni penceresi eskisinin yerini alıyor. GEC-02'den sonra yeniden ölçülür; sorun yeni pencerede de varsa düzeltilir |
| OYN-12 | Seviye atlayınca sayfanın üstündeki seviye/XP bilgisi yenilenmiyor | Sayfa bilgisi seviye atlama komutundan sonra güncellenmeli |
| OYN-13 | "Yedek yükle" düğmesine klavyeyle ulaşılamıyor | Klavye ve ekran okuyucu erişimi |

## 5. Öneriler (sahibi "hepsini istiyorum" dedi)

Bu dört öneri önceki bir oturumda sohbette yapıldı; metinleri depoya yazılmamıştı. Aşağıdaki tanımlar benim anladığım
kapsamdır. Sahibinin kuralı "Onayladığım öneriyi harfiyen uygula" olduğu için her biri işe başlamadan önce sahibine
tek cümleyle onaylatılır.

| Madde | Öneri | Taslak tanım (onay bekliyor) | o / m / p |
|---|---|---|---|
| ONR-01 | Hız seçici | Oyunun hızı (`ayarlar.json` `zaman_olcegi`, şu an elle) sayfadan seçilir. Düğmeler oyunun kendi düğme resimleridir. 1.4.07'nin yeni süreleri de (kuyruk, Soul Mixer) aynı ölçekle bölünür. | 0,5 / 1 / 2 |
| ONR-02 | "Sen yokken" özeti | Oyuncu döndüğünde, yokken olanların kısa listesi: botların akınları, kazanılan ve kaybedilen, biten inşaat ve eğitim, Diyar Haberleri. Veri imparatorluk günlüğünden ve haber şeridinden gelir, resimler oyunun kendi resimleridir. | 1 / 2 / 3 |
| ONR-03 | Bildirimler | Android'de uygulama kapalıyken yerel bildirim: inşaat, eğitim ya da kuyruk bitti, kalkan bitiyor, saldırıya uğradın. Zamanlar formül defterindeki sürelerden hesaplanır. Simge oyunun kendi simgesidir (`templates/img/simge-192.png`). Bildirim internetsiz çalışır. | 2 / 3 / 5 |
| ONR-04 | Oyunun Türk birimleri | Oyunun kendi "Turkish Swordsman/Axeman/Archer/Horseman" birimleri (öğe 880, 881, 882, 885; resimleri `880_tk_sword` …) oyunda kullanılabilir olur. Mağazada mı, bayramlarda mı, botlarda mı kullanılacağına sahibi karar verir. | 0,5 / 1 / 2 |

## 6. Riskler

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| Ruffle 0.7.1'de, deneyde görülmeyen bir 1.4.07 hatası | Orta ? | Yüksek | Oynanış betiği her komut grubunu Ruffle'da çalıştırır; hata çıkarsa önce istemci tarafında yama, sonra tahmin yenilenir |
| 1.4.07'de komut argümanlarının 0926'dan farklı olması | Orta ◐ | Yüksek | GEC-01'deki imza tablosu; her işleyici bu tabloya karşı test edilir |
| Göçte oyuncunun kaydının bozulması | Düşük | Çok yüksek | Göç öncesi `.bak` ve günlük yedek; değişmezlik testleri; 51 gerçek biçimli kayıtla deneme |
| Upstream yamalı SWF'yi değiştirir | Düşük | Orta | Commit ve SHA-256 sabit; değişiklik bize kendiliğinden gelmez |
| Yeni pencerelerdeki İngilizce, resmin içinde | Yüksek ✔ | Düşük | KAR-01: resimdeki yazı yeniden çizilmez; metin alanındaysa çevrilir |
| Android imza anahtarı olmadan güncelleme kayıtları korumaz | Kesin ✔ | Yüksek | Anahtar en son eklenir (KAR-09). O zamana kadar her yeni APK'da: yedek indir → kaldır → kur → Yedekten Yükle. Anahtar eklendikten sonraki ilk APK'da bir kez daha aynısı |
