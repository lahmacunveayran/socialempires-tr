// Emülatördeki gerçek WebView'u sürer: yeni imparatorluk, "Krallığa Gir", Ruffle oyunu yükler mi?
// sinama.sh uygulamayı "sinama" bayrağıyla açar (WebView hata ayıklaması); Playwright'ın Android arayüzü adb
// üzerinden uygulamanın WebView'una bağlanır (genel CDP bağlantısı WebView'da çalışmıyor).
//
// Kullanım: node android/sinama_oyun.js <paket> [ekran.png]
// Çıkış kodu 0: oyun yüklendi (Ruffle "loadeddata", yükleme perdesi kalktı), oyun sunucuya açılışının bittiğini
// bildirdi ("track_game_status: 129b-init"), sayfa hatası yok. Ekran görüntüsü en sonda ve sonucu etkilemez:
// emülatörün grafik katmanı ekran görüntüsü sırasında ara sıra çöküyor.

const { _android: android } = require("playwright-core");

const PAKET = process.argv[2];
const EKRAN = process.argv[3] || "oyun.png";
const ADRES = "http://127.0.0.1:5050";
const sinirli = (soz, ms) => Promise.race([soz, new Promise((_, ret) => setTimeout(() => ret(new Error("süre doldu")), ms))]);
const sure = () => `${((Date.now() - BASLANGIC) / 1000).toFixed(1)} sn`;
const BASLANGIC = Date.now();
const hatalar = [];
const konsol = [];
function konsoluYaz() {
  console.log("--- konsol (son 25) ---");
  konsol.slice(-25).forEach((k) => console.log(k));
  if (hatalar.length) console.log(`--- sayfa hataları ---\n${hatalar.join("\n")}`);
}

(async () => {
  const [cihaz] = await android.devices({ omitDriverInstall: true });
  if (!cihaz) throw new Error("adb cihazı bulunamadı");
  console.log(`Cihaz: ${cihaz.model()} (${cihaz.serial()})`);
  const webview = await cihaz.webView({ pkg: PAKET }, { timeout: 60000 });
  const sayfa = await webview.page();
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
  if (!durum.swf) throw new Error("Ruffle SWF bilgisini vermedi");

  // Oyunun kendisi sunucuya aşamalarını bildirir (oyun/istemci.py track_game_status)
  let asamalar = [];
  for (let i = 0; i < 60; i++) {
    const kayit = (await cihaz.shell("logcat -d -s python.stdout:V")).toString();
    asamalar = [...new Set(kayit.match(/track_game_status: \S+/g) || [])];
    if (asamalar.some((a) => a.endsWith("129b-init"))) break;
    await sayfa.waitForTimeout(2000);
  }
  console.log(`--- oyunun bildirdiği aşamalar ---\n${asamalar.join("\n")}`);
  konsoluYaz();
  if (!asamalar.some((a) => a.endsWith("129b-init"))) throw new Error("Oyun açılışını bitirmedi (129b-init yok)");
  if (hatalar.length) throw new Error(`${hatalar.length} sayfa hatası`);
  console.log(`[${sure()}] Tamam: oyun Android WebView'da yüklendi ve açılışını bitirdi.`);

  await sinirli(sayfa.screenshot({ path: EKRAN }), 30000)
    .catch((h) => console.log(`(ekran görüntüsü alınamadı: ${h.message})`));
  await sinirli(cihaz.close(), 10000).catch(() => {});
  process.exit(0);
})().catch((h) => { konsoluYaz(); console.error(`HATA: ${h.message}`); process.exit(1); });
