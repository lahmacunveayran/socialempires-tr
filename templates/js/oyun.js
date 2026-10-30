// Oyun sayfası: çerçeve ölçeği, "Krallığa Gir" düğmesi, yükleme ekranı,
// Diyar Haberleri şeridi ve Şeref Kürsüsü.
(function () {
  "use strict";
  var AYAR = window.OYUN_AYARI;
  var HAREKETSIZ = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SAYI = new Intl.NumberFormat("tr-TR");

  function el(etiket, sinif, metin) {
    var e = document.createElement(etiket);
    if (sinif) e.className = sinif;
    if (metin !== undefined) e.textContent = metin;
    return e;
  }

  // Sayan sayı (NumberTicker): 0'dan hedefe yavaşlayarak sayar.
  function say(e, hedef, sure) {
    hedef = Number(hedef) || 0;
    if (HAREKETSIZ) { e.textContent = SAYI.format(hedef); return; }
    var bas = performance.now(); sure = sure || 1400;
    (function adim(t) {
      var k = Math.min(1, (t - bas) / sure);
      e.textContent = SAYI.format(Math.round(hedef * (1 - Math.pow(2, -10 * k))));
      if (k < 1) requestAnimationFrame(adim); else e.textContent = SAYI.format(hedef);
    })(bas);
  }
  document.querySelectorAll("[data-say]").forEach(function (e) { say(e, e.dataset.say); });
  var xpDolum = document.querySelector(".xp-dolum");
  if (xpDolum) requestAnimationFrame(function () { xpDolum.style.width = xpDolum.dataset.oran + "%"; });

  // "3 dk önce"
  var GORELI = new Intl.RelativeTimeFormat("tr", { numeric: "auto" });
  function once(zaman) {
    var fark = Math.round(zaman - Date.now() / 1000);
    if (fark > -45) return "az önce";
    if (fark > -3600) return GORELI.format(Math.round(fark / 60), "minute");
    if (fark > -86400) return GORELI.format(Math.round(fark / 3600), "hour");
    return GORELI.format(Math.round(fark / 86400), "day");
  }

  // Fareyi izleyen ışık (MagicCard)
  document.addEventListener("pointermove", function (o) {
    var panel = o.target.closest && o.target.closest(".panel");
    if (!panel) return;
    var k = panel.getBoundingClientRect();
    panel.style.setProperty("--mx", (o.clientX - k.left) + "px");
    panel.style.setProperty("--my", (o.clientY - k.top) + "px");
  });


  // --- Çerçeve ölçeği: oyun EXACT_FIT ile kutuya esner, oran tam 760:600 kalmalı.
  var kutu = document.getElementById("oyun-kutusu");

  // Paralaks yalnızca transform ile; prefers-reduced-motion açıkken CSS kapatır.
  window.addEventListener("scroll", function () {
    document.documentElement.style.setProperty("--kaydirma", String(window.scrollY));
  }, { passive: true });

  // --- Yükleme ekranı: Arthur'un nasihatleri
  var NASIHATLER = [
    "Konağını büyüt; yeni binaların kapısı ondan açılır.",
    "Köylülerin boş durmasın: odun, taş ve yiyecek imparatorluğun damarıdır.",
    "Kulelerini köyün kenarına diz; akıncılar önce onlara çarpar.",
    "Bir rakibe saldırmadan önce ordusunun gücüne bak, Arthur'dan öğüt.",
    "Büyücünün İksirleri her ay yenilenir; ejderhayı kaçırma.",
    "Okçu Ocağı'nda yetişen okçular uzaktan vurur, kılıççıların arkasında dursun.",
    "Kardeşlik Loncası, arkadaş isteyen binaların işçisini gönderir.",
    "Kalkanın varken kimse sana akın edemez; sen saldırınca kalkan düşer.",
  ];
  var yukleme = document.getElementById("yukleme");
  var dolum = yukleme.querySelector(".dolum");
  var asama = yukleme.querySelector(".asama");
  var nasihat = yukleme.querySelector(".nasihat");
  var nasihatSayaci = null;
  function ilerle(yuzde, metin) {
    dolum.style.width = yuzde + "%";
    asama.textContent = metin;
  }
  function nasihatDegistir() {
    nasihat.textContent = "Arthur: " + NASIHATLER[Math.floor(Math.random() * NASIHATLER.length)];
  }

  // --- Krallığa Gir: Ruffle oyuncusu ancak tıklanınca kurulur. Tıklama bir
  // kullanıcı hareketi olduğu için tarayıcı sesi de açar; Ruffle'ın kendi
  // turuncu "oynat" düğmesi ve ses örtüsü hiç görünmez.
  var perde = document.getElementById("giris-perdesi");
  var dugme = document.getElementById("kralliga-gir");
  dugme.addEventListener("click", function () {
    perde.hidden = true;
    yukleme.hidden = false;
    nasihatDegistir();
    nasihatSayaci = setInterval(nasihatDegistir, 6000);
    ilerle(15, "Ruffle hazırlanıyor...");
    if (window.RufflePlayer && window.RufflePlayer.newest) return oyunuBaslat();
    var betik = document.createElement("script");
    betik.src = AYAR.ruffle;
    betik.onload = oyunuBaslat;
    betik.onerror = function () { ilerle(15, "Ruffle yüklenemedi. Sayfayı yenileyin."); };
    document.head.appendChild(betik);
  });

  // Ruffle'ın varsayılan çizicisi (wgpu-webgl) köşe gölgelendiricisinde 256'dan fazla uniform ister. Birçok telefon ve
  // tablet GPU'su (ve Android emülatörü) en fazla 256 verir; o zaman Ruffle "unreachable" ile çöker ve oyun açılmaz.
  // Böyle GPU'larda Ruffle'ın kendi WebGL çizicisi seçilir (DAG-07).
  function kisitliGpu() {
    try {
      var tuval = document.createElement("canvas");
      var gl = tuval.getContext("webgl2") || tuval.getContext("webgl");
      return !gl || gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS) <= 256;
    } catch (e) {
      return true;
    }
  }

  function oyunuBaslat() {
    window.RufflePlayer = window.RufflePlayer || {};
    window.RufflePlayer.config = {
      autoplay: "on",
      unmuteOverlay: "hidden",
      splashScreen: false,
      contextMenu: "rightClickOnly", // dokunmatikte uzun basma menü açmasın
      allowScriptAccess: true,       // oyun ExternalInterface kullanıyor
      backgroundColor: "#669C2C",
      letterbox: "off",
      logLevel: "warn",
    };
    if (kisitliGpu()) window.RufflePlayer.config.preferredRenderer = "webgl";
    var ruffle = window.RufflePlayer.newest();
    var oyuncu = ruffle.createPlayer();
    kutu.appendChild(oyuncu);
    ilerle(35, "Yükleyici indiriliyor...");
    oyuncu.addEventListener("loadedmetadata", function () { ilerle(60, "Oyun dosyası indiriliyor..."); });
    oyuncu.addEventListener("loadeddata", function () {
      ilerle(100, "Diyar kuruluyor...");
      setTimeout(function () {
        yukleme.hidden = true;
        clearInterval(nasihatSayaci);
        oyuncu.focus(); // ilk tıklama odağa harcanmasın
      }, 2500);
    });
    oyuncu.load({ url: AYAR.swf, parameters: AYAR.parametreler });
  }

  // --- Diyar Haberleri: 15 saniyede bir yoklama; en fazla 5 saniyede bir satır.
  var liste = document.getElementById("haberler");
  var ozet = document.getElementById("haber-ozeti");
  var durdurDugmesi = document.getElementById("haber-durdur");
  var sonId = 0, kuyruk = [], durdu = false, ilkYukleme = true;
  var EN_COK_SATIR = 30;

  function saat(zaman) {
    var t = new Date(zaman * 1000);
    return t.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" });
  }
  // Simgeler oyunun kendi armalarıdır (images_new/b_*.png).
  var ARMA = AYAR.varlik + "images_new/";
  var HABER_SIMGELERI = { savas: "b_4.png", seviye: "b_14.png", ekonomi: "b_5.png", lonca: "b_1.png", dunya: "b_9.png" };
  var HABER_TURLERI = { savas: "Savaş", seviye: "Seviye", ekonomi: "Ordu", lonca: "Lonca", dunya: "Dünya" };
  function satirEkle(olay, yeni) {
    var bos = liste.querySelector(".bos-haber");
    if (bos) bos.remove();
    var li = el("li", "haber" + (yeni ? " yeni" : ""));
    li.dataset.tur = olay.tur;
    var govde = el("div");
    var ust = el("div", "ust");
    var zaman = el("time", "", once(olay.zaman));
    zaman.dateTime = new Date(olay.zaman * 1000).toISOString();
    zaman.dataset.zaman = olay.zaman;
    ust.append(el("span", "tur", HABER_TURLERI[olay.tur] || "Haber"), zaman);
    govde.append(ust, el("p", "", olay.metin));
    var ikon = el("img", "ikon");
    ikon.src = ARMA + (HABER_SIMGELERI[olay.tur] || "b_7.png");
    ikon.alt = "";
    li.append(ikon, govde);
    liste.insertBefore(li, liste.firstChild);
    while (liste.children.length > EN_COK_SATIR) liste.removeChild(liste.lastChild);
    ozet.textContent = "Son haber: " + olay.metin;
  }
  setInterval(function () {
    liste.querySelectorAll("time[data-zaman]").forEach(function (t) { t.textContent = once(Number(t.dataset.zaman)); });
  }, 30000);
  function yokla() {
    fetch("/dunya/olaylar?sonra=" + sonId, { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        sonId = v.son; // sunucu yeniden başladıysa numarayı o sıfırlar
        if (ilkYukleme) {
          v.olaylar.slice(-8).forEach(function (o) { satirEkle(o, false); });
          ilkYukleme = false;
        } else {
          kuyruk = kuyruk.concat(v.olaylar);
        }
      })
      .catch(function () {});
  }
  setInterval(function () {
    if (!durdu && kuyruk.length) satirEkle(kuyruk.shift(), true);
  }, 5000);
  durdurDugmesi.addEventListener("click", function () {
    durdu = !durdu;
    durdurDugmesi.textContent = durdu ? "Sürdür" : "Durdur";
    durdurDugmesi.setAttribute("aria-pressed", String(durdu));
  });
  yokla();
  setInterval(yokla, 15000);

  // --- Şeref Kürsüsü: ilk üç podyumda, kalanlar kabartma satırlarda.
  var kursu = document.getElementById("kursu");
  function portre(o) {
    var img = el("img"); img.src = o.resim || "/img/profile/1025.png"; img.alt = ""; img.loading = "lazy";
    return img;
  }
  function levhaSatiri(o, i, deger) {
    var li = el("li", o.ben ? "ben" : "");
    li.style.setProperty("--i", i);
    var ad = el("span", "ad", o.ad);
    if (o.rutbe) ad.appendChild(el("small", "", o.rutbe));
    li.append(el("span", "no", o.sira), portre(o), ad, deger);
    return li;
  }
  function kalkan(ust, sayi) {
    var k = el("span", "kalkan-rozet yazi-altin");
    k.append(el("small", "", ust), document.createTextNode(sayi));
    return k;
  }
  function kursuYukle() {
    fetch("/dunya/kursu", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        kursu.textContent = "";
        var podyum = el("div", "podyum");
        [1, 0, 2].forEach(function (i) {
          var o = v.ilk[i];
          if (!o) return;
          var b = el("div", "basamak b" + (i + 1));
          var p = el("div", "portre");
          p.appendChild(portre(o));
          if (i === 0) {
            var tac = el("img", "tac");
            tac.src = ARMA + "weekly_tournament_bot3.png";
            tac.alt = "";
            p.appendChild(tac);
          }
          var blok = el("div", "blok");
          blok.append(el("span", "no yazi-oyun", i + 1), el("span", "ad", o.ad), el("span", "sv", "sv. " + o.seviye));
          b.append(p, blok, el("span", "rt", o.rutbe));
          podyum.appendChild(b);
        });
        var levha = el("ol", "levha");
        v.ilk.slice(3).forEach(function (o, i) { levha.appendChild(levhaSatiri(o, i, kalkan("sv", o.seviye))); });
        if (v.ben && !v.ilk.some(function (o) { return o.ben; })) {
          levha.appendChild(el("li", "ayrac", "• • •"));
          levha.appendChild(levhaSatiri(Object.assign({}, v.ben, { ben: true }), 8, kalkan("sv", v.ben.seviye)));
        }
        kursu.append(podyum, levha);
      })
      .catch(function () {});
  }
  kursuYukle();
  setInterval(kursuYukle, 60000);

  // --- Haftalık turnuva: ilk 10 hafta bitince ödül alır.
  var hafta = document.getElementById("hafta");
  var haftaBilgi = document.getElementById("hafta-bilgi");
  var reyting = document.getElementById("reyting");
  var haftaSonu = null;
  function haftaYukle() {
    fetch("/dunya/hafta", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        hafta.textContent = "";
        v.ilk.forEach(function (o, i) {
          var puan = el("span", "puan yazi-altin");
          say(puan, Math.round(o.puan), 1000 + i * 80);
          hafta.appendChild(levhaSatiri(o, i, puan));
        });
        reyting.innerHTML = "Reyting <b>" + SAYI.format(v.reyting) + "</b>";
        var bitis = new Date(v.hafta + "T00:00:00+03:00");
        bitis.setDate(bitis.getDate() + 7);
        haftaSonu = bitis;
        haftaBilgi.textContent = (v.ben ? "Bu hafta " + v.ben.sira + ". sıradasın. " : "") +
          "Hafta " + bitis.toLocaleDateString("tr-TR", { day: "numeric", month: "long", timeZone: "Europe/Istanbul" }) +
          " 00.00'da kapanır; ilk 10 ödül alır.";
      })
      .catch(function () {});
  }

  // Dönen rakamlar (SplitFlap): değişen her rakam ikiye bölünüp döner.
  var geriSayim = document.getElementById("geri-sayim");
  var flaplar = {};
  function flapKur(birim, etiket) {
    var kutu = el("div", "birim");
    var dizi = el("div", "flaplar");
    flaplar[birim] = [0, 1].map(function () {
      var f = el("span", "flap");
      f.innerHTML = "<span class='u'><i>0</i></span><span class='a'><i>0</i></span>";
      f.dataset.deger = "0";
      dizi.appendChild(f);
      return f;
    });
    kutu.append(dizi, el("small", "", etiket));
    geriSayim.appendChild(kutu);
  }
  [["g", "gün"], ["s", "saat"], ["d", "dk"], ["n", "sn"]].forEach(function (b) { flapKur(b[0], b[1]); });
  function flapYaz(f, yeni) {
    var eski = f.dataset.deger;
    if (eski === yeni) return;
    f.dataset.deger = yeni;
    if (HAREKETSIZ) { f.innerHTML = "<span class='u'><i>" + yeni + "</i></span><span class='a'><i>" + yeni + "</i></span>"; return; }
    f.innerHTML = "<span class='u'><i>" + yeni + "</i></span><span class='a'><i>" + eski + "</i></span>" +
      "<span class='ku'><i>" + eski + "</i></span><span class='ka'><i>" + yeni + "</i></span>";
    setTimeout(function () {
      if (f.dataset.deger === yeni) f.innerHTML = "<span class='u'><i>" + yeni + "</i></span><span class='a'><i>" + yeni + "</i></span>";
    }, 600);
  }
  function sayac() {
    if (!haftaSonu) return;
    var kalan = Math.max(0, Math.floor((haftaSonu - Date.now()) / 1000));
    var degerler = { g: Math.floor(kalan / 86400), s: Math.floor(kalan % 86400 / 3600), d: Math.floor(kalan % 3600 / 60), n: kalan % 60 };
    Object.keys(degerler).forEach(function (b) {
      var metin = String(Math.min(99, degerler[b])).padStart(2, "0");
      flapYaz(flaplar[b][0], metin[0]);
      flapYaz(flaplar[b][1], metin[1]);
    });
  }
  haftaYukle();
  setInterval(haftaYukle, 60000);
  setInterval(sayac, 1000);

  // --- Etkinlik takvimi
  var etkinlik = document.getElementById("etkinlik");
  fetch("/dunya/takvim", { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (v) {
      var tarih = function (s) { return new Date(s + "T12:00:00+03:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", timeZone: "Europe/Istanbul" }); };
      var aktif = v.etkinlikler.filter(function (e) { return e.aktif; });
      var yakin = v.etkinlikler.filter(function (e) { return !e.aktif; })[0];
      var olay = function (e, icerik) {
        var resim = e.resim ? "<img class='simge' src='" + e.resim + "' alt=''>" : "";
        return "<div class='olay'>" + resim + icerik + "</div>";
      };
      var parcalar = aktif.map(function (e) {
        return olay(e, "<b class='yazi-oyun'>" + e.ad + "</b>" + e.setler.join(", ") +
          " setleri mağazada.<small>" + tarih(e.son_gun) + " gün sonuna dek</small>");
      });
      if (yakin) parcalar.push(olay(yakin, "Sıradaki şenlik: " + yakin.ad + "<small>" + tarih(yakin.baslangic) + "</small>"));
      if (parcalar.length) etkinlik.innerHTML = parcalar.join("");
      else etkinlik.remove();
    })
    .catch(function () { etkinlik.remove(); });

  // --- Kayıt yedeği: başka bilgisayardan alınan yedeği yükle
  document.getElementById("yedek-dosyasi").addEventListener("change", function (e) {
    var dosya = e.target.files[0];
    if (!dosya) return;
    if (!confirm("Yedek yüklenecek ve şimdiki kayıt .bak dosyasına alınacak. Sürdürülsün mü?")) return;
    var form = new FormData();
    form.append("dosya", dosya);
    fetch("/kayit/yukle", { method: "POST", body: form })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        if (v.durum === "ok") location.reload();
        else alert(v.hata || "Yedek yüklenemedi.");
      })
      .catch(function () { alert("Yedek yüklenemedi."); });
  });
})();
