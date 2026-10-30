#!/usr/bin/env bash
# Emülatörde kabul kapısı: APK kurulur, açılır; uygulamanın içindeki sunucu 4 dakika içinde hazır olmalı,
# Ruffle uygulamayla gelmiş olmalı ve uygulama açık kalmalı. Uygulama sunucuyu açamazsa beklemeden düşer.
# Her adımın süre sınırı vardır; takılan adım günlükte adıyla görünür.
# Kullanım (emülatör açıkken): bash android/sinama.sh <apk> [ekran.png]
set -uo pipefail
APK="$1"
EKRAN="${2:-ekran.png}"
PAKET=io.github.lahmacunveayran.socialempirestr

adim() { echo "== $(date +%H:%M:%S) $*"; }
gunluk() {
  echo "--- Python ve uygulama günlüğü ---"
  timeout 30 adb logcat -d -s python.stdout:V python.stderr:V SocialEmpires:V AndroidRuntime:E | tail -80
}

adim "APK kuruluyor"
timeout 180 adb install -r "$APK" || exit 1
timeout 20 adb logcat -c
baslangic=$(date +%s)
adim "Uygulama açılıyor"
timeout 60 adb shell am start -n "$PAKET/.MainActivity" || exit 1
timeout 20 adb forward tcp:5050 tcp:5050 || exit 1

adim "Sunucu bekleniyor"
hazir=0
while [ $(( $(date +%s) - baslangic )) -lt 240 ]; do
  if curl -fsS --max-time 3 http://127.0.0.1:5050/saglik/hazir >/dev/null 2>&1; then hazir=1; break; fi
  if timeout 20 adb logcat -d -s SocialEmpires:E | grep -q "Sunucu acilamadi"; then
    adim "Uygulama sunucuyu açamadı"; gunluk; exit 1
  fi
  sleep 2
done
echo "Hazır olma süresi: $(( $(date +%s) - baslangic )) sn"

if [ "$hazir" = 1 ]; then
  adim "Giriş sayfası yükleniyor"
  sleep 15
fi
adim "Ekran görüntüsü"
timeout 30 adb exec-out screencap -p > "$EKRAN" || echo "ekran görüntüsü alınamadı"
gunluk

[ "$hazir" = 1 ] || { echo "Sunucu 4 dakika içinde hazır olmadı"; exit 1; }
adim "Sağlık"
curl -fsS --max-time 10 http://127.0.0.1:5050/saglik || exit 1
echo
kod=$(curl -s --max-time 60 -o /dev/null -w "%{http_code}" http://127.0.0.1:5050/ruffle/0.7.1/ruffle.js)
[ "$kod" = 200 ] || { echo "Ruffle uygulamayla gelmemiş ($kod)"; exit 1; }
timeout 20 adb shell pidof "$PAKET" >/dev/null || { echo "Uygulama kapanmış"; exit 1; }
adim "Tamam: sunucu hazır, Ruffle var, uygulama açık."
