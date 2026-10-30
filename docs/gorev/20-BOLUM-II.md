# SOCIAL EMPIRES TR GÖREV KİTABI: BÖLÜM II (açık işler ve sahibinin testleri)

Önce `00-CEKIRDEK.md` dosyasını oku. Bu dosya §6 (açık işler) ve §7 (sahibinin elle yapacağı testler) bölümlerini içerir.

## 6. Açık işler

`BULGULAR.json`'da durumu `acik`, `onay_bekliyor`, `ertelendi` ya da `engelli` olan maddeler. Yeni işe başlamadan
önce buradan seç; sahibinin kararı gerekenleri ona sor.

| Madde  | Durum           | Ne gerekiyor                                                                      |
| ------ | --------------- | --------------------------------------------------------------------------------- |
| DAG-04 | onay_bekliyor   | Sahibi gerçek Android telefon ve iPad'de dener (§7.1)                             |
| HIZ-03 | ci_bekliyor     | Karar verildi: kısa ekranlarda başlık sıkışık düzene geçer (alan oyuna)            |
| HIZ-02 | ertelendi       | Mobil LCP 3,7 sn (yavaş 4G benzetimi); ev ağında sorun beklenmiyor                 |
| ICR-01 | engelli         | İstemcinin AS3 bayt kodunu değiştirmeden yapılamaz                                 |
| VAR-01 | duzeltildi (◐)  | Ateş topu efektinin ekrandaki görünüşü gözle denetlenmedi (§7.2)                   |
| KAR-05 | karar_verildi (◐) | Tema setlerinin takvim kipi için açık bir "evet" alınmadı                        |

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

İlk sürümü yayınlamak için etiket gönderin (ya da bunu Claude'dan isteyin):

```bash
git tag v0.1.0
```

```bash
git push origin v0.1.0
```

Sürüm sayfasındaki zip'i Python kurulu olmayan bir bilgisayarda açıp `Social Empires.bat` dosyasına çift tıklayın.
