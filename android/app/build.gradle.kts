plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

// Oyun dosyaları ve simge derlemeden önce hazırlanır: python araclar/android_paketi.py
val oyunVerisi = file("build/oyun-verisi")
if (!oyunVerisi.isDirectory) {
    throw GradleException("Önce oyun dosyalarını hazırlayın: python araclar/android_paketi.py")
}

android {
    namespace = "io.github.lahmacunveayran.socialempirestr"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.lahmacunveayran.socialempirestr"
        minSdk = 24
        targetSdk = 35
        // Güncelleme eskisinin üstüne kurulsun diye her CI derlemesinde artar
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = System.getenv("SE_SURUM") ?: "gelistirme"
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    // İmza anahtarı depoda tutulmaz. Depo sahibi GitHub sırlarına eklediyse (ANDROID.md "İmza anahtarı") CI onunla
    // imzalar: yeni sürüm eskisinin üstüne kurulur, kayıtlar korunur. Yoksa her derleme geçici hata ayıklama
    // anahtarıyla imzalanır ve güncelleme için eski uygulama kaldırılmalıdır.
    val imzaDosyasi = System.getenv("SE_IMZA_DOSYASI")?.let { file(it) }?.takeIf { it.isFile }
    signingConfigs {
        if (imzaDosyasi != null) {
            create("sahibin") {
                storeFile = imzaDosyasi
                storePassword = System.getenv("SE_IMZA_SIFRESI")
                keyAlias = System.getenv("SE_IMZA_ADI") ?: "socialempires"
                keyPassword = System.getenv("SE_IMZA_SIFRESI")
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName(if (imzaDosyasi != null) "sahibin" else "debug")
        }
    }

    sourceSets {
        getByName("main") {
            res.srcDir("build/oyun-res")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

chaquopy {
    defaultConfig {
        version = "3.12"
        pip {
            install("flask")
            install("waitress")
            install("jsonpatch")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("build/oyun-verisi")
        }
    }
}
