// Faz 1 kabul kapısı: oyun sayfasının 1920x1080, 1366x768 ve 390x844
// ekranlardaki görüntüleri, çerçeve oranı (760:600 = 1,2667) ve saati ileri
// alarak çekilen üç gökyüzü (öğlen, gün batımı, gece).
//
// Kullanım (sunucu açıkken): node araclar/sayfa_goruntuleri.js <USERID> [klasor]
// "--oyna" eklenirse 1920x1080'de "Krallığa Gir"e basılıp oyunun açıldığı da
// sınanır.

const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const ADRES = "http://127.0.0.1:5050";
const [uid, cikti = "sayfa_goruntuleri"] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const oyna = process.argv.includes("--oyna");
if (!uid) {
  console.error("Kullanim: node araclar/sayfa_goruntuleri.js <USERID> [klasor] [--oyna]");
  process.exit(2);
}
fs.mkdirSync(cikti, { recursive: true });
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

const EKRANLAR = [
  { ad: "1920x1080", width: 1920, height: 1080 },
  { ad: "1366x768", width: 1366, height: 768 },
  { ad: "390x844", width: 390, height: 844, isMobile: true, hasTouch: true },
];
// İstanbul, 21 Haziran 2026 (UTC+3)
const SAATLER = { oglen: "2026-06-21T13:00:00+03:00", gun_batimi: "2026-06-21T20:45:00+03:00",
                  gece: "2026-06-21T23:30:00+03:00" };

async function giris(baglam) {
  await baglam.request.post(`${ADRES}/`, {
    form: { USERID: uid, GAMEVERSION: "SocialEmpires1.4.07sec_fixed.swf" }, maxRedirects: 0,
  });
}

(async () => {
  const tarayici = await chromium.launch({
    args: ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle",
           "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  });
  const sonuc = { oranlar: {}, evreler: {} };
  for (const e of EKRANLAR) {
    const baglam = await tarayici.newContext({ viewport: { width: e.width, height: e.height },
      isMobile: !!e.isMobile, hasTouch: !!e.hasTouch, deviceScaleFactor: 1 });
    await giris(baglam);
    const sayfa = await baglam.newPage();
    await sayfa.goto(`${ADRES}/play.html?saat=${encodeURIComponent(SAATLER.gun_batimi)}`);
    await bekle(1500);
    const kutu = await sayfa.locator("#oyun-kutusu").boundingBox();
    const yatayKaydirma = await sayfa.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    sonuc.oranlar[e.ad] = { genislik: kutu.width, yukseklik: kutu.height,
      oran: +(kutu.width / kutu.height).toFixed(4), yatayKaydirma };
    await sayfa.screenshot({ path: path.join(cikti, `ekran_${e.ad}.png`) });
    await baglam.close();
  }

  const baglam = await tarayici.newContext({ viewport: { width: 1366, height: 768 } });
  await giris(baglam);
  const sayfa = await baglam.newPage();
  for (const [ad, saat] of Object.entries(SAATLER)) {
    await sayfa.goto(`${ADRES}/play.html?saat=${encodeURIComponent(saat)}`);
    await bekle(800);
    sonuc.evreler[ad] = await sayfa.evaluate(() => document.documentElement.dataset.evre);
    await sayfa.screenshot({ path: path.join(cikti, `gok_${ad}.png`) });
  }

  if (oyna) {
    const gunluk = [];
    sayfa.on("console", (m) => gunluk.push(m.text()));
    await sayfa.setViewportSize({ width: 1920, height: 1080 });
    await sayfa.goto(`${ADRES}/play.html`);
    await sayfa.click("#kralliga-gir", { force: true }); // düğme nabız gibi atıyor
    await sayfa.waitForSelector("#yukleme[hidden]", { state: "attached", timeout: 120000 });
    await bekle(20000);
    await sayfa.locator("#oyun-kutusu").screenshot({ path: path.join(cikti, "oyun_1920.png") });
    sonuc.oyun = { ruffleSurumu: (gunluk.find((s) => s.includes("Version:")) || "").replace(/%c/g, "").slice(0, 120) };
  }
  fs.writeFileSync(path.join(cikti, "sonuc.json"), JSON.stringify(sonuc, null, 2));
  console.log(JSON.stringify(sonuc, null, 2));
  await tarayici.close();
})().catch((h) => { console.error(h); process.exit(1); });
