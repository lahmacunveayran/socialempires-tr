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
    return t.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
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
        if (v.son < sonId) sonId = 0; // sunucu yeniden başladı
        else sonId = v.son;
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
})();
