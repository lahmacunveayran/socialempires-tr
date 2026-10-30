// Gökyüzü modülü: Güneş yüksekliği (NOAA denklemleri) ve evreler.
// Çalıştırma: node --test tests/js
const { test } = require("node:test");
const assert = require("node:assert/strict");
require("../../templates/js/gokyuzu.js");

const G = globalThis.Gokyuzu;
const RESMI = -0.833; // resmî doğuş/batış: kırılma ve Güneş'in yarıçapı

// İstanbul'da (UTC+3) Güneş'in resmî ufku geçtiği dakika, "SS:DD".
function gecis(gun, sabah) {
  let onceki = null;
  for (let dk = 0; dk < 1440; dk++) {
    const t = new Date(Date.parse(`${gun}T00:00:00+03:00`) + dk * 60000);
    const h = G.gunesYuksekligi(t);
    if (onceki !== null && (sabah ? onceki < RESMI && h >= RESMI : onceki >= RESMI && h < RESMI)) {
      const yerel = new Date(t.getTime() + 3 * 3600000);
      return yerel.toISOString().slice(11, 16);
    }
    onceki = h;
  }
  return null;
}

function dakika(ss) {
  const [s, d] = ss.split(":").map(Number);
  return s * 60 + d;
}

// Yol haritasındaki denetim hesabı (bağımsız sitelerdeki değerler).
for (const [gun, dogus, batis] of [["2026-06-21", "05:32", "20:40"], ["2026-12-21", "08:25", "17:39"]]) {
  test(`İstanbul ${gun}: doğuş ${dogus}, batış ${batis} (±2 dk)`, () => {
    assert.ok(Math.abs(dakika(gecis(gun, true)) - dakika(dogus)) <= 2, gecis(gun, true));
    assert.ok(Math.abs(dakika(gecis(gun, false)) - dakika(batis)) <= 2, gecis(gun, false));
  });
}

test("evreler Güneş yüksekliğine göre", () => {
  assert.equal(G.evre(30), "gunduz");
  assert.equal(G.evre(3), "altin-saat");
  assert.equal(G.evre(-2), "kizillik");
  assert.equal(G.evre(-6), "mavi-saat");
  assert.equal(G.evre(-12), "alacakaranlik");
  assert.equal(G.evre(-40), "gece");
});

test("renkler OKLab'de karıştırılır", () => {
  assert.match(G.renkler(-2).ust, /^color-mix\(in oklab,/);
  assert.equal(G.renkler(45).ust, G.renkler(30).ust); // en üst durakta sabit
});

test("öğle güneşi yüksek, gece yarısı ufkun altında", () => {
  assert.ok(G.gunesYuksekligi(new Date("2026-06-21T13:00:00+03:00")) > 70);
  assert.ok(G.gunesYuksekligi(new Date("2026-06-21T01:00:00+03:00")) < -15);
});
