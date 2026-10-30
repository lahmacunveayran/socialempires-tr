# Sorun ve çözüm kaydı

Bu depoda çalışırken karşılaşılan sorunlar ve çözümleri burada tutulur, böylece aynı sorun ikinci kez zaman yemez.
Oturum başında göz gezdirilir. Yeni bir sorunla karşılaşınca ya da bir sorunu çözünce buraya bir satır eklenir.

- Maddeler silinmez. Çözüm değişirse eski satırın altına yenisi yazılır.
- Oyunun hata ve özellikleri `BULGULAR.json`'a yazılır; burası ortam, araç ve çalışma biçimi sorunları içindir.
- İşaretler: ✔ yaşandı ve çözümü denendi, ◐ başka oturumun notundan, ? çözümü doğrulanmadı.

## Ortam ve kurulum

| # | Sorun (belirti) | Neden | Çözüm | İşaret, tarih |
|---|---|---|---|---|
| S-01 | Yeni konteynerde `python -m unittest discover -s tests` 117 test bulur, 89'u `ModuleNotFoundError: werkzeug / jsonpatch / flask` verir | Bağımlılıklar yeni konteynerde kurulu değil | `pip install -q --ignore-installed blinker -r requirements.txt`; sonra 197 test geçer | ✔ 30.10.2026 |
| S-02 | `pip install -r requirements.txt` "Cannot uninstall blinker 1.7.0, RECORD file not found" ile durur | Debian'ın kurduğu blinker pip'le kaldırılamıyor | `--ignore-installed blinker` | ✔ 30.10.2026 |
| S-03 | Kökten `python -m unittest tests.test_x` "import ortak" hatası verir | Testler `tests/` klasörünü yol sanıyor | Tek dosyayı `tests/` içinden çalıştır: `cd tests && python -m unittest test_x` | ◐ |
| S-04 | `pkill -f "python3 server.py"` kendi kabuğunu da öldürür | Kabuğun komut satırında da aynı metin var | `P=$(pgrep -f "^python3 server.py$"); [ -n "$P" ] && kill $P` | ◐ |
| S-05 | Değişkenli `rm -rf $S` boş değişkenle tehlikeli | Değişken boşsa kök silinir | Her zaman `rm -rf "${S:?}"` | ◐ |
| S-06 | Playwright ya da Chromium "yeniden kurulsun mu" | Ortamda hazır kurulu | Yeniden kurma; `require('playwright')` doğrudan çalışır | ◐ |

## Ağ, GitHub ve upstream

| # | Sorun (belirti) | Neden | Çözüm | İşaret, tarih |
|---|---|---|---|---|
| S-07 | GitHub REST API 403 | Kimliksiz istek sınırı / vekil | `git clone` ve `raw.githubusercontent.com` çalışır; GitHub işleri için MCP araçları | ◐ |
| S-08 | web.archive.org bağlanmadı | Ağ politikası (ayarlara eklendiği hâlde) | Yeni oturumda yeniden denenmeli; doğrulanmadı | ? |
| S-09 | `git clone -b <commit>` çalışmaz | `-b` yalnızca dal ya da etiket alır | `git init` + `git fetch --depth 1 --filter=blob:none origin <commit>` + `checkout FETCH_HEAD` (`varliklari_indir.py`) | ✔ 30.10.2026 |
| S-10 | `--filter=blob:none` klonda `git ls-tree -r -l` dakikalarca sürer, binlerce indirme yapar | `-l` (boyut) her dosyanın içeriğini tek tek indirtir | Boyut gerekmiyorsa `-l` kullanma; içerik karşılaştırması için blob kimlikleri yeter (`git ls-tree -r <commit>`) | ✔ 30.10.2026 |
| S-11 | İndirilen kodu (JPEXS FFDec, upstream sunucusu, onların betikleri) çalıştırmak izin sistemine takılır | Güvenlik kuralı | Yalnızca oku; kendi betiklerimizle çalış (`oyun/swf_yama.py`, `araclar/swf_resimleri.py`). SWF'yi Ruffle'da açmak sorun değil | ◐ |
| S-12 | Varlıklar upstream'in değişebilir `main` dalından iniyordu | Dal adı sabit değil | `oyun/kaynaklar.py`'de sabit commit (KYN-03) | ✔ 30.10.2026 |

## Android ve CI

| # | Sorun (belirti) | Neden | Çözüm | İşaret, tarih |
|---|---|---|---|---|
| S-13 | Emülatör bir kez grafik katmanı çöküşüyle düştü | CI emülatörünün yazılım GPU'su | Yeniden çalıştırınca geçti; tekrar ederse günlüğe bak | ◐ |
| S-14 | "Python 3.12 is not available for the ABI armeabi-v7a" | Chaquopy 3.12+ yalnızca 64 bit | Python 3.11 (DAG-05) | ◐ |
| S-15 | Android 15 emülatöründe oyun açılmaz: "Vertex shader active uniforms exceed ... (256)" | Ruffle'ın wgpu çizicisi 256 uniform sınırlı GPU'da | `oyun.js` GPU sınırını okur; ≤256 ise `preferredRenderer='webgl'` (DAG-07) | ◐ |
| S-16 | "A script in this movie has taken too long to execute" | ~5 MB config tek olayda işleniyor | Ruffle `maxExecutionDuration` 60 sn (DAG-08) | ◐ |
| S-17 | İmza anahtarını depoya koyan commit durduruldu | Otomatik güvenlik denetimi kimlik bilgisi sızıntısı saydı | Anahtar GitHub sırrında (`ANDROID_IMZA`), depoda asla (KAR-07) | ◐ |
| S-18 | CI çıktısı (APK) indirilemiyor | GitHub Actions artifact'leri giriş ister | Tablete link verirken GitHub girişini hatırlat; doğrudan indirme için sürüm (v*) | ◐ |
| S-24 | Sahibinin bilgisayarındaki proje yolu `C:\Users\Avukat Emre Aydoğdu\Desktop\socialempires-tr`: boşluk ve "ğ" içeriyor | Android derleme araçları (SDK, emülatör, Gradle) bu tür yollarda bazen hata verir (?, ölçülmedi); oyun sunucusu etkilenmez | Sahibinin kararı (30.10.2026): yol şimdilik değişmez, en sona bakılır. Gerekirse araçlar `C:\Android` gibi düz bir yola kurulur | ? 30.10.2026 |

## Çalışma biçimi dersleri

| # | Ders | Olay | İşaret, tarih |
|---|---|---|---|
| S-19 | Masaüstünde görülmeyen bir şeyi "çürütüldü" sayma | "Cargando" masaüstünde hızlı geçiyordu, tablette görünüyordu (VAR-02 → VAR-03) | ◐ |
| S-20 | Onaylanan öneri harfiyen uygulanır, ayrıntı uydurulmaz | "Birimin oyundaki adı" denmişti, ad uyduruldu (OYN-04) | ◐ |
| S-21 | Önce ölç, sonra karar ver | 1.4.07 "imkânsız" sanılıyordu, deneyde açıldı (KYN-05) | ◐ |
| S-22 | Bağımsız denetimde denetçiye kendi sonucunu verme; her bulguyu kendin yeniden üret | DNT-01 … DNT-04 | ◐ |
| S-23 | Görsel gerekiyorsa yalnızca oyunun kendi dosyası, olduğu gibi | Sahibi çerçevelerin elle yapıldığını fark etti (OYN-09); 30.10.2026'da kural yeniden ve kesin söylendi | ✔ 30.10.2026 |
