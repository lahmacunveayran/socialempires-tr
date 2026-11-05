# Testin gücünün ölçümü

Bu belge testlerimizin hatayı **gerçekten yakalayıp yakalamadığını** nasıl ölçtüğümüzü, ölçümün sonucunu ve
sınırlarını yazar. Sahibinin isteği (5 Kasım 2026): tahmin değil ölçüm, kaynaklı ve tekrarlanabilir.

## 1. Neden "testler geçiyor" yetmez

- Bir test kodu **çalıştırıp** hiçbir şeyi **denetlemeyebilir**. Satır kapsamı (coverage) yalnızca ilkini gösterir.
  Büyük bir çalışmada kapsam ile hata yakalama arasında güçlü ilişki bulunmadı: Inozemtseva ve Holmes,
  "Coverage is not strongly correlated with test suite effectiveness", ICSE 2014,
  <https://doi.org/10.1145/2568225.2568271>.
- Google da kapsamı hedef değil, yol gösterici sayar (%60 kabul edilebilir, %75 iyi, %90 örnek):
  <https://testing.googleblog.com/2020/08/code-coverage-best-practices.html>.
- Testin asıl zayıf yeri **beklenen değerdir** (oracle). Beklenen değer kodun kendi çıktısından alınırsa test, kod
  bozulduğunda da geçer. Barr vd., "The oracle problem in software testing: a survey", TSE 2015,
  <https://doi.org/10.1109/TSE.2014.2372785>. Yapay zekânın yazdığı testlerin bilinen zayıflığı da budur. Meta bu
  yüzden ürettiği testleri mutantlarla sınar: Foster vd., "Mutation-Guided LLM-based Test Generation at Meta",
  FSE 2025, <https://arxiv.org/abs/2501.12862>.

## 2. Yöntem: mutasyon testi

Kodu bir araç küçük küçük bozar ("mutant"): `+` yerine `-`, `<` yerine `<=`, `a.tam(2)` yerine `a.tam(1)`, sabit
yerine başka bir sayı. Her mutantta bütün testler koşar. En az bir test düşerse mutant **öldü**; hiçbiri düşmezse
**kaldı**. Öldürme oranı testin gücüdür.

- Mutantların gerçek hataların yerine geçebileceği ölçüldü: gerçek hataların %73'ü bir mutantla eşleşir. Just vd.,
  "Are mutants a valid substitute for real faults in software testing?", FSE 2014,
  <https://doi.org/10.1145/2635868.2635929>.
- Google bunu her gün kod incelemesinde kullanır: Petrović vd., "Practical Mutation Testing at Scale: A view from
  Google", TSE 2022, <https://doi.org/10.1109/TSE.2021.3107634>.
- Bütün mutantları koşmak gerekmez: rastgele birkaç bin mutant, toplam oranı birkaç puan içinde verir. Gopinath vd.,
  "How hard does mutation analysis have to be, anyway?", ISSRE 2015.

**Eşdeğer mutant.** Bazı mutantlar programın davranışını hiç değiştirmez (ör. hiç okunmayan bir varsayılan
değer). Bunları hiçbir test öldüremez; oran olduğundan düşük görünür. Kalan mutantların yaklaşık %45'i eşdeğer
bulunmuştur (Schuler ve Zeller, "Covering and uncovering equivalent mutants", STVR 2013,
<https://doi.org/10.1002/stvr.1473>). Hangisinin eşdeğer olduğunu her durumda otomatik bilmek mümkün değildir
(Madeyski vd., TSE 2014, <https://doi.org/10.1109/TSE.2013.44>). Biz örneklem alıp elle baktık (§5).

## 3. Araçlar ve kurallar

| Araç | Sürüm | Görevi |
|---|---|---|
| cosmic-ray | 8.7.0 | Mutantları üretir ve koşar (mutmut Windows'ta çalışmaz, S-48) |
| coverage.py | 7.17.2 | Dal kapsamı; hiçbir testin çalıştırmadığı satırı bulur |
| Hypothesis | 6.170.14 | Özellik tabanlı testler (`tests/test_degismezler.py`) |

Ölçüm aracı: `araclar/mutasyon_olc.py`. Sayım kuralları:

1. `oyun/` altındaki **bütün** mutantlar üretilir; operatör ayıklanmaz (cosmic-ray'in hepsi).
2. Tohumla (`20261105`) tekrarlanabilir **basit rastgele örneklem**: 2000 mutant.
3. coverage.py'nin açıkça "çalışmadı" dediği deyimdeki mutant koşulmaz, **kaldı** sayılır ("kapsam dışı").
   Öldürülemeyeceği kesindir; böylece kapsam eksiği de oranın içinde görünür. Kuşkulu durumda mutant koşulur
   (kural `mutasyon_olc.kapsam_disi`, testi `tests/test_mutasyon_olc.py`).
4. Test komutu `python -B -m unittest discover -s tests -f`, mutant başına 120 sn sınır. Zaman aşımı öldü sayılır.
5. Aracın açamadığı mutant ("geçersiz") sayılmaz; ayrıca yazılır.
6. Oranlar **Wilson %95 aralığıyla** verilir (küçük örneklemde normal yaklaşımdan güvenilir).

## 4. Temel ölçüm (önce)

Kod: test düzeltmelerinden önceki hâl (`ada-ocagi`, d330208). Üretilen mutant 16 125; örneklem 2000; geçersiz 1.
Satır kapsamı %72 (4172/5556 satır, 1127/1852 dal).

| Modül | n | Öldü | Kaldı | Kapsam dışı | Öldürme oranı (%95) |
|---|---:|---:|---:|---:|---|
| komutlar | 482 | 248 | 116 | 118 | %51,5 [47,0; 55,9] |
| dunya | 270 | 66 | 151 | 53 | %24,4 [19,7; 29,9] |
| swf_font | 248 | 58 | 38 | 152 | %23,4 [18,5; 29,0] |
| swf_yama | 151 | 46 | 9 | 96 | %30,5 [23,7; 38,2] |
| istemci | 88 | 57 | 23 | 8 | %64,8 [54,4; 73,9] |
| fx_yama | 73 | 50 | 17 | 6 | %68,5 [57,1; 78,0] |
| pvp | 72 | 39 | 31 | 2 | %54,2 [42,7; 65,2] |
| turnuva | 62 | 29 | 33 | 0 | %46,8 [34,9; 59,0] |
| kayit | 56 | 34 | 15 | 7 | %60,7 [47,6; 72,4] |
| elo | 43 | 28 | 15 | 0 | %65,1 [50,2; 77,6] |
| diğer 24 modül | 454 | 235 | 138 | 81 | %51,8 |
| **Toplam** | **1999** | **890** | **586** | **523** | **%44,5 [42,4; 46,7]** |

Yalnızca kapsanan satırlarda: 890/1476 = **%60,3 [57,8; 62,8]**.

**Düzeltme (PR #36 incelemesi).** İlk raporda oran %42,6 [40,4; 44,8] yazılmıştı. Araç, çok satırlı bir deyimin
devam satırındaki mutantı "kapsam dışı" sayıp koşmuyordu: coverage.py deyimi yalnızca ilk satırıyla yazar (küçük
bir örnekle doğrulandı, testte yazılı). 621 kapsam dışı mutantın 98'i böyleydi; hepsi aynı commit'te gerçekten
koşuldu, 39'u öldü. Yukarıdaki tablo düzeltilmiş hâlidir.

## 5. Eşdeğer mutant tahmini

Kapsanan satırlarda kalan mutantlardan rastgele 40'ına elle bakıldı. **9'u eşdeğer** (biri "büyük olasılıkla",
üçü config değerleriyle doğrulandı): 9/40 = %22,5 [12,3; 37,5]. Örnekler: hiç okunmayan bir varsayılan değer
(`p.get("id", -1)` yerine `p.get("id", not 1)`), sonucu değiştirmeyen sınır (`<` / `<=` eşit olamayan değerlerde).

Bu oran 586 kalana uygulanırsa yaklaşık 132'si (72-220) eşdeğer. Düzeltilmiş oran: toplamda **%48 [46; 50]**,
kapsanan satırlarda **%66 [63; 71]**. Bu bir tahmindir (◐); ham oran ölçümdür (✔). Örneklem, düzeltmeden önceki
527 kalandan çekildi; sonradan koşulan 98'in kalanları örneklemde yok.

## 6. Kalan mutantlar ne söyledi

Örneklemdeki kalanlar türlerine göre okundu:

1. **Argüman sırası.** komutlar'da en kalabalık tür `a.tam(2)` yerine `a.tam(1)` gibi mutantlardı. Eski testler
   tek kasaba ve x = y olan eşyalarla yazılmıştı; sıra karışsa da aynı sonuç çıkıyordu.
   → `tests/test_arguman_sirasi.py`: beklenen sıra istemcinin bayt kodundan üretilen
   `docs/inceleme/1407-komutlar.md`'den okunur; iki kasaba, x ≠ y, her argümana ayrı değer.
2. **Hiç çalışmayan işleyiciler.** 128 komut işleyicisinin 60'ı hiçbir testte çalışmıyordu (coverage ile sayıldı;
   TST-02'deki elle sayım 65/125 idi).
   → `tests/test_istemci_kaynakli.py`: nakit ya da depo değiştiren testsiz komutlar; beklenen değerin hangi istemci
   yönteminden okunduğu her testte yazılı.
3. **Hata yolunda yarım kalan kayıt.** Bozuk komut kaydı yarım değiştirip bırakabiliyordu.
   → `tests/test_degismezler.py`: her komut rastgele argümanlarla koşar; beş değişmez (kaynak ve nakit eksiye
   düşmez ve tamsayıdır, kayıt JSON'a sorunsuz yazılır, kayıt şeması bozulmaz, hata veren komut kaydı değiştirmez,
   depo listesi oyundaki en büyük eşya id'sini geçmez).
4. **Sabitlenmemiş denge değerleri.** `denge`, `elo` ve `pvp`'deki sabitler (ör. `4 * 3600` yerine `4 ^ 3600`)
   hiçbir testte sınanmıyor. Bunların doğru değeri istemci ya da sahibinin kararıdır; teste yazılmadı (§8).
5. **Bot dünyası (`dunya`).** En zayıf büyük modül (%24, sonra %23). Benzetim çıktısının doğru değeri belgeli değil.

## 7. Ölçümün bulduğu hatalar

| Hata | Kanıt | Durum |
|---|---|---|
| Hata veren komut kaydı yarım değiştirip bırakıyordu (ör. nakit düşüp eşya verilmeden hata) | `test_degismezler` eski kodda 6 başarısızlık ve 3 hata verdi (D4 ve D5) | Düzeltildi: `command()` her komuttan önce kaydın kopyasını alır, hata olursa geri yükler (~2 ms) |
| `depo_ekle` oyunda olmayan dev id'yi kabul ediyordu: id 10⁸ → 100 milyon elemanlı liste | Değişmez D5: depo listesi en büyük eşya id'sini (50031) geçmemeli | Düzeltildi: config'te olmayan id reddedilir |
| Sunak yokken nakitle alınan kahraman iki kez veriliyordu (depoda ve haritada) | İstemci `PopupHeroes/onBuyItem`: sunak yoksa `store_add_items` gönderir, ardından `buy_cash`'i pencere konumuyla yine gönderir | Düzeltildi: kahraman yalnızca sunak (150) varsa haritaya konur |
| Koleksiyon ödülü yeniden yüklemede kayboluyor | İstemci `CollectableManager$/getReward` ödülü komutsuz depoya koyuyor (`storeItem(..., false)`); sunucunun `finish_collection`'ı ödül eklemiyor | Açık (BULGULAR) |

## 8. Sınırlar

- Örneklem 2000 mutant; modül başına aralıklar küçük modüllerde geniştir (tabloda yazılı).
- Eşdeğer tahmini 40 mutantlık bir el örneklemine dayanır.
- Mutantlar tek noktalı küçük değişikliklerdir; birden çok yeri birlikte bozan hatayı temsil etmeyebilir
  (Just vd. 2014: gerçek hataların %27'si hiçbir mutantla eşleşmedi).
- Denge sabitlerinin ve bot benzetiminin doğru değeri ölçümle bulunamaz; kaynağı (istemci ya da sahibin kararı)
  olmadan beklenen değer yazılmaz. Kodun kendi çıktısını beklenen değer yapmak testi yine boşa çıkarır.
- Ölçüm yalnızca Python tarafını kapsar; `tests/js` ve istemcinin kendisi ölçülmedi.

## 9. Sonra

Kod: bu PR'ın düzeltmeleri ve yeni testleriyle (cdd3a55). Aynı araç, aynı tohum, aynı (düzeltilmiş) kapsam kuralı.
Kod değiştiği için mutant listesi de değişti (16 125 → 16 142); örneklem bağımsızdır, karşılaştırma oran
üzerinden yapılır. Satır kapsamı %76 (4398/5564 satır, 1212/1856 dal).

| Modül | n | Öldü | Kaldı | Kapsam dışı | Öldürme oranı (%95) | Önce |
|---|---:|---:|---:|---:|---|---|
| komutlar | 532 | 332 | 179 | 21 | %62,4 [58,2; 66,4] | %51,5 |
| dunya | 271 | 61 | 169 | 41 | %22,5 [17,9; 27,8] | %24,4 |
| swf_font | 224 | 64 | 32 | 128 | %28,6 [23,1; 34,8] | %23,4 |
| swf_yama | 156 | 37 | 12 | 107 | %23,7 [17,7; 31,0] | %30,5 |
| istemci | 86 | 50 | 22 | 14 | %58,1 [47,6; 68,0] | %64,8 |
| fx_yama | 92 | 61 | 24 | 7 | %66,3 [56,2; 75,1] | %68,5 |
| pvp | 67 | 42 | 25 | 0 | %62,7 [50,7; 73,3] | %54,2 |
| turnuva | 56 | 21 | 35 | 0 | %37,5 [26,0; 50,6] | %46,8 |
| kayit | 49 | 30 | 16 | 3 | %61,2 [47,2; 73,6] | %60,7 |
| elo | 41 | 28 | 12 | 1 | %68,3 [53,0; 80,4] | %65,1 |
| diğer 24 modül | 426 | 230 | 121 | 75 | %54,0 | %51,8 |
| **Toplam** | **2000** | **956** | **647** | **397** | **%47,8 [45,6; 50,0]** | **%44,5** |

Yalnızca kapsanan satırlarda: 956/1603 = **%59,6 [57,2; 62,0]** (önce %60,3).

Okuma:

- **Toplam** 3,3 puan arttı. İki bağımsız örneklem için oran farkı sınaması: z ≈ 2,1, p ≈ 0,04. Anlamlı ama küçük.
- **komutlar** 10,9 puan arttı (z ≈ 3,5, p < 0,001). Yeni testlerin hedefi buydu; kapsam dışı mutant 118 → 21.
- Diğer modüllerdeki farklar aralıkların içinde: örneklem gürültüsünden ayırt edilemez. Bu modüllere test eklenmedi.
- **Kapsanan satırlarda oran yerinde saydı.** Artışın çoğu, daha önce hiç çalışmayan kodun artık çalışmasından geliyor.
  Yeni çalışan kodda kalan mutantlar (ör. komutlar'da kaldı 116 → 179) büyük ölçüde argüman sırası dışındaki
  türler: varsayılan değerler, yazdırılan hata metinleri, sınır karşılaştırmaları. Her birinin gözlenebilir olup
  olmadığı tek tek okunmadı.
- Hedef sayı konmadı (Google da koymaz). Ölçüm, testin neyi denetlemediğini bulmak için kullanılır.

Not: ikinci koşuda da 92 mutant eski kuralla atlanmış, düzeltmeden sonra koşuldu (aynı yöntem).

## 10. Yeniden ölçmek

Ayrı bir sanal ortamda:

```
python -m venv olcum-ortami
olcum-ortami\Scripts\python -m pip install -r requirements-test.txt cosmic-ray==8.7.0 coverage==7.17.2
olcum-ortami\Scripts\python araclar/mutasyon_olc.py --ornek 2000 --tohum 20261105 --isci 14 --cikti olcum
```

Yalnızca işlenmiş (commit'li) kod ölçülür. 16 çekirdekli makinede 14 işçiyle yaklaşık 1,5 saat sürer. Kalan
mutantlar farklarıyla `olcum/kalanlar.txt`'ye yazılır. Aynı tohum aynı örneklemi seçer; iki ölçüm arasında kod
değiştiyse mutant listesi de değişir, karşılaştırma oran üzerinden yapılır.

Özellik testlerinde geniş arama: `HYPOTHESIS_PROFILE=kesif python -m unittest tests.test_degismezler`
(komut başına 1000 rastgele girdi). CI'da her komut için 25 sabit tohumlu girdi koşar.

## 11. Yeni test yazarken (CLAUDE.md kuralı)

- Test, koruduğu kod bozulunca düşmeli. Emin değilsen kodu elle boz, testi koş.
- Beklenen değerin kaynağı yazılır: istemcinin bayt kodu (yöntem adıyla), belge, config ya da değişmez.
- Uygulamanın kendi çıktısı ya da kendi formülü beklenen değer yapılmaz.
- Sıra, kasaba ve koordinat gibi karışabilecek değerler birbirinden farklı seçilir (x ≠ y, iki kasaba).
