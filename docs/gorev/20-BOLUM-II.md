# SOCIAL EMPIRES TR GÖREV KİTABI: BÖLÜM II (açık işler ve sahibinin testleri)

Önce `00-CEKIRDEK.md` dosyasını oku. Bu dosya §6 (açık işler) ve §7 (sahibinin elle yapacağı testler) bölümlerini içerir.

## 6. Açık işler

`BULGULAR.json`'da durumu `acik`, `onay_bekliyor`, `ertelendi` ya da `engelli` olan maddeler. Yeni işe başlamadan
önce buradan seç; sahibinin kararı gerekenleri ona sor.

| Madde  | Durum           | Ne gerekiyor                                                                      |
| ------ | --------------- | --------------------------------------------------------------------------------- |
| DAG-04 | onay_bekliyor   | Sahibi gerçek Android telefon ve iPad'de dener (§7.1)                             |
| HIZ-03 | duzeltildi      | Karar verildi: kısa ekranlarda başlık sıkışık düzene geçer (PR #13) (alan oyuna)            |
| HIZ-02 | ertelendi       | Mobil LCP 3,7 sn (yavaş 4G benzetimi); ev ağında sorun beklenmiyor                 |
| ICR-01 | engelli         | 0926'da yapılamaz; 1.4.07'ye tam geçişte GEC-07 ile çözülecek (KAR-08)             |
| VAR-01 | duzeltildi (◐)  | Ateş topu efektinin ekrandaki görünüşü gözle denetlenmedi (§7.2)                   |
| KAR-05 | karar_verildi (◐) | Tema setlerinin takvim kipi için açık bir "evet" alınmadı                        |
| GEC-01 … GEC-09 | acik   | 1.4.07'ye tam geçiş, sırayla (`docs/YOL_HARITASI_1407.md` §3)                     |
| KAR-13 | karar_verildi | GEC-03 bitince alanlara bölünmüş bağımsız denetim (Lyraska DENETIM-2 yöntemi)     |
| OYN-11 … OYN-13 | acik   | Küçük işler: günlük ödül başlığı, seviye/XP bilgisi, "Yedek yükle" klavye         |
| ONR-01 … ONR-04 | acik   | Öneriler; her birinin taslak tanımı başlamadan önce sahibine onaylatılır (§5)       |
| KYN-02, KYN-04 | acik    | Soul Mixer ve ölü yamalar geçişle (GEC-01 … GEC-03) ele alınır                      |
| OYN-05, OYN-07, OYN-08, VAR-03, DAG-12, DNT-02 | onay_bekliyor | Sahibi 1.4.07 sürümünde tablette dener (§7.4) |

## 7. Sahibinin elle yapacağı testler

### 7.1 Telefon ve tablet (DAG-04)

Benzetimde (`node araclar/cihaz_denemesi.js <USERID> klasor --dokun`) iPhone, Pixel ve iPad dik/yatayda düzen
doğru; gerçek Safari ve gerçek parmakla deneme yine de gerekli.


1. Bilgisayarda `ayarlar.json` dosyasında `"ev_agi": true` yapın ve oyunu başlatın.
2. Sunucunun açılışta yazdığı `http://192.168.x.x:5050/` adresini telefonda açın (aynı Wi-Fi).
3. İmparatorluğa girin, "Krallığa Gir"e basın, bir binaya dokunun, haritayı parmakla kaydırın.
4. Oyundan çıkıp yeniden girin: yaptığınız değişiklik duruyor mu?
5. Aynısını iPad'de deneyin. Sonucu ("çalıştı" ya da gördüğünüz hata) bildirin.

### 7.2 Ateş topu efekti (VAR-01)

Ateş topu atan bir birimle saldırıya geçin ya da saldırıya uğrayın; ateş topu görünüyor mu? Görünmüyorsa ya da tuhaf
görünüyorsa bildirin.

### 7.3 Windows paketi

İlk sürümü yayınlamak için etiket gönderin (ya da bunu yapay zekâ oturumundan isteyin):

```bash
git tag v0.1.0
```

```bash
git push origin v0.1.0
```

Sürüm sayfasındaki zip'i Python kurulu olmayan bir bilgisayarda açıp `Social Empires.bat` dosyasına çift tıklayın.

### 7.4 Tablet denemesi, 1.4.07 sürümünde (GEC-09)

Sahibi PR #18 APK'sını denemeyecek, denemeyi 1.4.07'ye geçiş bitince yapacak (KAR-08). O sürümde bakılacaklar:

1. Yükleme perdesinde "Yükleniyor" yazıyor mu, "Cargando" var mı? (VAR-03)
2. Yüksek kalitede dokunulan yerde koyu yeşil iz kalıyor mu? (OYN-07)
3. Görüntü: Doldur oyunu esnetmeden ekranı kaplıyor mu? (OYN-08)
4. Geri tuşu, durum ve gezinme çubukları (DAG-12); galeriden profil resmi (OYN-05); klavye (DNT-02).

### 7.5 Android imza anahtarı (bir kez)

Sahibinin kararı (KAR-09): bütün işler bittikten sonra, **en son iş** olarak yapılır. Adımlar `ANDROID.md` "İmza
anahtarı" bölümünde. O zamana kadar her yeni APK'da yedek al, kaldır, kur, yükle gerekir.
