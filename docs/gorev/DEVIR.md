# Devir: buluttan devam (6 Kasım 2026)

Sahibi bundan sonra bulut oturumundan devam ediyor. Bu dosya yeni oturumun ilk okuyacağı yerdir; aşağıdaki
"Devir metni" bölümü sahibinin buluta yapıştıracağı metindir.

## Durum özeti

- **Sahibi:** `lahmacunveayran`. İngilizce bilmiyor: her mesaj kısa, sade Türkçe.
- **Faz:** 1.4.07'ye tam geçiş (KAR-08, `docs/YOL_HARITASI_1407.md`). GEC-01, GEC-02 ve GEC-03 bitti.
- **Açık PR'lar** (birleştirme sırası önemli, S-44):
  1. **#38** `gec03-kalan`: GEC-03'ün sonu. Kontroller yeşil. İki inceleme konuşması düzeltildi (f1d0c1f) ama
     kapatılmadı: kapatmak sahibinin onayını ister (S-55). Önce bu birleşir.
  2. **#39** `test-zayif`: TST-04 testleri (denge 24, SWF yaması 37, bot dünyası 50) ve yeniden ölçüm. #38'in
     dalı içine birleştirildi; #38 squash ile birleşince bu dala güncel `master` birleştirilir (çakışmada iki
     tarafın ağacı aynıysa `git checkout --ours`, ağaç eşitliği `git diff` ile denetlenir), sonra birleşir.
  3. Dependabot #32-#34: sahibinde.
- **Testler:** 437 Python, 3 JS. `pip install -q --ignore-installed blinker -r requirements-test.txt` gerekir.

## Sıradaki işler (sırayla)

1. #38'in iki konuşmasını kapatmak için sahibinden onay al; #38'i birleştir (squash, model adı yazmadan).
2. #39'a güncel master'ı birleştir, testler ve inceleme geçince birleştir.
3. **OYN-14:** bot dünyası seviye eşiğini sunucunun geri kalanından bir kaydırarak okuyor. Önce istemcinin
   seviye eşiğini nasıl okuduğunu bayt kodundan bul (`araclar/abc_okur.py`); sonra `dunya._ekonomi`,
   `config.get_level_from_xp`, `rt_level_up`, `get_xp_from_level`, `sunucu._xp_araligi` tek okumaya bağlanır.
4. **KAR-13:** bağımsız denetim (GEC-03 bitti). Başlamadan önce sahibine kullanım payını hatırlat.
5. GEC-04'ün kalanı (geri dönüş testi), sonra GEC-05 (PvP, kalkan, KYT-03; OYN-15 … OYN-17 burada doğrulanır).
6. Sahibinden kararlar: KMT-08 (görev sınırı), KMT-09 (Asker Toplama çevrimdışı), TST-04 notundaki denge
   sabitleri, ONR-01 … ONR-04, v0.1.0 (GEC-09).

## Bulutta dikkat

- Oyun SWF'leri (`download_assets/`) depoda yok. Bayt kodu okumak gerekirse sahibinden iste ya da
  `varliklari_indir.py`'nin indirdiği yerden al; indirilen kod çalıştırılmaz, yalnızca okunur (S-11).
- Mutasyon ölçümü (`araclar/mutasyon_olc.py`) Linux'ta da çalışır; cosmic-ray 8.7.0 ve coverage 7.17.2 gerekir.
- İnceleme konuşmasını kapatmak, PR birleştirmek, dışarıya yazmak: her seferinde sahibine sor.

## Devir metni (buluta yapıştırılacak)

```
Social Empires Türkçe sunucusunda (lahmacunveayran/socialempires-tr) çalışmaya devam et. Benimle her zaman kısa,
sade Türkçe konuş; İngilizce bilmiyorum.

Bu devir belgeleri test-zayif dalında (PR #39); master'a henüz girmediyse o dalı aç (git fetch origin &&
git checkout test-zayif) ya da oradan oku. Önce şunları oku: CLAUDE.md, docs/gorev/DEVIR.md, docs/gorev/00-CEKIRDEK.md, docs/gorev/BULGULAR.json
(devam_noktasi), docs/gorev/SORUN_COZUM.md ve son devir notu docs/devlog/2026-11-06.md. Kurallar CLAUDE.md'de;
özellikle: kendi ürettiğin görsel yok, tek kişilik ve çevrimdışı, commit ve PR metinlerine model adı yazılmaz,
master'a doğrudan gönderilmez, testler gevşetilmez, yeni test koruduğu kod bozulunca düşmeli ve beklenen değerin
kaynağı yazılır.

Sıradaki işler DEVIR.md'deki sırayla: önce #38 (iki inceleme konuşmasını kapatmak için bana sor), sonra #39
(güncel master birleştirilir), sonra OYN-14 (bot seviye eşiği), sonra KAR-13 bağımsız denetim (başlamadan önce
kullanım payımı hatırlat). Her adımın sonunda ne yaptığını ve sırada ne olduğunu bana kısaca söyle.
```
