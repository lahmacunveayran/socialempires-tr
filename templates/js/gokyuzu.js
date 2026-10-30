// Gökyüzü: saate göre değil, Güneş'in ufkun kaç derece üstünde ya da altında
// olduğuna (h) göre boyanır. Böylece haziran akşamı ile aralık akşamı
// kendiliğinden farklı görünür. Hesap NOAA'nın Güneş konumu denklemleriyle
// (SunCalc ile aynı yaklaşım, yaklaşık 0,1° hata) yapılır.
(function (kok) {
  "use strict";
  var RAD = Math.PI / 180;
  var ISTANBUL = { enlem: 41.0082, boylam: 28.9784 };

  // Julian günü -> Güneş'in sapması (delta) ve zaman denklemi (dakika).
  function gunesVerisi(tarih) {
    var jd = tarih.getTime() / 86400000 + 2440587.5;
    var t = (jd - 2451545.0) / 36525;
    var l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360;
    var m = 357.52911 + t * (35999.05029 - 0.0001537 * t);
    var e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
    var c = Math.sin(m * RAD) * (1.914602 - t * (0.004817 + 0.000014 * t)) +
            Math.sin(2 * m * RAD) * (0.019993 - 0.000101 * t) +
            Math.sin(3 * m * RAD) * 0.000289;
    var gercekBoylam = l0 + c;
    var omega = 125.04 - 1934.136 * t;
    var lambda = gercekBoylam - 0.00569 - 0.00478 * Math.sin(omega * RAD);
    var eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
    var eps = eps0 + 0.00256 * Math.cos(omega * RAD);
    var delta = Math.asin(Math.sin(eps * RAD) * Math.sin(lambda * RAD));
    var y = Math.pow(Math.tan(eps * RAD / 2), 2);
    var zaman = 4 / RAD * (y * Math.sin(2 * l0 * RAD) - 2 * e * Math.sin(m * RAD) +
      4 * e * y * Math.sin(m * RAD) * Math.cos(2 * l0 * RAD) -
      0.5 * y * y * Math.sin(4 * l0 * RAD) - 1.25 * e * e * Math.sin(2 * m * RAD));
    return { delta: delta, zamanDenklemi: zaman };
  }

  // cos(phi) = sin(enlem) sin(delta) + cos(enlem) cos(delta) cos(saat açısı); h = 90 - phi
  function gunesYuksekligi(tarih, konum) {
    return gunesKonumu(tarih, konum).h;
  }

  // Yükseklik (h, derece) ve saat açısı (derece; 0 = öğle, -90 sabah, +90 akşam).
  function gunesKonumu(tarih, konum) {
    konum = konum || ISTANBUL;
    var g = gunesVerisi(tarih);
    var utcDakika = tarih.getUTCHours() * 60 + tarih.getUTCMinutes() + tarih.getUTCSeconds() / 60;
    var gercekGunesZamani = utcDakika + g.zamanDenklemi + 4 * konum.boylam;
    var saatAcisi = (gercekGunesZamani / 4 - 180) * RAD;
    var enlem = konum.enlem * RAD;
    var cosPhi = Math.sin(enlem) * Math.sin(g.delta) + Math.cos(enlem) * Math.cos(g.delta) * Math.cos(saatAcisi);
    var aci = ((saatAcisi / RAD) % 360 + 540) % 360 - 180;
    return { h: 90 - Math.acos(Math.max(-1, Math.min(1, cosPhi))) / RAD, saatAcisi: aci };
  }

  // Evreler: −0,833° resmi doğuş/batış; −4, −8 ve −18 alacakaranlık eşikleri.
  var EVRELER = [
    { ad: "gunduz", alt: 6 },
    { ad: "altin-saat", alt: -0.833 },
    { ad: "kizillik", alt: -4 },
    { ad: "mavi-saat", alt: -8 },
    { ad: "alacakaranlik", alt: -18 },
    { ad: "gece", alt: -Infinity },
  ];

  function evre(h) {
    for (var i = 0; i < EVRELER.length; i++) if (h > EVRELER[i].alt) return EVRELER[i].ad;
    return "gece";
  }

  // Yükseklik -> gök renkleri (üst, ufuk). Aradaki değerler OKLab'de
  // karıştırılır: sRGB'de maviden turuncuya geçerken çıkan bulanık
  // gri-kahverengi OKLab'de çıkmaz.
  var DURAKLAR = [
    { h: 20, ust: "#2f7fd6", ufuk: "#b9e0ff" },
    { h: 6, ust: "#4a88cf", ufuk: "#ffe2a8" },
    { h: -0.833, ust: "#5c6fb5", ufuk: "#ffb36b" },
    { h: -4, ust: "#3d3f86", ufuk: "#f0745a" },
    { h: -8, ust: "#1d2660", ufuk: "#5d6db0" },
    { h: -18, ust: "#070b22", ufuk: "#141c45" },
  ];

  function renkler(h) {
    if (h >= DURAKLAR[0].h) return { ust: DURAKLAR[0].ust, ufuk: DURAKLAR[0].ufuk };
    for (var i = 1; i < DURAKLAR.length; i++) {
      var a = DURAKLAR[i - 1], b = DURAKLAR[i];
      if (h >= b.h) {
        var p = Math.round((a.h - h) / (a.h - b.h) * 100);
        var karis = function (x, y) { return "color-mix(in oklab, " + x + " " + (100 - p) + "%, " + y + ")"; };
        return { ust: karis(a.ust, b.ust), ufuk: karis(a.ufuk, b.ufuk) };
      }
    }
    var son = DURAKLAR[DURAKLAR.length - 1];
    return { ust: son.ust, ufuk: son.ufuk };
  }

  // Gökteki yer (yüzde): saat açısı yatayda, yükseklik dikeyde. Ay kabaca
  // Güneş'in karşısında durur; gösterim içindir, gök mekaniği değildir.
  function gokYeri(saatAcisi, h) {
    return { x: Math.max(-10, Math.min(110, 50 + saatAcisi / 110 * 50)),
             // Oyun çerçevesi ortayı kapladığı için gök cisimleri üst şeritte gezer.
             y: Math.max(3, Math.min(18, 17 - h / 90 * 14)) };
  }

  function uygula(tarih) {
    var konum = gunesKonumu(tarih);
    var h = konum.h;
    var r = renkler(h);
    var stil = document.documentElement.style;
    var gunes = gokYeri(konum.saatAcisi, h);
    var ay = gokYeri(((konum.saatAcisi + 360) % 360) - 180, -h);
    stil.setProperty("--gunes-x", gunes.x + "%");
    stil.setProperty("--gunes-y", gunes.y + "%");
    stil.setProperty("--ay-x", ay.x + "%");
    stil.setProperty("--ay-y", ay.y + "%");
    stil.setProperty("--gunes-gorunur", String(Math.max(0, Math.min(1, (h + 3) / 4))));
    stil.setProperty("--ay-gorunur", String(Math.max(0, Math.min(1, (-h - 2) / 6))));
    // Bulutlar ve ışık: gündüz parlak, batımda turuncuya, gece koyu maviye çalar.
    stil.setProperty("--gun-isigi", String(Math.max(0.12, Math.min(1, (h + 10) / 18))));
    stil.setProperty("--gok-ust", r.ust);
    stil.setProperty("--gok-ufuk", r.ufuk);
    // Yıldızlar mavi saatte belirmeye başlar, gecede tam görünür.
    stil.setProperty("--yildiz", String(Math.max(0, Math.min(1, (-h - 6) / 10))));
    document.documentElement.dataset.evre = evre(h);
    return h;
  }

  // ?saat=2026-06-21T20:40 ile saat ileri alınabilir (ekran görüntüleri için).
  function simdi() {
    var m = /[?&]saat=([^&]+)/.exec(location.search);
    var t = m ? new Date(decodeURIComponent(m[1])) : null;
    return t && !isNaN(t) ? t : new Date();
  }

  kok.Gokyuzu = { gunesYuksekligi: gunesYuksekligi, gunesKonumu: gunesKonumu, evre: evre, renkler: renkler, uygula: uygula };

  if (typeof document !== "undefined") {
    uygula(simdi());
    // Gökyüzü dakikada bir güncellenir; sürekli animasyon gerekmez.
    if (!/[?&]saat=/.test(location.search)) setInterval(function () { uygula(new Date()); }, 60000);
  }
})(typeof window !== "undefined" ? window : globalThis);
