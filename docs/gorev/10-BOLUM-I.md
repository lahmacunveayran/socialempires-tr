# SOCIAL EMPIRES TR GÖREV KİTABI: BÖLÜM I (yol haritası, Faz 0–4)

Önce `00-CEKIRDEK.md` dosyasını oku. Bu dosya §4 (bulgu kaydının özeti) ve §5 (fazlar) bölümlerini içerir. Kaynak plan:
"Social Empires TR Yol Haritası" (30 Ekim 2026, sahibinin belgesi). Ölçümlerin tamamı `docs/YOL_HARITASI_DURUM.md` ve
`docs/FAZ0_OLCUMLER.md` dosyalarında; burada tekrarlanmaz, yalnızca bağlanır.

<kayit>

## 4. Bulgu kaydı

Asıl kayıt `BULGULAR.json`'dur; bu tablo onun özetidir ve çelişirse JSON geçerlidir.

| Önek  | Alan                                | Maddeler              |
| ----- | ----------------------------------- | --------------------- |
| F0    | Faz 0 temel ve ölçüm                | F0-01 … F0-06         |
| VAR   | Oyun varlıkları ve SWF              | VAR-01, VAR-02        |
| GUV   | Güvenlik (CodeQL)                   | GUV-01 … GUV-03       |
| HIZ   | Sayfa hızı ve kayma                 | HIZ-01 … HIZ-03       |
| TAS   | Tasarım                             | TAS-01 … TAS-04       |
| DAG   | Dağıtım (Windows, telefon, CI)      | DAG-01 … DAG-04       |
| ICR   | Oyun içeriği                        | ICR-01                |
| KAR   | Sahibinin kararları                 | KAR-01 … KAR-08       |
| REG   | Oturum içinde yakalanan geri gidişler | REG-01              |
| OYN   | Oynanış ve oyun sayfası             | OYN-01 … OYN-13       |
| DNT   | Bağımsız denetim                    | DNT-01 … DNT-04       |
| KYN   | Upstream ve kaynaklar               | KYN-01 … KYN-05       |
| GEC   | 1.4.07'ye tam geçiş (`docs/YOL_HARITASI_1407.md`) | GEC-01 … GEC-09 |
| ONR   | Sahibinin istediği öneriler         | ONR-01 … ONR-04       |

Çürütülenler (yeniden açma): **F0-01** (Ruffle'da haritaya tıklanıyor; eski yargı eğitim kilidinden), **VAR-02**
("Cargando" artık görünmüyor), **TAS-01** (ğ/İ/ş içermeyen yazı tipleri kullanılmadı).

</kayit>

<fazlar>

## 5. Fazlar

Her faz bir kabul kapısıyla kapanır. ✔ ölçüldü, ◐ dolaylı, ? ölçülmedi.

### 5.1 Faz 0: Temel ve ölçüm (PR #8)

| İş                                   | Sonuç                                               | Madde        |
| ------------------------------------ | --------------------------------------------------- | ------------ |
| Harita tıklaması deneyi              | ✔ çalışıyor; eski yargı çürütüldü                   | F0-01, F0-06 |
| Ruffle 0.7.1 sabit, yerelden         | ✔ dış istek 0                                       | F0-02        |
| Waitress                             | ✔                                                   | F0-03        |
| Sıkıştırma ve önbellek başlıkları    | ✔ 1,96 MB → 151 KB; 304                             | F0-04, F0-05 |

Kabul kapısı ✔ geçti (`docs/FAZ0_OLCUMLER.md`).

### 5.2 Faz 1: Açılış sahnesi (PR #8, #10)

Gökyüzü Güneş yüksekliğine göre (✔ İstanbul doğuş/batış ±1 dk, `tests/js/gokyuzu.test.js`); çerçeve oranı ✔ üç
ekranda tam 1,2667; "Krallığa Gir" ✔; Lighthouse masaüstü ✔ LCP 0,7 sn, CLS 0 (HIZ-01). Mobil LCP ertelendi (HIZ-02).

### 5.3 Faz 2: Canlı dünya (PR #8)

Diyar Haberleri ✔ Λ = 1,63 olay/dk (`araclar/haber_olcumu.py`); Şeref Kürsüsü ✔ 60 sn önbellek, 2–4 ms yanıt.

### 5.4 Faz 3: Oyun içeriği (PR #8, #9)

Etkinlik takvimi ✔ 10 bayram tarihi (`tests/test_icerik.py`); haftalık turnuva Elo ✔ ödül yalnızca ilk 10'a;
kayıt yedeği ✔ bayt bayt aynı. Günlük hediye sandığı yapıldı, sonra sahibinin kararıyla kaldırıldı (KAR-03).
Arthur'un etkinlik hedefleri engelli (ICR-01).

### 5.5 Faz 4: Dağıtım (PR #8, #10, #11)

Windows paketi ✔ temiz Windows'ta 1,1 sn (DAG-01); ev ağı ayarı ve PWA manifesti ✔; Android/iPad ? (DAG-04).

### 5.6 Tasarım işleri (PR #8, #9, #11, açık PR)

Oyunun kendi görselleriyle oyun sayfası, giriş sayfası ve hile paneli (TAS-02 … TAS-04); yazı tipi seçimi ölçülerek
(TAS-01); görsel kuralı (KAR-04). Tasarım ilkeleri `docs/YOL_HARITASI_DURUM.md` "Görsel tasarım".

</fazlar>
