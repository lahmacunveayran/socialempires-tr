// Emülatördeki gerçek WebView'u sürer: yeni imparatorluk, "Krallığa Gir", Ruffle oyunu yükler mi?
// sinama.sh, uygulamayı "sinama" bayrağıyla açar (WebView hata ayıklaması) ve DevTools soketini 9222'ye yönlendirir.
//
// Kullanım: node android/sinama_oyun.js [cdp-adresi] [ekran.png]
// Çıkış kodu 0: oyun yüklendi (Ruffle "loadeddata", yükleme perdesi kalktı), sayfa hatası yok.

const { chromium } = require("playwright-core");

const CDP = process.argv[2] || "http://127.0.0.1:9222";
const EKRAN = process.argv[3] || "oyun.png";
const ADRES = "http://127.0.0.1:5050";
const sure = () => `${((Date.now() - BASLANGIC) / 1000).toFixed(1)} sn`;
const BASLANGIC = Date.now();

(async () => {
  const tarayici = await chromium.connectOverCDP(CDP, { timeout: 60000 });
  const baglam = tarayici.contexts()[0];
  const sayfa = baglam.pages()[0] || (await baglam.newPage());
  const hatalar = [];
  const konsol = [];
  sayfa.on("pageerror", (h) => hatalar.push(h.message));
  sayfa.on("console", (m) => konsol.push(`${m.type()}: ${m.text()}`.slice(0, 300)));

  console.log(`WebView: ${await sayfa.evaluate(() => navigator.userAgent)}`);
  await sayfa.goto(`${ADRES}/new.html`, { timeout: 120000 });
  await sayfa.waitForSelector("#kralliga-gir", { timeout: 60000 });
  console.log(`[${sure()}] Oyun sayfası açık: ${sayfa.url()}`);

  await sayfa.click("#kralliga-gir", { force: true }); // düğme nabız gibi atıyor
  await sayfa.waitForSelector("ruffle-player", { state: "attached", timeout: 60000 });
  console.log(`[${sure()}] Ruffle oluşturuldu`);
  // İlk açılışta oyun varlıkları (~60 MB) GitHub'dan iner
  await sayfa.waitForSelector("#yukleme[hidden]", { state: "attached", timeout: 420000 });
  console.log(`[${sure()}] Oyun yüklendi (yükleme perdesi kalktı)`);
  await sayfa.waitForTimeout(20000);

  const durum = await sayfa.evaluate(() => {
    const oyuncu = document.querySelector("ruffle-player");
    const meta = oyuncu && oyuncu.metadata;
    return {
      swf: meta ? `${meta.width}×${meta.height}, SWF ${meta.swfVersion}` : null,
      cerceve: (() => { const k = document.getElementById("oyun-kutusu").getBoundingClientRect();
        return `${Math.round(k.width)}×${Math.round(k.height)}`; })(),
      pencere: `${innerWidth}×${innerHeight}`,
    };
  });
  console.log(`[${sure()}] ${JSON.stringify(durum)}`);
  await sayfa.screenshot({ path: EKRAN }).catch((h) => console.log(`ekran görüntüsü alınamadı: ${h.message}`));

  console.log("--- konsol (son 25) ---");
  konsol.slice(-25).forEach((s) => console.log(s));
  if (hatalar.length) console.log(`--- sayfa hataları ---\n${hatalar.join("\n")}`);
  await tarayici.close().catch(() => {});
  if (!durum.swf) throw new Error("Ruffle SWF bilgisini vermedi");
  if (hatalar.length) throw new Error(`${hatalar.length} sayfa hatası`);
  console.log("Tamam: oyun Android WebView'da yüklendi.");
})().catch((h) => { console.error(`HATA: ${h.message}`); process.exit(1); });
