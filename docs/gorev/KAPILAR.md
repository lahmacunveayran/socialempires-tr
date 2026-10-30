# Kalite kapıları

Son güncelleme: 30 Ekim 2026. Push'tan önce yerel kapılar temiz olur; CI kapıları PR'da yeşil olmadan iş bitmiş sayılmaz.

## Ortam (bu bulut oturumu)

| Öğe              | Değer                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------- |
| Python / Node    | 3.13 (CI 3.12) / 22.22                                                                  |
| Tarayıcı         | Playwright Chromium (Ruffle başsız çalışır; GPU yok, "hardware acceleration" uyarısı)   |
| Ağ               | python.org kapalı; npm, PyPI ve GitHub (git, raw) açık; GitHub REST API kimliksiz sınırlı |

## Yerel kapılar (her push'tan önce)

| Kapı                | Komut                                       | Son sonuç                |
| ------------------- | ------------------------------------------- | ------------------------ |
| Python testleri     | `python -m unittest discover -s tests`      | ✔ 130 test (30 Ekim)     |
| Tarayıcı JS testleri | `node --test tests/js/*.test.js`           | ✔ 5 test                 |
| Sözdizimi           | `python -m compileall -q .`                 | ✔                        |
| JS sözdizimi        | `node --check templates/js/*.js`            | ✔                        |

`tests/test_gorev.py` bu kitabın `BULGULAR.json` şemasını da denetler.

## CI kapıları (`.github/workflows/`)

| Kapı                     | İş akışı                  | Son sonuç                                   |
| ------------------------ | ------------------------- | ------------------------------------------- |
| Testler (Python + JS)    | `tests.yml`               | ✔ PR #11                                     |
| CodeQL (Python, JS)      | depo ayarı                | ✔ PR #11; PR #8'deki 5 uyarı giderildi       |
| Windows paketi + sınama  | `windows.yml`             | ✔ PR #11; temiz Windows'ta 1,1 sn'de hazır   |

## Elle kapılar (görsel ya da davranış değişikliğinde)

Sunucu açıkken (`python server.py`) çalıştırılır; oyun varlıkları ilk seferde GitHub'dan iner.

| Kapı                     | Komut                                                                  | Son sonuç                                         |
| ------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------- |
| Ruffle harita deneyi     | `node araclar/harita_deneyi.js <USERID> klasor`                        | ✔ sürükleme (-140,-72), dış istek 0, konsol temiz |
| Sayfa ekranları ve oran  | `node araclar/sayfa_goruntuleri.js <USERID> klasor --oyna`             | ✔ 3 ekranda oran 1,2667, Ruffle 0.7.1 açılıyor    |
| Kayma karşılaştırması    | `python araclar/goruntu_farki.py once.png sonra.png`                   | (deneyin parçası)                                 |
| Haber yoğunluğu          | `python araclar/haber_olcumu.py 30`                                    | ✔ Λ = 1,63 olay/dk                                |
| Cihaz benzetimi          | `node araclar/cihaz_denemesi.js <USERID> klasor --dokun`               | ✔ 9 cihazda sığıyor, oran 1,2667; 6 dokunmatikte Ruffle açılıyor |
| Lighthouse               | `npx lighthouse@12 http://127.0.0.1:5050/play.html --preset=desktop`   | ✔ masaüstü 100 / LCP 0,7 sn / CLS 0               |

Lighthouse giriş yapılmış sayfayı ölçmek için oturum çerezini `--extra-headers` ile alır (ayrıntı: devir notu).
