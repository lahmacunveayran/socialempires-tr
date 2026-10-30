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
3. Google Play Protect uyarı verirse **Yine de yükle**'ye basın. Uygulama Play Store'da değildir.
4. **Social Empires** simgesine dokunun. Birkaç saniye "Oyun sunucusu açılıyor…" yazar, sonra imparatorluk
   seçme ekranı gelir.

## Kayıtlar

- Kayıtlar uygulamanın içindedir. **Uygulamayı kaldırmak kayıtları siler.** Kaldırmadan önce oyun sayfasındaki
  **yedek indir** ile yedek alın.
- Yeni sürüm, depo sahibinin imza anahtarı GitHub'a eklendiyse (aşağıda "İmza anahtarı") eskisinin üstüne kurulur
  ve kayıtlar korunur. Eklenmediyse her APK geçici bir anahtarla imzalanır; Android "uygulama yüklenmedi" der.
  O durumda: **yedek indir → eski uygulamayı kaldır → yenisini kur → Yedekten Yükle.**
- Bilgisayardaki imparatorluğu tablete taşımak: bilgisayarda **yedek indir**, dosyayı tablete atın,
  uygulamada **Yedekten Yükle**. Tersi de aynı.
- Android'in kendi yedeği açıksa (Google hesabı) kayıtlar oraya da girer; indirilen oyun dosyaları girmez.

## Kullanım

- Oyun fareyle oynanmak için yapıldı; dokunma tıklama gibi çalışır, haritayı parmakla kaydırabilirsiniz.
  Yakınlaştırma oyunun sağdaki kaydırıcısıyla yapılır.
- Geri tuşu bir önceki sayfaya döner (örneğin hile panelinden oyuna).
- Discord gibi dış bağlantılar tarayıcıda açılır.

## Teknik notlar

- Sunucu yalnızca cihazın kendisine açıktır (`127.0.0.1:5050`); evdeki başka cihazlar bağlanamaz.
- Python sunucusu [Chaquopy](https://chaquo.com/chaquopy/) (MIT) ile çalışır; oyun Android WebView'da
  [Ruffle](https://ruffle.rs/) 0.7.1 ile açılır. Ruffle uygulamayla gelir.
- Her APK yayınlanmadan önce bir Android emülatöründe açılıp sınanır (`.github/workflows/android.yml`).

## İmza anahtarı (depo sahibi için, bir kez)

Android, bir uygulamanın yeni sürümünü ancak aynı anahtarla imzalanmışsa eskisinin üstüne kurar. Anahtar gizlidir;
depoya konmaz, GitHub sırlarında durur.

1. Java yüklü bir bilgisayarda anahtarı üretin (şifreyi siz seçin, bir yere not edin):

   ```bash
   keytool -genkeypair -keystore socialempires.jks -storetype PKCS12 -alias socialempires -keyalg RSA -keysize 2048 -validity 36500 -dname "CN=Social Empires Turkce"
   ```

2. Dosyayı metne çevirin: Windows PowerShell'de
   `[Convert]::ToBase64String([IO.File]::ReadAllBytes("socialempires.jks")) | Set-Clipboard`
   (Linux/macOS: `base64 -w0 socialempires.jks`).
3. GitHub'da depo **Settings → Secrets and variables → Actions → New repository secret**:
   `ANDROID_IMZA` = kopyalanan metin, `ANDROID_IMZA_SIFRESI` = seçtiğiniz şifre.
4. `socialempires.jks` dosyasını güvenli bir yerde saklayın. Kaybolursa sonraki sürümler eski kurulumun üstüne
   kurulamaz.

## Kaynaktan derleme

JDK 17, Android SDK ve Python 3.11 gerekir (Chaquopy derleme makinesinde uygulamanınkiyle aynı sürümü ister).

```bash
python araclar/android_paketi.py
gradle -p android :app:assembleRelease
```

APK: `android/app/build/outputs/apk/release/app-release.apk`. Emülatörde sınama: `bash android/sinama.sh <apk>`.
