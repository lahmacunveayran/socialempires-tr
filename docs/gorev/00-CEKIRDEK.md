# SOCIAL EMPIRES TR GÖREV KİTABI: ÇEKİRDEK (her oturumda okunur)

Sürüm: 30 Ekim 2026 · Depo: `lahmacunveayran/socialempires-tr` · Okuyucu: bu depoda çalışan yapay zekâ oturumu

Kitap üç dosyadır; bölüm numaraları dosyalar boyunca süreklidir ve başvurular (§) dosya sınırını aşar. Yöntem
`lahmacunveayran/Lyraska` deposundaki görev kitabından alındı: amaç, her oturumun yaptığını sonradan **denetlenebilir**
kılmak.

| Dosya                       | İçerik                                                                              | Ne zaman okunur          |
| --------------------------- | ----------------------------------------------------------------------------------- | ------------------------ |
| `00-CEKIRDEK.md` (bu dosya) | §0 okuyucu, §1 proje gerçekleri, §2 çalışma sözleşmesi, §3 durum ve hafıza, §10 örnekler | her oturumda             |
| `10-BOLUM-I.md`             | §4 bulgu kaydının özeti, §5 yol haritası fazları (Faz 0–4) ve tasarım işleri        | geçmiş işi denetlerken   |
| `20-BOLUM-II.md`            | §6 açık işler, §7 sahibinin elle yapacağı testler                                   | yeni işe başlarken       |
| `BULGULAR.json`             | Her maddenin durumu, kanıtı, testi, PR'ı, onayı (makinece okunur)                   | her oturumda             |
| `KAPILAR.md`                | Kalite kapıları: komutlar, nerede çalıştıkları, son sonuçları                       | push'tan önce            |
| `SORUN_COZUM.md`            | Ortam, araç ve çalışma biçimi sorunları ile çözümleri (S-01 …)                      | her oturumda; sorun çıkınca |
| `../YOL_HARITASI_1407.md`   | 1.4.07'ye tam geçişin aşamaları, kabul kapıları ve tahminleri (KAR-08)              | yeni aşamaya başlarken   |

**Kanıt işaretleri** (kitaptaki ve `BULGULAR.json`'daki iddialar için):

- ✔ Çalıştırıldı ya da ölçüldü; nasıl ölçüldüğü yanında yazılı.
- ◐ Kod okumasına ya da dolaylı kanıta dayanıyor; çalıştırılıp gözle doğrulanmadı.
- ? Doğrulanmadı. Doğrulayamazsan "doğrulanamadı" yaz, tahminle ilerleme.

<okuyucu>

## 0. Okuyucu için

Depoyu ilk kez gören ama çok yetenekli bir mühendis olarak düşün. Sahibi yazılımcı değil: kodu sen yazarsın, sahibi
oynar, dener ve karar verir. Onunla her zaman **Türkçe**, sade ve adım adım konuşulur.

| Terim              | Anlamı                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| istemci            | Oyunun Flash dosyası `SocialEmpires0926bsec.swf`. Oyun mantığı onda çalışır; sunucu yalnızca kaydeder.       |
| komut              | İstemcinin `command.php` ile bildirdiği değişiklik (`oyun/komutlar.py`). Sunucu taklit eder, kural koymaz.   |
| kayıt              | `saves/<kimlik>.save.json`. Atomik yazılır, `.bak` ve günlük yedek alınır.                                   |
| varlık             | Oyunun SWF, resim ve müzik dosyaları (~1,3 GB). Depoda yok; ilk açılışta `download_assets/` altına iner.      |
| oyun görseli       | Oyun varlıklarındaki ya da `templates/img/` altındaki resim. Sayfada **yalnızca** bunlar kullanılır (§2.1).  |
| SWF yaması         | `oyun/swf_yama.py` (yazılar, yazı tipleri) ve `oyun/fx_yama.py` (eksik efekt): istemciyi sunarken düzeltir.  |
| Ruffle             | Flash öykünücüsü. Sürüm 0.7.1'e sabit, `/ruffle/0.7.1/` altından sunulur (`oyun/ruffle.py`).                 |
| bot                | 50 bilgisayar köyü (`playerInfo.bot`). Dünya simülasyonu onları oynatır.                                     |
| dünya turu         | `oyun/dunya.py` `tek_tick`: dakikada bir bot ekonomisi, akınlar, dünya olayları, haber şeridi.               |
| oyun sayfası       | `/play.html` (`templates/oyun.html`): gökyüzü, çerçeve, Diyar Haberleri, Şeref Kürsüsü, haftalık turnuva.     |
| kapılar            | Push'tan önce ve CI'da çalışan denetimlerin tamamı (`KAPILAR.md`).                                           |

</okuyucu>

<gercekler>

## 1. Proje gerçekleri

Hepsi ✔ (bu depodan okundu ya da çalıştırıldı, 30 Ekim 2026, `master` @ `cd80a86`), aksi belirtilmedikçe.

- Python 3.12 (CI) / Flask + Waitress (8 iş parçacığı); ayrıntı `oyun/sunucu.py` `calistir`. Bu ortamda Python 3.13.
- Testler: `python -m unittest discover -s tests` → 262 test (✔ çalıştırıldı, 31 Ekim 2026, sahibinin Windows'unda, GEC-03 birlik paketleri);
  `node --test tests/js/*.test.js` → 3 test (✔ 30 Ekim 2026, bulut oturumu). Yeni konteynerde önce bağımlılıklar
  kurulur (`SORUN_COZUM.md` S-01, Windows'ta S-27).
- Proje sahibinin bilgisayarında `D:\socialempires-tr` (S-25). Orada Python 3.12, Node yok (S-28), konsol cp1254 (S-26).
- CI (`.github/workflows/`): `tests` (Python + JS testleri), CodeQL (Python, JavaScript), `windows` (paket üretir,
  temiz Windows'ta 60 sn kapısıyla sınar, `v*` etiketinde sürüm yayınlar).
- Oyun sayfası Lighthouse (masaüstü): skor 100, LCP 0,7 sn, CLS 0 (✔ `lighthouse@12`, ayrıntı `docs/YOL_HARITASI_DURUM.md`).
- Windows paketi temiz Windows'ta 1,1 sn'de hazır (✔ CI `windows / sinama`, PR #10).
- Ortam sınırları (bu bulut oturumu): python.org'a erişim yok (Windows paketi yalnızca CI'da tam üretilir);
  GitHub REST API kimliksiz istekte sınırlı; `animata.design` gibi sitelere ağ izni yok, kaynak koda GitHub'dan bakılır.

</gercekler>

<sozlesme>

## 2. Çalışma sözleşmesi

### 2.1 Görseller (sahibinin kesin kuralı, `CLAUDE.md`)

Kendi ürettiğin hiçbir görsel girmez: çizim, SVG illüstrasyon, yapay zekâ resmi, emoji, CSS ile çizilmiş figür.
Yalnızca oyunun kendi görselleri, olduğu gibi. Işık huzmesi, gölge, kenar ışığı gibi **efektler** figür sayılmaz.
Bir şeyin figür mü efekt mi olduğundan emin değilsen sahibine sor.

### 2.2 Kararlar (sahibi, 30 Ekim 2026)

İngilizce yazılı oyun görselleri yeniden çizilmez; sunucu tek kişilik ve çevrimdışıdır; günlük ödül yalnızca oyunun
kendi ödülüdür. Ayrıntı ve kanıt: `BULGULAR.json` `KAR-*` maddeleri.

### 2.3 Akış ve kapılar

- Oturuma atanan dalda çalış. `master`'a doğrudan push yok; PR açılır. Birleştirmeyi sahibi yapar.
- Push'tan önce `KAPILAR.md`'deki yerel kapılar temiz olur. CI yeşil olmadan iş bitmiş sayılmaz.
- Testler atlanmaz, devre dışı bırakılmaz, gevşetilmez. Kırmızı CI'nın nedeni bulunur, "geçici" denmez.
- Geçmişi yeniden yazan işlem yok (force push, rebase). Birleşmiş dal yeniden kullanılacaksa güncel `master`'dan açılır.
- Dışa dönük ve geri alınamaz işler (sürüm etiketi göndermek, depo ayarı, silme) yalnızca sahibinin açık isteğiyle.

### 2.4 Kanıt disiplini

Her iddiaya ✔/◐/? işareti koy. "Çalışıyor" demeden önce çalıştır: birim testi, Playwright + Ruffle denemesi
(`araclar/harita_deneyi.js`, `araclar/sayfa_goruntuleri.js`), ölçüm (`araclar/haber_olcumu.py`, Lighthouse).
Ölçemediğini açıkça "ölçülmedi" diye yaz. Bulduğun ama düzeltmediğin hatayı `BULGULAR.json`'a `acik` olarak ekle.

### 2.5 Sahiple konuşma

Kısa ve Türkçe. Ne yaptığını, nasıl doğruladığını ve ondan ne beklediğini (karar, test) açıkça ayır. Teknik işi
ona bırakma; yapabileceği tek şey senin yapamayacağın şeyse (gerçek telefon, Windows bilgisayar) adım adım yaz.

</sozlesme>

<hafiza>

## 3. Durum, hafıza ve oturum düzeni

Durum sohbette değil dosyada tutulur; yeni bir oturum dosyalardan ve git geçmişinden devam eder.

| Dosya                           | İçerik                                                  | Biçim          |
| ------------------------------- | ------------------------------------------------------- | -------------- |
| `docs/gorev/BULGULAR.json`      | Maddelerin durumu, kanıtı, testi, PR'ı, onayı           | yapısal (JSON) |
| `docs/gorev/KAPILAR.md`         | Kapı komutları, nerede çalıştıkları, son sonuçları      | serbest metin  |
| `docs/gorev/SORUN_COZUM.md`     | Karşılaşılan sorunlar ve çözümleri                      | tablo          |
| `docs/devlog/YYYY-AA-GG.md`     | Devir notu (§10 şablonu; aynı gün ikinci oturumsa `-2`) | serbest metin  |
| `docs/YOL_HARITASI_DURUM.md`    | Yol haritası fazlarının kabul kapıları ve ölçümleri     | mevcut biçim   |

`BULGULAR.json` alanları korunur, **maddeler asla silinmez**; durumları güncellenir. `tests/test_gorev.py` şemayı
denetler (CI'da çalışır). Durum değerleri:

| Durum           | Anlamı                                                              |
| --------------- | ------------------------------------------------------------------- |
| `acik`          | Bulundu, henüz ele alınmadı                                         |
| `dogrulandi`    | Varlığı doğrulandı, düzeltilmedi                                    |
| `curutuldu`     | İddia yanlış ya da artık geçerli değil (kanıtıyla)                  |
| `ci_bekliyor`   | Düzeltme yazıldı, PR'ı açık; CI ve birleştirme bekleniyor           |
| `duzeltildi`    | Düzeltme `master`'da                                                |
| `onay_bekliyor` | Sahibinin kararı ya da testi gerekiyor                              |
| `karar_verildi` | Sahibi karar verdi; `onay` alanında cevabı ve tarihi                |
| `engelli`       | Bu ortamdan ya da bu istemciyle yapılamıyor (nedeni `notlar`'da)    |
| `ertelendi`     | Bilerek sonraya bırakıldı                                           |

**Oturum açılışı:** `git status` ve `git log --oneline -15`; son devir notunu, `BULGULAR.json`'daki
`devam_noktasi`'ni, `KAPILAR.md`'yi ve `SORUN_COZUM.md`'yi oku; hızlı kapıları çalıştır; sonra işe başla. Bir sorunu
çözünce ya da yeni bir sorunla karşılaşınca `SORUN_COZUM.md`'ye satır ekle.

**Her PR'da:** ilgili maddelerin `durum`/`pr`/`test` alanlarını güncelle; o günün devir notundaki "Durum" ve
"Sıradaki adım" bölümlerini güncelle.

**Oturum kapanışı:** `devam_noktasi`'ni güncelle, devir notunu yaz, commit + push.

</hafiza>

<ornekler>

## 10. Biçim örnekleri

<example>
`BULGULAR.json` maddesi:

```json
{
  "id": "VAR-01",
  "baslik": "fx/p.miniFireball2.swf arşivde yok (404)",
  "sinif": "hata",
  "onem": "Orta",
  "durum": "duzeltildi",
  "isaret": "✔",
  "kanit": "Ruffle konsolunda 4× 'HttpNotOk 404'; düzeltmeden sonra 0 (araclar/harita_deneyi.js)",
  "test": "tests/test_fx_yama.py",
  "pr": "#9",
  "onay": null,
  "notlar": "Efektin ekrandaki görünüşü gözle denetlenmedi."
}
```
</example>

<example>
Devir notu (`docs/devlog/YYYY-AA-GG.md`):

```markdown
# Devir notu — GG Ay YYYY

## Bu oturumda yapılanlar

- ...

## Durum

- CI: yeşil / kırmızı (neden)
- Açık PR'lar: ...

## Sıradaki adım

- ...

## Notlar / açık sorular

- ...
```
</example>

</ornekler>
