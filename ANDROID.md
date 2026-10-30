# Android uygulaması

Oyunun tamamı tek bir uygulamada: sunucu telefonun ya da tabletin içinde çalışır, bilgisayar gerekmez.
Oyun tam ekran açılır.

## Gerekenler

- Android 7.0 ya da üstü; 32 ve 64 bit cihazlar (eski Galaxy Tab A'lardan yeni Tab S'lere kadar).
- Yaklaşık 250 MB boş yer.
- **İlk açılışta internet.** Oyunun resimleri, sesleri ve haritaları (~60 MB) bir kez indirilir; sonra
  internet gerekmez.

## Kurulum

1. APK dosyasını tablete indirin:
   - Yayınlanmış sürüm: [Sürümler](https://github.com/lahmacunveayran/socialempires-tr/releases) sayfasındaki
     `SocialEmpiresTR-...-android.apk`.
   - Henüz yayınlanmamış bir deneme: GitHub'da ilgili PR'ın **Checks → android** sayfasındaki `android-apk`
     dosyası (GitHub hesabıyla iner, zip içindedir; Dosyalarım uygulamasıyla açın).
2. APK'ya dokunun. Android "bilinmeyen uygulama" izni isterse açın.
   Samsung'da: **Ayarlar → Uygulamalar → ⋮ → Özel erişim → Bilinmeyen uygulamaları yükle →** (Dosyalarım ya da
   Chrome) **→ İzin ver**.
   Samsung "Otomatik Engelleyici" (Auto Blocker) kurulumu engellerse: **Ayarlar → Güvenlik ve gizlilik →
   Otomatik Engelleyici → Kapat**; kurulumdan sonra yeniden açabilirsiniz.
3. Google Play Protect uyarı verirse **Yine de yükle**'ye basın. Uygulama Play Store'da değildir.
4. **Social Empires** simgesine dokunun. Birkaç saniye "Oyun sunucusu açılıyor…" yazar, sonra imparatorluk
   seçme ekranı gelir.

## İnternetsiz oynamak: çevrimdışı paket

Oyun sayfasının üstündeki **çevrimdışı paket** bağlantısı:

- **Temel paket (~175 MB):** oyun, arayüz, efektler, müzik, mağazadaki bütün bina ve birimler. İnternetsiz
  oynamaya yeter.
- **Tam paket (~1,1 GB):** üstüne mağazada olmayan ödül, boss ve bot binalarının çizimleri.

İndirme sürerken oynayabilirsiniz; yarıda kalırsa yeniden basınca kaldığı yerden sürer. Wi-Fi'da indirin.

## Kayıtlar

- Kayıtlar uygulamanın içindedir. **Uygulamayı kaldırmak kayıtları siler.** Kaldırmadan önce oyun sayfasındaki
  **yedek indir** ile yedek alın.
- Yeni sürüm, depo sahibinin imza anahtarı GitHub'a eklendiyse (aşağıda "İmza anahtarı") eskisinin üstüne kurulur
  ve kayıtlar korunur. Eklenmediyse her APK geçici bir anahtarla imzalanır; Android "uygulama yüklenmedi" der.
  O durumda: **yedek indir → eski uygulamayı kaldır → yenisini kur → Yedekten Yükle.**
- **Bilgisayar ile tablet arasında taşımak (Wi-Fi ile taşı):** iki cihaz aynı Wi-Fi'da olsun.
  1. İmparatorluğun bulunduğu cihazda **wi-fi ile taşı → Göndermeyi Aç**. Ekranda adres (192.168.x.x) ve 6
     haneli kod çıkar; 10 dakika açık kalır.
  2. Öteki cihazda **wi-fi ile taşı**, adresi ve kodu yazıp **Bağlan**, imparatorluğu seçip **Al**.
  Aynı imparatorluk iki cihazda da varsa gelen kayıt üzerine yazılır, eskisi yedek olarak saklanır. Windows
  "erişime izin ver" sorarsa **Özel ağlar** için izin verin. Dosyayla da olur: **yedek indir** → **Yedekten Yükle**.
- Android'in kendi yedeği açıksa (Google hesabı) kayıtlar oraya da girer; indirilen oyun dosyaları girmez.

## Kullanım

- **Tam ekran:** oyun ekranın tamamını kaplayarak açılır; durum ve gezinme çubukları gizlidir (kenardan
  kaydırınca bir süre görünür). Haberler, Şeref Kürsüsü ve üst bağlantılar için sol üstteki **Çık**'a basın;
  yeniden tam ekran için üstteki **Tam Ekran** düğmesi. Seçiminiz hatırlanır. Uygulama yatay ekranda açılır.
- Oyun fareyle oynanmak için yapıldı; dokunma tıklama gibi çalışır, haritayı parmakla kaydırabilirsiniz.
- **İki parmakla yakınlaştırma:** parmakları açınca yakınlaşır, kapayınca uzaklaşır (oyunun sağdaki kaydırıcısı
  da çalışır). İlk parmağın altındaki bina seçilebilir; boş yere dokununca seçim kalkar.
- Oyun açıkken tablet uzun süre başka uygulamadaysa Android uygulamayı kapatabilir; kayıtlar her hamlede
  yazıldığı için bir şey kaybolmaz. Hiç kapanmasın isterseniz: **Ayarlar → Pil → Arka plan kullanım sınırları →
  Asla uyumayan uygulamalar → Social Empires**.
- Geri tuşu bir önceki sayfaya döner (örneğin hile panelinden oyuna). Oyundayken yanlışlıkla çıkılmasın diye
  iki kez basmak gerekir; uygulama arka plana alınır, oyun kapanmaz. Arka plandayken oyun ve müzik durur.
- Android'in yazı boyutu ayarı oyun sayfasını büyütmez; düzen her cihazda aynı kalır.
- Discord gibi dış bağlantılar tarayıcıda açılır.

## Teknik notlar

- Sunucu yalnızca cihazın kendisine açıktır (`127.0.0.1:5050`); evdeki başka cihazlar bağlanamaz.
- Python sunucusu [Chaquopy](https://chaquo.com/chaquopy/) (MIT) ile çalışır; oyun Android WebView'da
  [Ruffle](https://ruffle.rs/) 0.7.1 ile açılır. Ruffle uygulamayla gelir.
- Her APK yayınlanmadan önce bir Android emülatöründe açılıp sınanır (`.github/workflows/android.yml`): yeni
  imparatorluk kurulur, oyun açılır ve açılışını bitirdiğini sunucuya bildirmelidir.
- Ruffle, GPU'su sınırlı cihazlarda (köşe uniform sınırı 256) kendi WebGL çizicisiyle açılır; çalışırken çökerse
  sayfa bir kez bu çiziciyle yeniden açılır. WebView'ın çizim süreci çökerse uygulama onu yeniden kurar.

## İmza anahtarı (depo sahibi için, bir kez)

Android, bir uygulamanın yeni sürümünü ancak aynı anahtarla imzalanmışsa eskisinin üstüne kurar. Anahtar gizlidir;
depoya konmaz, GitHub sırlarında durur.

Windows bilgisayarda adım adım (yaklaşık 10 dakika):

1. **Java'yı kurun.** <https://adoptium.net/> adresinden "Temurin 17 (LTS)" Windows `.msi` dosyasını indirip kurun.
   Kurulumda "Set JAVA_HOME" ve "Add to PATH" seçenekleri açık kalsın. Java zaten kuruluysa bu adımı atlayın.
2. **Bir şifre seçin.** En az 8 karakter; harf ve rakam yeterli, tırnak işareti kullanmayın. Şifreyi kâğıda yazın.
3. **PowerShell'i açın.** Başlat menüsüne `PowerShell` yazıp açın. Açılan pencere kendi klasörünüzdedir
   (`C:\Users\<adınız>`); anahtar dosyası oraya yazılır.
4. **Anahtarı üretin.** Aşağıdaki satırı yapıştırıp Enter'a basın. Şifreyi iki kez sorar; yazarken ekranda
   görünmez, bu normaldir.

   ```bash
   keytool -genkeypair -keystore socialempires.jks -storetype PKCS12 -alias socialempires -keyalg RSA -keysize 2048 -validity 36500 -dname "CN=Social Empires Turkce"
   ```

   "keytool tanınmıyor" derse PowerShell'i kapatıp yeniden açın; Java'nın yolu ancak yeni pencerede görünür.
5. **Dosyayı metne çevirip panoya alın.** Aşağıdaki satır anahtarı uzun bir metin olarak panoya kopyalar; ekranda bir
   şey yazmaz.

   ```bash
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("$PWD\socialempires.jks")) | Set-Clipboard
   ```

   Linux/macOS'ta: `base64 -w0 socialempires.jks`.
6. **GitHub'a iki sır ekleyin.** Depoda **Settings → Secrets and variables → Actions → New repository secret**:
   - Ad `ANDROID_IMZA`, değer: panodaki metin (Ctrl+V). **Add secret**.
   - Yeniden **New repository secret**: ad `ANDROID_IMZA_SIFRESI`, değer: 2. adımdaki şifre. **Add secret**.
7. **Dosyayı saklayın.** `socialempires.jks` dosyasını ve şifreyi güvenli bir yerde, en az iki kopya olarak
   saklayın (ör. USB bellek ve bulut). Kaybolursa sonraki sürümler eski kurulumun üstüne kurulamaz. Dosyayı kimseyle
   paylaşmayın, depoya koymayın.

Sırlar eklendikten sonraki ilk APK, tablette şimdiye kadar kurulu olan geçici anahtarlı uygulamanın üstüne **bir
kez daha** kurulamaz: o seferlik **yedek indir → eski uygulamayı kaldır → yenisini kur → Yedekten Yükle**. Sonraki
bütün güncellemeler doğrudan üstüne kurulur, kayıtlar korunur. CI'daki "İmza anahtarı (varsa)" adımı "Sahibin
anahtarıyla imzalanacak" yazıyorsa anahtar devrededir.

## Kaynaktan derleme

JDK 17, Android SDK ve Python 3.11 gerekir (Chaquopy derleme makinesinde uygulamanınkiyle aynı sürümü ister).

```bash
python araclar/android_paketi.py
gradle -p android :app:assembleRelease
```

APK: `android/app/build/outputs/apk/release/app-release.apk`. Emülatörde sınama: `bash android/sinama.sh <apk>`.
