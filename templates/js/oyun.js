// Oyun sayfası: çerçeve ölçeği, "Krallığa Gir" düğmesi, yükleme ekranı,
// Diyar Haberleri şeridi ve Şeref Kürsüsü.
(function () {
  "use strict";
  var AYAR = window.OYUN_AYARI;
  var GEN = 760, YUK = 600, EN_BUYUK_OLCEK = 1.5;

  // --- Çerçeve ölçeği: oyun EXACT_FIT ile kutuya esner, oran tam 760:600 kalmalı.
  var kutu = document.getElementById("oyun-kutusu");
  var alan = document.querySelector(".oyun-alani");
  function olcekle() {
    var stil = getComputedStyle(document.documentElement);
    var baslik = parseFloat(stil.getPropertyValue("--baslik-yuksekligi")) || 0;
    var bosluk = parseFloat(stil.getPropertyValue("--bosluk")) || 0;
    var cerceve = 20;
    var genislik = alan.clientWidth - cerceve;
    var yukseklik = window.innerHeight - baslik - 2 * bosluk - cerceve;
    var s = Math.min(genislik / GEN, yukseklik / YUK, EN_BUYUK_OLCEK);
    // Çok dar yükseklikte (telefon yatay) genişliğe göre ölçeklenir, sayfa kayar.
    if (s < 0.45) s = Math.min(genislik / GEN, EN_BUYUK_OLCEK);
    kutu.style.width = Math.floor(GEN * s) + "px";
    kutu.style.height = Math.round(Math.floor(GEN * s) * YUK / GEN) + "px";
  }
  window.addEventListener("resize", olcekle);
  olcekle();

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
  });

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
  function satirEkle(olay, yeni) {
    var bos = liste.querySelector(".bos");
    if (bos) bos.remove();
    var li = document.createElement("li");
    li.dataset.tur = olay.tur;
    if (yeni) li.className = "yeni";
    li.textContent = olay.metin;
    var zaman = document.createElement("time");
    zaman.dateTime = new Date(olay.zaman * 1000).toISOString();
    zaman.textContent = saat(olay.zaman);
    li.appendChild(zaman);
    liste.insertBefore(li, liste.firstChild);
    while (liste.children.length > EN_COK_SATIR) liste.removeChild(liste.lastChild);
    ozet.textContent = "Son haber: " + olay.metin;
  }
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

  // --- Şeref Kürsüsü: dakikada bir.
  var kursu = document.getElementById("kursu");
  var kursuBen = document.getElementById("kursu-ben");
  function kursuYukle() {
    fetch("/dunya/kursu", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        kursu.textContent = "";
        v.ilk.forEach(function (o) {
          var li = document.createElement("li");
          if (o.ben) li.className = "ben";
          var no = document.createElement("span"); no.className = "no"; no.textContent = o.sira;
          var ad = document.createElement("span"); ad.className = "ad"; ad.textContent = o.ad;
          var rutbe = document.createElement("small"); rutbe.textContent = o.rutbe; ad.appendChild(rutbe);
          var sv = document.createElement("span"); sv.className = "sv"; sv.textContent = "sv. " + o.seviye;
          li.append(no, ad, sv);
          kursu.appendChild(li);
        });
        kursuBen.textContent = v.ben && !v.ilk.some(function (o) { return o.ben; })
          ? "Sen " + v.toplam + " imparatorluk içinde " + v.ben.sira + ". sıradasın (" + v.ben.rutbe + ")."
          : "";
      })
      .catch(function () {});
  }
  kursuYukle();
  setInterval(kursuYukle, 60000);

  // --- Haftalık turnuva: ilk 10 hafta bitince ödül alır.
  var hafta = document.getElementById("hafta");
  var haftaBilgi = document.getElementById("hafta-bilgi");
  function haftaYukle() {
    fetch("/dunya/hafta", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        hafta.textContent = "";
        v.ilk.forEach(function (o) {
          var li = document.createElement("li");
          if (o.ben) li.className = "ben";
          var no = document.createElement("span"); no.className = "no"; no.textContent = o.sira;
          var ad = document.createElement("span"); ad.className = "ad"; ad.textContent = o.ad;
          var puan = document.createElement("span"); puan.className = "sv"; puan.textContent = Math.round(o.puan) + " p";
          li.append(no, ad, puan);
          hafta.appendChild(li);
        });
        var bitis = new Date(v.hafta + "T00:00:00+03:00");
        bitis.setDate(bitis.getDate() + 7);
        haftaBilgi.textContent = "Reytingin: " + v.reyting + (v.ben ? " · Bu hafta " + v.ben.sira + ". sıradasın" : "") +
          " · Hafta " + bitis.toLocaleDateString("tr-TR", { day: "numeric", month: "long", timeZone: "Europe/Istanbul" }) + " 00.00'da kapanır; ilk 10 ödül alır.";
      })
      .catch(function () {});
  }
  haftaYukle();
  setInterval(haftaYukle, 60000);

  // --- Etkinlik takvimi
  var etkinlik = document.getElementById("etkinlik");
  fetch("/dunya/takvim", { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (v) {
      var tarih = function (s) { return new Date(s + "T12:00:00+03:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", timeZone: "Europe/Istanbul" }); };
      var aktif = v.etkinlikler.filter(function (e) { return e.aktif; });
      var yakin = v.etkinlikler.filter(function (e) { return !e.aktif; })[0];
      var parcalar = aktif.map(function (e) {
        return "<b>" + e.ad + "</b> sürüyor: " + e.setler.join(", ") + " setleri mağazada (" + tarih(e.son_gun) + " sonuna dek).";
      });
      if (yakin) parcalar.push("Sıradaki: <b>" + yakin.ad + "</b>, " + tarih(yakin.baslangic) + ".");
      if (parcalar.length) { etkinlik.innerHTML = parcalar.join("<br>"); etkinlik.hidden = false; }
    })
    .catch(function () {});

  // --- Ücretsiz Hediyeler: 7 günlük sandık
  var pencere = document.getElementById("hediye-penceresi");
  var gunler = document.getElementById("hediye-gunleri");
  var ileti = document.getElementById("hediye-ileti");
  var alDugmesi = document.getElementById("hediye-al");
  function hediyeGoster() {
    return fetch("/hediye", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (v) {
        gunler.textContent = "";
        v.oduller.forEach(function (o, i) {
          var li = document.createElement("li");
          if (i < v.sira || (!v.alinabilir && i === v.sira)) li.className = "alindi";
          if (v.alinabilir && i === v.sira) li.className = "bugun";
          var b = document.createElement("b"); b.textContent = o.gun + ". gün";
          li.append(b, document.createTextNode(o.adet + " × " + o.ad));
          gunler.appendChild(li);
        });
        alDugmesi.disabled = !v.alinabilir;
        if (!v.alinabilir) ileti.textContent = "Bugünün hediyesini aldın. Yarın yine gel!";
      });
  }
  document.getElementById("hediye-ac").addEventListener("click", function () {
    ileti.textContent = "";
    hediyeGoster().then(function () { pencere.showModal(); }).catch(function () {});
  });
  document.getElementById("hediye-kapat").addEventListener("click", function () { pencere.close(); });
  alDugmesi.addEventListener("click", function () {
    fetch("/hediye/al", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (v) { hediyeGoster(); ileti.textContent = v.ileti || v.hata; })
      .catch(function () {});
  });

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
