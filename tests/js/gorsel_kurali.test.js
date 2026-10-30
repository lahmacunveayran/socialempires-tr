// Görsel kuralı (CLAUDE.md): sayfada elle çizilmiş süs yok, yalnızca oyunun kendi resimleri.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const KOK = path.join(__dirname, "..", "..");
const css = fs.readFileSync(path.join(KOK, "templates", "css", "oyun.css"), "utf8");
const OYUN_STATIK = "/default01.static.socialpointgames.com/static/socialempires/";

test("CSS yalnızca oyunun resimlerini kullanır", () => {
  const adresler = [...css.matchAll(/url\("([^"]+)"\)/g)].map((m) => m[1]);
  assert.ok(adresler.length > 10);
  for (const adres of adresler) {
    assert.ok(adres.startsWith("/img/") || adres.startsWith(OYUN_STATIK) || adres.startsWith("/fonts/"), adres);
  }
});

test("templates/img/oyun resimleri depoda", () => {
  for (const [, ad] of css.matchAll(/url\("\/img\/oyun\/([^"]+)"\)/g)) {
    assert.ok(fs.existsSync(path.join(KOK, "templates", "img", "oyun", ad)), ad);
  }
});

test("degradeyle çizilmiş süs yok", () => {
  assert.doesNotMatch(css, /conic-gradient|radial-gradient|repeating-linear-gradient/);
  // linear-gradient yalnızca yazı boyası (background-clip: text) ve kaydırma maskesi için
  for (const satir of css.split("\n").filter((s) => s.includes("linear-gradient"))) {
    assert.ok(/background-clip: text|mask/.test(satir), satir.trim());
  }
});
