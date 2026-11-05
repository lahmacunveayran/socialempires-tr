# Devir: buluttan devam (6 Kasım 2026)

Sahibi bundan sonra bulut oturumundan devam ediyor. Bu dosya yeni oturumun ilk okuyacağı yerdir. En alttaki
"Devir metni" bölümü sahibinin buluta yapıştıracağı metindir.

## 1. Durum özeti

| Konu | Durum |
|---|---|
| Sahibi | `lahmacunveayran`. İngilizce bilmiyor: her mesaj kısa, sade Türkçe. |
| Faz | 1.4.07'ye tam geçiş (KAR-08, `docs/YOL_HARITASI_1407.md`). GEC-01, GEC-02, GEC-03 bitti ve master'da. |
| Son birleşen | **#38** (GEC-03'ün sonu), squash, `ec2dfe5`. Üç inceleme konuşması düzeltildi ve sahibinin onayıyla kapatıldı. |
| Açık PR | **#39** `test-zayif`: TST-04 testleri (denge 24, SWF yaması 37, bot dünyası 50) ve bu devir belgeleri. Güncel master birleştirildi (`e9d616e`), GitHub "birleştirilebilir" diyor. Son push'ta `inceleme` işi sürüyordu. |
| Yarım kalan | TST-04 yeniden ölçümü 350/1873 mutantta durduruldu (S-56). Yarım ölçüm sonuç sayılmaz; baştan koşulur. |
| Testler | 437 Python, 3 JS; hepsi geçiyor. |
| Bekleyen Dependabot | #32, #33, #34: sahibinin kararında. |

## 2. Sıradaki işler (sırayla)

1. **#39'u bitir.** `gh pr checks 39` ile denetimlere bak. `inceleme` yeni not yazdıysa düzelt (S-42 koruması
   ile push). Konuşmayı yanıtlamak, kapatmak ve PR'ı birleştirmek için **her seferinde sahibine sor** (S-55).
   Birleştirme squash ile, commit metnine model adı yazılmadan.
2. **TST-04 yeniden ölçümü.** #39 birleştikten sonra master'da, §4'teki komutla baştan koş. Sonucu
   `docs/TEST_OLCUMU.md`'ye yeni §12 olarak yaz: modül başına önce/sonra tablosu (önceki ölçüm §9'daki
   tablo: Toplam %47,8 [45,6; 50,0]), fark sınaması, kalan mutantların özeti. BULGULAR'da TST-04 notuna ekle.
   Ayrı bir PR aç.
3. **OYN-14:** bot dünyası seviye eşiğini sunucunun geri kalanından bir kaydırarak okuyor (✔ açık). Önce
   istemcinin eşiği nasıl okuduğunu bayt kodundan bul (`araclar/abc_okur.py`; SWF gerekir, §5). Sonra
   `dunya._ekonomi`, `config.get_level_from_xp`, `rt_level_up`, `get_xp_from_level`, `sunucu._xp_araligi` tek
   okumaya bağlanır. Test, beklenen değeri istemciden alır.
4. **KAR-13:** bağımsız denetim (GEC-03 bitti). Başlamadan önce sahibine kullanım payını hatırlat.
5. **GEC-04'ün kalanı** (geri dönüş testi), sonra **GEC-05** (PvP: kalan 8 komut `begin_attack_new`,
   `buy_shield`, `clean_attack_log`, `end_attack_new`, `end_tournament_match`, `get_enemy_new`, `reply_attack`,
   `reset_shield`; kalkan; KYT-03). OYN-15 … OYN-17 (◐) burada doğrulanır.
6. **Sahibinden kararlar:** KMT-08 (görev sınırı uygulanmıyor), KMT-09 (Asker Toplama çevrimdışı açılsın mı),
   TST-04 notundaki kaynaksız denge sabitleri, ONR-01 … ONR-04, v0.1.0 (GEC-09). Karar vermek sahibinindir;
   seçenekleri sade Türkçeyle sun.

## 3. Bulut ortamını kurmak

```
pip install -q --ignore-installed blinker -r requirements-test.txt
python -m unittest discover -s tests        # 437 test
node --test tests/js/*.test.js              # 3 test
```

`requirements-test.txt` Hypothesis'i de kurar; kurulmazsa `test_degismezler` içe aktarılamaz ve sayı 435'e
düşer (S-50). Testler oyun SWF'lerine ihtiyaç duymaz (`test_swf_yama` kendi SWF'lerini kurar).

## 4. Mutasyon ölçümü

```
python -m venv olcum-ortami
olcum-ortami/bin/python -m pip install -r requirements-test.txt cosmic-ray==8.7.0 coverage==7.17.2
olcum-ortami/bin/python araclar/mutasyon_olc.py --ornek 2000 --tohum 20261105 --isci <çekirdek-2> --cikti olcum
```

- Yalnızca commit'li kod ölçülür; araç işçi başına ayrık çalışma ağacı açar.
- 16 çekirdekte 14 işçiyle yaklaşık 1,5-2 saat. Bulutta çekirdek azsa daha uzun sürer: başlamadan sahibine
  süreyi söyle, arka planda koştur.
- Yarıda durursa `git worktree list` ile kalan ağaçları kaldır (`git worktree remove --force`, `git worktree
  prune`), sonra baştan koş (S-56).
- Bozma denemesinden sonra dosyayı `git checkout --` ile geri alma; işlenmemiş iş silinir (S-53). Bellekte
  saklayıp geri yaz.

## 5. Bulutta dikkat

- Oyun SWF'leri (`download_assets/`) depoda yok. Bayt kodu okumak gerekirse (OYN-14, GEC-05) sahibinden iste ya
  da `varliklari_indir.py`'nin indirdiği yerden al. İndirilen kod çalıştırılmaz, yalnızca okunur (S-11);
  kendi klasörüne konur, okuyan Python `-I` ile koşar.
- Üst üste PR açılırsa açıklamaya birleştirme sırası yazılır (S-44). Push'tan önce
  `test "$(gh pr view <no> --json state -q .state)" = OPEN && git push` (S-42).
- `sinama` işi koddan bağımsız düşebilir (emülatör); bir kez yeniden çalıştırılır (S-43).
- Master'a doğrudan push yok, force-push ve rebase yok, testler gevşetilmez, model adı hiçbir metne yazılmaz.

## Devir metni (buluta yapıştırılacak)

```
Social Empires Türkçe sunucusunda (lahmacunveayran/socialempires-tr) çalışmaya devam et. Benimle her zaman kısa,
sade Türkçe konuş; İngilizce bilmiyorum.

Bu devir belgeleri test-zayif dalında (PR #39). Master'a henüz girmediyse o dalı aç (git fetch origin &&
git checkout test-zayif). Önce şunları oku: CLAUDE.md, docs/gorev/DEVIR.md, docs/gorev/00-CEKIRDEK.md,
docs/gorev/BULGULAR.json (devam_noktasi), docs/gorev/SORUN_COZUM.md ve son devir notu docs/devlog/2026-11-06.md.
Ortamı DEVIR.md §3'teki gibi kur ve testlerin geçtiğini gör (437 Python, 3 JS).

Kurallar CLAUDE.md'de; özellikle: kendi ürettiğin görsel yok, tek kişilik ve çevrimdışı, commit ve PR metinlerine
model adı yazılmaz, master'a doğrudan gönderilmez, testler gevşetilmez, yeni test koruduğu kod bozulunca düşmeli
ve beklenen değerin kaynağı yazılır. İnceleme konuşmasını yanıtlamak ya da kapatmak ve PR birleştirmek için her
seferinde bana sor.

Sıradaki işler DEVIR.md §2'deki sırayla: önce #39 (denetimlere bak, birleştirmek için bana sor), sonra test
ölçümünü baştan koş ve TEST_OLCUMU.md §12'ye yaz (başlamadan ne kadar süreceğini söyle), sonra OYN-14 (bot seviye
eşiği), sonra KAR-13 bağımsız denetim (başlamadan önce kullanım payımı hatırlat). Her adımın sonunda ne yaptığını
ve sırada ne olduğunu bana kısaca söyle.
```
