// Telefon, tablet ve dizüstü ekranlarında oyun sayfasını ölçer (DAG-04, HIZ-03).
//
// Her cihaz için: oyun çerçevesinin boyutu ve oranı (hedef 760:600 = 1,2667), çerçevenin ekrana sığıp sığmadığı,
// başlığın taşıp taşmadığı, yatay kaydırma. "--dokun" verilirse telefon ve tablette "Krallığa Gir"e dokunup
// Ruffle'ın açıldığını da sınar. Masaüstü yükseklikleri tarayıcı çubukları düşülmüş iç yüksekliktir.
//
// Not: Playwright cihaz tanımları Chromium ile benzetimdir (ekran, dokunma, kullanıcı aracısı); gerçek iOS Safari
// değildir. Gerçek cihaz denemesi sahibinindir (docs/gorev/20-BOLUM-II.md §7.1).
//
// Kullanım (sunucu açıkken): node araclar/cihaz_denemesi.js <USERID> [klasor] [--dokun]

const { chromium, devices } = require("playwright");
const fs = require("fs");
const path = require("path");

const ADRES = "http://127.0.0.1:5050";
const [uid, cikti = "cihaz_denemesi"] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const dokun = process.argv.includes("--dokun");
if (!uid) {
  console.error("Kullanim: node araclar/cihaz_denemesi.js <USERID> [klasor] [--dokun]");
  process.exit(2);
}
fs.mkdirSync(cikti, { recursive: true });

const CIHAZLAR = [
  ["Dizüstü 1366×768", { viewport: { width: 1366, height: 657 } }],
  ["Dizüstü 1536×864", { viewport: { width: 1536, height: 744 } }],
  ["Masaüstü 1920×1080", { viewport: { width: 1920, height: 969 } }],
  ["iPhone 13", devices["iPhone 13"]],
  ["iPhone 13 yatay", devices["iPhone 13 landscape"]],
  ["Pixel 7", devices["Pixel 7"]],
  ["Pixel 7 yatay", devices["Pixel 7 landscape"]],
  ["iPad dik", devices["iPad (gen 7)"]],
  ["iPad yatay", devices["iPad (gen 7) landscape"]],
];

(async () => {
  const tarayici = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
  const sonuc = [];
  for (const [ad, ayar] of CIHAZLAR) {
    const { defaultBrowserType, ...baglamAyari } = ayar; // eslint-disable-line no-unused-vars
    const baglam = await tarayici.newContext(baglamAyari);
    await baglam.request.post(`${ADRES}/`, {
      form: { USERID: uid, GAMEVERSION: "SocialEmpires0926bsec.swf" }, maxRedirects: 0,
    });
    const sayfa = await baglam.newPage();
    const hatalar = [];
    sayfa.on("pageerror", (h) => hatalar.push(h.message));
    await sayfa.goto(`${ADRES}/play.html`);
    await sayfa.waitForTimeout(1500);
    const olcu = await sayfa.evaluate(() => {
      const k = document.getElementById("oyun-kutusu").getBoundingClientRect();
      const b = document.querySelector(".baslik").getBoundingClientRect();
      const o = document.querySelector(".oturum").getBoundingClientRect();
      return {
        cerceve: `${Math.round(k.width)}×${Math.round(k.height)}`,
        oran: +(k.width / k.height).toFixed(4),
        sigiyor: k.bottom <= innerHeight + 1,
        baslikTasmaz: o.bottom <= b.bottom + 1 && o.top >= b.top - 1,
        yatayKaydirma: document.documentElement.scrollWidth > innerWidth,
        pencere: `${innerWidth}×${innerHeight}`,
      };
    });
    if (dokun && ayar.hasTouch) {
      await sayfa.tap("#kralliga-gir", { force: true });
      await sayfa.waitForSelector("ruffle-player", { timeout: 60000 });
      await sayfa.waitForSelector("#yukleme[hidden]", { state: "attached", timeout: 120000 });
      olcu.ruffle = await sayfa.evaluate(() => !!document.querySelector("ruffle-player"));
    }
    olcu.hata = hatalar.length;
    await sayfa.screenshot({ path: path.join(cikti, `${ad.replace(/[^\w]+/g, "_")}.png`) });
    sonuc.push({ cihaz: ad, ...olcu });
    await baglam.close();
  }
  await tarayici.close();
  console.table(sonuc);
  fs.writeFileSync(path.join(cikti, "sonuc.json"), JSON.stringify(sonuc, null, 2));
})().catch((h) => { console.error(h); process.exit(1); });
