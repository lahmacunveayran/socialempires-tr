# Bağımsız denetim: ortak kurallar (KAR-13)

Social Empires Türkçe, eski Flash oyunu Social Empires için tek kişilik, çevrimdışı, yerel bir sunucudur (Python,
Flask). Oyun mantığı istemcide (Flash dosyası) çalışır; sunucu istemcinin bildirdiği komutları (`command.php`)
taklit edip kayda yazar. Sunucu ayrıca bir "bot dünyası" (50 bilgisayar köyü), haber şeridi, turnuva, hile paneli,
Türkçe SWF yaması ve Android/Windows paketleri içerir.

Bu denetimde sen bağımsız bir denetçisin. Görevin, sana verilen alanda **hataları, istemciyle uyuşmazlıkları,
güvenlik açıklarını ve testlerin korumadığı riskli yerleri** bulmak. Kod değiştirmezsin; rapor yazarsın.

## Nereye bakılır

- **Kod kopyası (salt okunur):** `K = /tmp/claude-0/-home-user-socialempires-tr/657f2b83-acaf-5846-97d6-a44006b9f145/scratchpad/denetim/kok`
  (commit `187e84f`). Yalnızca burayı oku.
- **İstemci:** `/tmp/claude-0/-home-user-socialempires-tr/657f2b83-acaf-5846-97d6-a44006b9f145/scratchpad/denetim/istemci/SocialEmpires1.4.07sec_fixed.swf`
  (SHA-256 `0e4cc178…6a15`). Bayt kodunu `K/araclar/abc_okur.py` ile oku (`Abc`, `abc_etiketleri`,
  `yontem_adlari`, `coz`, `cagrilar`; dosyanın başındaki açıklamaya bak). Kod gizlenmiştir: akışı izleyerek okunur
  (`coz`), doğrusal değil. SWF'yi okuyan Python'u `-I` ile çalıştır ve `sys.path`'e `K/araclar`'ı elle ekle.
- **Kendi çalışma klasörün:** `/tmp/claude-0/-home-user-socialempires-tr/657f2b83-acaf-5846-97d6-a44006b9f145/scratchpad/denetim/is/<alan>/`
  Betiklerini, geçici kayıtlarını buraya yaz. Sunucuyu ya da testleri denemek için `K`'yı buraya kopyalayabilirsin.
- **Raporun:** `/tmp/claude-0/-home-user-socialempires-tr/657f2b83-acaf-5846-97d6-a44006b9f145/scratchpad/denetim/rapor/<alan>.md`

## Yasaklar

- `/home/user/socialempires-tr` (asıl depo) okunmaz: orada önceki bulguların kaydı var, bağımsızlığını bozar.
  Git geçmişi, GitHub, PR'lar, inceleme yorumları da okunmaz. Kopyada `docs/gorev` ve `docs/devlog` bu yüzden yok
  (`tests/test_gorev.py`'nin kopyada düşmesi bundandır, bulgu değildir).
- İnternetten indirme yok. İstemci dışında bir SWF gerekirse "doğrulanamadı" yaz.
- Kodu ya da kopyayı değiştirme. Bozma denemesi gerekirse kendi kopyanda yap.
- Bilgisayar meşgul (arka planda uzun bir ölçüm koşuyor): bütün test takımını en çok iki kez koş; tek test
  dosyası koşmak serbest (`cd tests && python -m unittest test_x`).

## Doğruluk kaynakları (sırayla)

1. İstemcinin bayt kodu (yöntem adıyla: `Sınıf/yöntem`).
2. Oyun config'i (`K/config/game_config_20120826.json`, yamalar `K/config/patch`, `K/mods`).
3. Biçim belgeleri (SWF v19, AVM2), Python/Flask belgeleri.
4. Depodaki belgeler (`K/docs`, `K/docs/inceleme`) projenin **kendi** iddialarıdır: kaynak değil, denetlenecek iddia.
   Kodun yorumları ve testleri de iddiadır; bir testin geçmesi davranışın doğru olduğunu göstermez.

## Kapsam dışı (bulgu sayılmaz, sahibinin kararı)

- Çok oyunculu özellik yokluğu (sunucu bilerek tek kişilik ve çevrimdışı).
- Oyun görsellerindeki İngilizce yazılar (yeniden çizilmez, bilerek).
- Sayfaya kendi çizilmiş görsel eklenmesi önerilmez: yalnızca oyunun kendi resimleri kullanılır. Kendi çizilmiş
  görsel (SVG, emoji, CSS figürü) **bulursan** bu bir bulgudur.
- Günlük ödülün yalnızca oyunun kendi günlük ödülü olması.
- PvP'de henüz yazılmamış 8 komut (`begin_attack_new`, `buy_shield`, `clean_attack_log`, `end_attack_new`,
  `end_tournament_match`, `get_enemy_new`, `reply_attack`, `reset_shield`): bilinen eksik. Yalnızca "yok" demek bulgu
  değildir; var olan kodun bunlara bağlı yanlış davranışı bulgudur.

## Bulgu biçimi

Her bulgu:

```
### <ALAN>-NN: <bir satırlık başlık>
- Önem: Yüksek | Orta | Düşük
- İşaret: ✔ (çalıştırdım/ölçtüm) | ◐ (kod okuması, çalıştırmadım) | ? (doğrulayamadım)
- Yer: dosya:satır (K'ye göre)
- Kanıt: ne çalıştırdın, ne çıktı (✔ için komut ve çıktı şart); istemci kaynağı varsa `Sınıf/yöntem` ve ilgili işlemler
- Etki: oyuncu ne görür / ne kaybeder
- Öneri: kısa (kod yazma)
```

Önem: **Yüksek** = kayıt kaybı, çökme, güvenlik açığı, oyunun ilerleyememesi. **Orta** = istemciyle uyuşmayan,
oyuncunun fark edeceği yanlış davranış. **Düşük** = kenar durumu, küçük tutarsızlık, test eksiği.

Raporun sonunda **"Bakıldı, sorun bulunmadı"** başlığıyla incelediğin ama temiz bulduğun konuları kısaca listele
(neye, nasıl baktın). Böylece kapsam görünür. Uydurma: emin değilsen ◐ ya da ? koy; bulgu sayısı hedef değildir.
Rapor Türkçe yazılır.

Son mesajın: rapor dosyasının yolu ve bulguların tek satırlık listesi (kimlik, önem, işaret, başlık).
