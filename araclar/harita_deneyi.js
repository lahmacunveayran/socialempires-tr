// Faz 0 harita tıklaması deneyi: eğitimi bitmiş bir kayıtla oyunu Ruffle'da
// açar, haritayı sürükler ve haritaya tıklar; her adımdan önce ve sonra ekran
// görüntüsü alır, Ruffle'ın konsol uyarılarını toplar. Sunucu dışındaki her
// istek engellenir: oyun açılıyorsa internetsiz de açılır.
//
// Kullanım (sunucu açıkken):
//   node araclar/harita_deneyi.js <USERID> [cikti_klasoru]
//
// Görüntüler karşılaştırılarak "harita kıpırdadı mı" sorusu yanıtlanır
// (araclar/goruntu_farki.py).

const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const ADRES = "http://127.0.0.1:5050";
const uid = process.argv[2];
const cikti = process.argv[3] || "harita_deneyi";
if (!uid) {
  console.error("Kullanim: node araclar/harita_deneyi.js <USERID> [cikti_klasoru]");
  process.exit(2);
}
fs.mkdirSync(cikti, { recursive: true });

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const tarayici = await chromium.launch({
    args: ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle",
           "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  });
  const baglam = await tarayici.newContext({ viewport: { width: 1000, height: 900 } });
  const sayfa = await baglam.newPage();
  const gunluk = [];
  sayfa.on("console", (m) => gunluk.push(`[${m.type()}] ${m.text()}`));
  sayfa.on("pageerror", (h) => gunluk.push(`[pageerror] ${h.message}`));
  let sonIstek = Date.now();
  sayfa.on("request", () => { sonIstek = Date.now(); });
  // İnternetsiz açılış denetimi: sunucu dışındaki her istek engellenir ve sayılır.
  const disIstekler = [];
  await sayfa.route("**/*", (r) => {
    const u = r.request().url();
    if (u.startsWith(ADRES)) return r.continue();
    disIstekler.push(u);
    return r.abort();
  });
  await sayfa.addInitScript(() => {
    window.RufflePlayer = window.RufflePlayer || {};
    window.RufflePlayer.config = { logLevel: "warn" };
  });

  await baglam.request.post(`${ADRES}/`, {
    form: { USERID: uid, GAMEVERSION: "SocialEmpires0926bsec.swf" },
    maxRedirects: 0,
  });
  await sayfa.goto(`${ADRES}/ruffle.html`);
  const oyuncu = sayfa.locator("ruffle-player");
  await oyuncu.waitFor({ timeout: 60000 });

  // Varlıklar ilk açılışta GitHub'dan iniyor: ağ 15 sn susana dek bekle.
  const baslangic = Date.now();
  while (Date.now() - sonIstek < 15000 && Date.now() - baslangic < 240000) await bekle(1000);
  await bekle(3000);

  const kutu = await oyuncu.boundingBox();
  const cek = (ad) => oyuncu.screenshot({ path: path.join(cikti, `${ad}.png`) });
  const nokta = (x, y) => [kutu.x + x, kutu.y + y];
  // Ruffle olayları kare başına işler: basma ve bırakma ayrı karelere düşsün.
  const tikla = async (x, y) => {
    await sayfa.mouse.move(...nokta(x, y), { steps: 5 });
    await bekle(100);
    await sayfa.mouse.down();
    await bekle(150);
    await sayfa.mouse.up();
  };

  await cek("0_acilis");
  // Ruffle'da ilk tıklama yalnızca odağı alır, oyuna ulaşmaz.
  await tikla(700, 590);
  await bekle(1000);
  // Açılış pencereleri sırayla çıkar: günlük ödül ("Ödülü al"),
  // Günün Haberleri (X) ve Büyücünün İksirleri (X). Hangilerinin çıktığı
  // girişe göre değişir (ör. "Baskın yedin!"); kayma 0 çıkarsa önce
  // 1_acilis.png'de açık kalan pencereye bakın.
  for (const [x, y] of [[388, 493], [686, 80], [731, 40]]) {
    await tikla(x, y);
    await bekle(3000);
  }
  await cek("1_acilis");

  // 1) Haritayı sürükle: ortadan sol üste.
  await sayfa.mouse.move(...nokta(380, 330));
  await sayfa.mouse.down();
  for (let i = 1; i <= 20; i++) {
    await sayfa.mouse.move(...nokta(380 - 8 * i, 330 - 5 * i));
    await bekle(40);
  }
  await sayfa.mouse.up();
  await bekle(1500);
  await cek("2_surukleme");

  // 2) Boş bir yere tek tıklama (köylü seçiliyse yürür, seçili değilse bir şey olmaz).
  await tikla(500, 420);
  await bekle(1500);
  await cek("3_tiklama");

  gunluk.push(`DIS ISTEKLER (${disIstekler.length}): ${disIstekler.join(" ")}`);
  fs.writeFileSync(path.join(cikti, "konsol.txt"), gunluk.join("\n") + "\n");
  console.log(`Bitti: ${cikti}/ (${gunluk.length} konsol satiri)`);
  await tarayici.close();
})().catch((h) => { console.error(h); process.exit(1); });
