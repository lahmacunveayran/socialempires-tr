package io.github.lahmacunveayran.socialempirestr;

import android.annotation.TargetApi;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.DocumentsContract;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.RenderProcessGoneDetail;
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
import java.security.SecureRandom;

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
    // Sayfa bu işaretle uygulamada olduğunu anlar ve oyun modunu (tam ekran) varsayılan açar (oyun.js)
    private static final String AJAN_ISARETI = " SocialEmpiresTR-Android";
    private static final long CIKIS_ARALIGI_MS = 2000;

    // Sunucu süreç boyunca bir kez açılır; ekran yeniden kurulsa da çalışmaya devam eder
    private static boolean sunucuAcildi = false;
    private static volatile String sunucuHatasi = null;
    // Bu süreç için gizli jeton: yalnızca bu uygulamanın WebView'u çerez olarak gönderir (oyun/sunucu.py _uygulama_jetonu)
    private static final String JETON = yeniJeton();

    private static String yeniJeton() {
        byte[] b = new byte[24];
        new SecureRandom().nextBytes(b);
        StringBuilder s = new StringBuilder();
        for (byte x : b) {
            s.append(String.format("%02x", x));
        }
        return s.toString();
    }

    private final Handler ana = new Handler(Looper.getMainLooper());
    private FrameLayout kok;
    private WebView web;
    private TextView durum;
    private ValueCallback<Uri[]> dosyaGeriCagrisi;
    private byte[] kaydedilecek;
    // Oyunun (Ruffle'ın) tam ekran isteği: WebView tam ekran öğesini ayrı bir görünüm olarak verir
    private View tamEkranGorunumu;
    private WebChromeClient.CustomViewCallback tamEkranGeriCagrisi;
    private long sonGeri;
    private static final long COKME_PENCERESI_MS = 120_000;
    private static final int EN_COK_COKME = 3;
    private int cokmeler;
    private long ilkCokme;
    private boolean onde;

    @Override
    protected void onCreate(Bundle kayitliDurum) {
        super.onCreate(kayitliDurum);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        // Kamera çentiği/deliği olan ekranlarda oyun o bölgeyi de kullanır
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            getWindow().getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }
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
        kok = new FrameLayout(this);
        kok.addView(web);
        kok.addView(durum);
        setContentView(kok);
        // Tam ekranda (çubuklar gizli, pencere kenardan kenara) Android sayfayı klavyeye göre küçültmez; klavye
        // Wi-Fi taşıma kodu gibi alanları örterdi. Klavye yüksekliği kadar alttan boşluk bırakılır.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            kok.setOnApplyWindowInsetsListener((v, ekler) -> {
                v.setPadding(0, 0, 0, ekler.getInsets(WindowInsets.Type.ime()).bottom);
                return ekler;
            });
        }

        CookieManager.getInstance().setCookie(ADRES, "se_uygulama=" + JETON + "; Path=/; HttpOnly; SameSite=Strict");
        CookieManager.getInstance().flush();
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
        // Android'in yazı boyutu ayarı (Samsung'da sık büyütülür) sayfa düzenini bozmasın; oyun kendi boyutunu kullanır
        ayar.setTextZoom(100);
        if (!ayar.getUserAgentString().contains(AJAN_ISARETI)) {
            ayar.setUserAgentString(ayar.getUserAgentString() + AJAN_ISARETI);
        }
        web.setVisibility(View.INVISIBLE);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest istek) {
                Uri adres = istek.getUrl();
                if ("127.0.0.1".equals(adres.getHost())) {
                    return false;
                }
                // Discord, GitHub gibi dış bağlantılar tarayıcıda açılır; file:, intent: gibi şemalar açılmaz
                // (file: Android 7+ FileUriExposedException ile uygulamayı düşürür)
                String sema = adres.getScheme() == null ? "" : adres.getScheme().toLowerCase();
                if (sema.equals("http") || sema.equals("https") || sema.equals("mailto")) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, adres));
                    } catch (RuntimeException ignored) {
                    }
                }
                return true;
            }

            // WebView'ın çizim süreci çökerse (bellek yetmezse ya da grafik sürücüsü düşerse) Android, bu işlenmezse
            // uygulamayı da kapatır. WebView yeniden kurulur ve oyun yeniden yüklenir; sunucu çalışmaya devam eder.
            @Override
            @TargetApi(Build.VERSION_CODES.O) // Android 8 öncesinde çağrılmaz
            public boolean onRenderProcessGone(WebView v, RenderProcessGoneDetail ayrinti) {
                Log.e(TAG, "WebView cizim sureci kapandi (cokme: " + ayrinti.didCrash() + ")");
                tamEkrandanCik(); // ölü WebView'ın tam ekran görünümü yenisinin üstünde kalmasın
                kok.removeView(v);
                v.destroy();
                long simdi = System.currentTimeMillis();
                cokmeler = simdi - ilkCokme > COKME_PENCERESI_MS ? 1 : cokmeler + 1;
                if (cokmeler == 1) {
                    ilkCokme = simdi;
                }
                web = new WebView(MainActivity.this);
                kok.addView(web, 0);
                webAyarla();
                if (cokmeler > EN_COK_COKME) {
                    // Çökme döngüsü: yeniden yükleyip durmak yerine nedeni gösterilir; dokununca yeniden denenir
                    durum.setText(R.string.ekran_cokuyor);
                    durum.setVisibility(View.VISIBLE);
                    durum.setOnClickListener(d -> {
                        durum.setOnClickListener(null);
                        durum.setVisibility(View.GONE);
                        cokmeler = 0;
                        web.setVisibility(View.VISIBLE);
                        web.loadUrl(ADRES);
                    });
                    return true;
                }
                web.setVisibility(View.VISIBLE);
                web.loadUrl(ADRES);
                if (!onde) {
                    web.onPause(); // arka planda bellek geri alındıysa oyun öne gelince çalışsın
                }
                Toast.makeText(MainActivity.this, R.string.yeniden_yukleniyor, Toast.LENGTH_LONG).show();
                return true;
            }
        });

        // "Yedekten yükle": dosya seçici
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onShowCustomView(View gorunum, CustomViewCallback geriCagri) {
                if (tamEkranGorunumu != null) {
                    geriCagri.onCustomViewHidden();
                    return;
                }
                Log.i(TAG, "Tam ekran istendi (onShowCustomView)");
                tamEkranGorunumu = gorunum;
                tamEkranGeriCagrisi = geriCagri;
                kok.addView(gorunum, new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
                sistemCubuklariniGizle();
            }

            @Override
            public void onHideCustomView() {
                tamEkrandanCik();
            }

            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> geriCagri, FileChooserParams secenek) {
                if (dosyaGeriCagrisi != null) {
                    dosyaGeriCagrisi.onReceiveValue(null);
                }
                dosyaGeriCagrisi = geriCagri;
                Intent sec = new Intent(Intent.ACTION_GET_CONTENT);
                sec.addCategory(Intent.CATEGORY_OPENABLE);
                // Sayfa yalnızca resim istiyorsa (profil resmi) galeri açılır; yedek yükleme her dosyayı gösterir
                String[] turler = secenek.getAcceptTypes();
                boolean resim = turler != null && turler.length > 0 && turler[0] != null && turler[0].startsWith("image/");
                sec.setType(resim ? "image/*" : "*/*");
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
                Python.getInstance().getModule("android_giris").callAttr("baslat", null, JETON);
                sunucuHatasi = "Sunucu kapandı.";
            } catch (Throwable hata) {
                Log.e(TAG, "Sunucu acilamadi", hata);
                sunucuHatasi = hata.toString();
            }
            synchronized (MainActivity.class) {
                sunucuAcildi = false; // yeniden denenebilsin (ekrana dokununca)
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
            ana.post(() -> {
                durum.setText(getString(R.string.acilamadi) + ayrinti + "\n\n" + getString(R.string.yeniden_dene));
                durum.setOnClickListener(d -> {
                    durum.setOnClickListener(null);
                    durum.setText(R.string.aciliyor);
                    sunucuHatasi = null;
                    sunucuyuAc();
                    hazirOluncaAc();
                });
            });
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

    private void yedekDosyasiniSil(Uri adres) {
        try {
            DocumentsContract.deleteDocument(getContentResolver(), adres);
        } catch (Exception ignored) {
            // silinemezse boş dosya kalır; kullanıcıya zaten "kaydedilemedi" denir
        }
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
            if (sonuc != RESULT_OK || veri == null || veri.getData() == null) {
                return;
            }
            Uri hedef = veri.getData();
            if (icerik == null) {
                // Seçici açıkken uygulama kapatıldı: oluşturulan boş dosya "yedek var" sanılmasın
                yedekDosyasiniSil(hedef);
                Toast.makeText(this, R.string.yedek_kaydedilemedi, Toast.LENGTH_LONG).show();
                return;
            }
            // Bulut belge sağlayıcılarında yazma uzun sürebilir: ana iş parçacığını kilitlemesin
            new Thread(() -> {
                boolean tamam;
                try (OutputStream cikti = getContentResolver().openOutputStream(hedef)) {
                    if (cikti == null) {
                        throw new IOException("Dosya açılamadı");
                    }
                    cikti.write(icerik);
                    tamam = true;
                } catch (IOException | RuntimeException hata) {
                    Log.e(TAG, "Yedek kaydedilemedi", hata);
                    yedekDosyasiniSil(hedef);
                    tamam = false;
                }
                boolean sonucu = tamam;
                ana.post(() -> Toast.makeText(this, sonucu ? R.string.yedek_kaydedildi : R.string.yedek_kaydedilemedi,
                        sonucu ? Toast.LENGTH_SHORT : Toast.LENGTH_LONG).show());
            }, "yedek-yaz").start();
        }
    }

    @Override
    public void onConfigurationChanged(android.content.res.Configuration yeni) {
        super.onConfigurationChanged(yeni);
        Log.i(TAG, "Yapilandirma degisti: yon " + yeni.orientation + ", " + yeni.screenWidthDp + "x" + yeni.screenHeightDp + " dp");
    }

    @Override
    protected void onStart() {
        super.onStart();
        onde = true;
        web.resumeTimers();
    }

    @Override
    protected void onStop() {
        super.onStop();
        Log.i(TAG, "onStop");
        onde = false;
        // Arka plandayken oyun döngüsü ve müzik dursun (pil); sunucu ve bot dünyası çalışmayı sürdürür.
        // onPause'da değil: Android 7-9'da bölünmüş ekranda oyun görünürken de onPause gelir.
        web.pauseTimers();
    }

    @Override
    protected void onDestroy() {
        // Etkinlik yeniden kurulursa eski WebView ve çizim süreci bellekte kalmasın
        tamEkrandanCik();
        kok.removeAllViews();
        web.destroy();
        super.onDestroy();
    }

    @Override
    public void onWindowFocusChanged(boolean odakta) {
        super.onWindowFocusChanged(odakta);
        Log.i(TAG, "Pencere odagi: " + odakta);
        if (odakta) {
            sistemCubuklariniGizle();
        }
    }

    /** Tam ekran: sistem çubukları gizlenir, kenardan kaydırınca bir süre görünüp yine gizlenir. */
    private void sistemCubuklariniGizle() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            // Android 11+: eski SYSTEM_UI_FLAG_* bayrakları Android 15'i hedefleyen uygulamada güvenilir değil
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController denetci = getWindow().getInsetsController();
            if (denetci != null) {
                denetci.hide(WindowInsets.Type.systemBars());
                denetci.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
        }
    }

    private void tamEkrandanCik() {
        if (tamEkranGorunumu == null) {
            return;
        }
        kok.removeView(tamEkranGorunumu);
        tamEkranGorunumu = null;
        if (tamEkranGeriCagrisi != null) {
            tamEkranGeriCagrisi.onCustomViewHidden();
            tamEkranGeriCagrisi = null;
        }
        sistemCubuklariniGizle();
    }

    @Override
    public void onBackPressed() {
        if (tamEkranGorunumu != null) {
            tamEkrandanCik();
            return;
        }
        String adres = web.getUrl();
        String yol = adres == null ? null : Uri.parse(adres).getPath();
        // Oyundayken (ya da gidecek önceki sayfa yokken) yanlışlıkla basılan geri oyunu kapatmasın: ikinci basışta
        // uygulama arka plana alınır, sunucu ve kayıt çalışmayı sürdürür
        if (yol == null || yol.startsWith("/play") || !web.canGoBack()) {
            long simdi = System.currentTimeMillis();
            if (simdi - sonGeri < CIKIS_ARALIGI_MS) {
                moveTaskToBack(true);
            } else {
                sonGeri = simdi;
                Toast.makeText(this, R.string.cikmak_icin_tekrar, Toast.LENGTH_SHORT).show();
            }
            return;
        }
        web.goBack();
    }

    @Override
    protected void onPause() {
        super.onPause();
        Log.i(TAG, "onPause");
        web.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    protected void onResume() {
        super.onResume();
        Log.i(TAG, "onResume");
        web.onResume();
        sistemCubuklariniGizle();
    }
}
