package io.github.lahmacunveayran.socialempirestr;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Oyunun Python sunucusunu (oyun/sunucu.py) uygulamanın içinde açar ve oyun sayfasını tam ekran gösterir.
 * Sunucu yalnızca 127.0.0.1:5050'de dinler; bilgisayar gerekmez.
 */
public class MainActivity extends Activity {
    private static final String TAG = "SocialEmpires";
    private static final String ADRES = "http://127.0.0.1:5050/";
    private static final long HAZIR_SURESI_MS = 240_000;
    private static final int DOSYA_SEC = 1;
    private static final int DOSYA_KAYDET = 2;

    // Sunucu süreç boyunca bir kez açılır; ekran yeniden kurulsa da çalışmaya devam eder
    private static boolean sunucuAcildi = false;
    private static volatile String sunucuHatasi = null;

    private final Handler ana = new Handler(Looper.getMainLooper());
    private WebView web;
    private TextView durum;
    private ValueCallback<Uri[]> dosyaGeriCagrisi;
    private byte[] kaydedilecek;

    @Override
    protected void onCreate(Bundle kayitliDurum) {
        super.onCreate(kayitliDurum);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        // Yalnızca CI sınaması (android/sinama.sh) açar: WebView'a adb üzerinden DevTools ile bağlanılabilir
        if (getIntent().getBooleanExtra("sinama", false)) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        web = new WebView(this);
        durum = new TextView(this);
        durum.setText(R.string.aciliyor);
        durum.setTextColor(0xFFFFF3D6);
        durum.setTextSize(20);
        durum.setGravity(Gravity.CENTER);
        durum.setPadding(48, 48, 48, 48);
        FrameLayout kok = new FrameLayout(this);
        kok.addView(web);
        kok.addView(durum);
        setContentView(kok);

        webAyarla();
        sunucuyuAc();
        hazirOluncaAc();
    }

    private void webAyarla() {
        WebSettings ayar = web.getSettings();
        ayar.setJavaScriptEnabled(true);
        ayar.setDomStorageEnabled(true);
        ayar.setMediaPlaybackRequiresUserGesture(false);
        ayar.setAllowFileAccess(false);
        web.setVisibility(View.INVISIBLE);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest istek) {
                Uri adres = istek.getUrl();
                if ("127.0.0.1".equals(adres.getHost())) {
                    return false;
                }
                // Discord, GitHub gibi dış bağlantılar tarayıcıda açılır
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, adres));
                } catch (ActivityNotFoundException ignored) {
                }
                return true;
            }
        });

        // "Yedekten yükle": dosya seçici
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> geriCagri, FileChooserParams secenek) {
                if (dosyaGeriCagrisi != null) {
                    dosyaGeriCagrisi.onReceiveValue(null);
                }
                dosyaGeriCagrisi = geriCagri;
                Intent sec = new Intent(Intent.ACTION_GET_CONTENT);
                sec.addCategory(Intent.CATEGORY_OPENABLE);
                sec.setType("*/*");
                try {
                    startActivityForResult(sec, DOSYA_SEC);
                } catch (ActivityNotFoundException hata) {
                    dosyaGeriCagrisi = null;
                    return false;
                }
                return true;
            }
        });

        // "Yedek indir": dosya sunucudan alınır, kullanıcının seçtiği yere kaydedilir
        web.setDownloadListener((adres, tarayici, icerikTuru, mime, uzunluk) -> yedekIndir(adres, icerikTuru, mime));
    }

    private void sunucuyuAc() {
        synchronized (MainActivity.class) {
            if (sunucuAcildi) {
                return;
            }
            sunucuAcildi = true;
        }
        Thread is = new Thread(() -> {
            try {
                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(getApplicationContext()));
                }
                Python.getInstance().getModule("android_giris").callAttr("baslat");
                sunucuHatasi = "Sunucu kapandı.";
            } catch (Throwable hata) {
                Log.e(TAG, "Sunucu acilamadi", hata);
                sunucuHatasi = hata.toString();
            }
        }, "oyun-sunucusu");
        is.setDaemon(true);
        is.start();
    }

    private void hazirOluncaAc() {
        new Thread(() -> {
            long son = System.currentTimeMillis() + HAZIR_SURESI_MS;
            while (System.currentTimeMillis() < son && sunucuHatasi == null) {
                if (hazirMi()) {
                    ana.post(() -> {
                        durum.setVisibility(View.GONE);
                        web.setVisibility(View.VISIBLE);
                        if (web.getUrl() == null) {
                            web.loadUrl(ADRES);
                        }
                    });
                    return;
                }
                try {
                    Thread.sleep(400);
                } catch (InterruptedException e) {
                    return;
                }
            }
            String ayrinti = sunucuHatasi != null ? "\n\n" + sunucuHatasi : "";
            ana.post(() -> durum.setText(getString(R.string.acilamadi) + ayrinti));
        }, "oyun-bekleme").start();
    }

    private static boolean hazirMi() {
        try {
            HttpURLConnection baglanti = (HttpURLConnection) new URL(ADRES + "saglik/hazir").openConnection();
            baglanti.setConnectTimeout(1000);
            baglanti.setReadTimeout(2000);
            try {
                return baglanti.getResponseCode() == 200;
            } finally {
                baglanti.disconnect();
            }
        } catch (IOException e) {
            return false;
        }
    }

    private void yedekIndir(String adres, String icerikTuru, String mime) {
        String ad = URLUtil.guessFileName(adres, icerikTuru, mime);
        String cerez = CookieManager.getInstance().getCookie(adres);
        new Thread(() -> {
            try {
                HttpURLConnection baglanti = (HttpURLConnection) new URL(adres).openConnection();
                if (cerez != null) {
                    baglanti.setRequestProperty("Cookie", cerez);
                }
                ByteArrayOutputStream veri = new ByteArrayOutputStream();
                try (InputStream girdi = baglanti.getInputStream()) {
                    byte[] tampon = new byte[64 * 1024];
                    int n;
                    while ((n = girdi.read(tampon)) > 0) {
                        veri.write(tampon, 0, n);
                    }
                } finally {
                    baglanti.disconnect();
                }
                ana.post(() -> {
                    kaydedilecek = veri.toByteArray();
                    Intent kaydet = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    kaydet.addCategory(Intent.CATEGORY_OPENABLE);
                    kaydet.setType("application/json");
                    kaydet.putExtra(Intent.EXTRA_TITLE, ad);
                    startActivityForResult(kaydet, DOSYA_KAYDET);
                });
            } catch (IOException hata) {
                Log.e(TAG, "Yedek indirilemedi", hata);
                ana.post(() -> Toast.makeText(this, R.string.yedek_kaydedilemedi, Toast.LENGTH_LONG).show());
            }
        }, "yedek-indir").start();
    }

    @Override
    protected void onActivityResult(int istek, int sonuc, Intent veri) {
        super.onActivityResult(istek, sonuc, veri);
        if (istek == DOSYA_SEC && dosyaGeriCagrisi != null) {
            dosyaGeriCagrisi.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(sonuc, veri));
            dosyaGeriCagrisi = null;
        } else if (istek == DOSYA_KAYDET) {
            byte[] icerik = kaydedilecek;
            kaydedilecek = null;
            if (sonuc != RESULT_OK || veri == null || veri.getData() == null || icerik == null) {
                return;
            }
            try (OutputStream cikti = getContentResolver().openOutputStream(veri.getData())) {
                if (cikti == null) {
                    throw new IOException("Dosya açılamadı");
                }
                cikti.write(icerik);
                Toast.makeText(this, R.string.yedek_kaydedildi, Toast.LENGTH_SHORT).show();
            } catch (IOException hata) {
                Log.e(TAG, "Yedek kaydedilemedi", hata);
                Toast.makeText(this, R.string.yedek_kaydedilemedi, Toast.LENGTH_LONG).show();
            }
        }
    }

    @Override
    public void onWindowFocusChanged(boolean odakta) {
        super.onWindowFocusChanged(odakta);
        if (odakta) {
            // Tam ekran: sistem çubukları kenardan kaydırınca görünür, sonra yine gizlenir
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
        }
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        web.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }
}
