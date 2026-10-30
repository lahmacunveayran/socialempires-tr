#!/usr/bin/env bash
# Emülatörde kabul kapısı: APK kurulur, açılır; uygulamanın içindeki sunucu 4 dakika içinde hazır olmalı,
# Ruffle uygulamayla gelmiş olmalı ve WebView oyun sayfasını istemiş olmalı.
# Kullanım (emülatör açıkken): bash android/sinama.sh <apk> [ekran.png]
set -uo pipefail
APK="$1"
EKRAN="${2:-ekran.png}"
PAKET=io.github.lahmacunveayran.socialempirestr

adb install -r "$APK" || exit 1
adb logcat -c
baslangic=$(date +%s)
adb shell am start -W -n "$PAKET/.MainActivity" || exit 1
adb forward tcp:5050 tcp:5050

hazir=0
for _ in $(seq 1 120); do
  if curl -fsS --max-time 2 http://127.0.0.1:5050/saglik/hazir >/dev/null 2>&1; then hazir=1; break; fi
  sleep 2
done
echo "Hazır olma süresi: $(( $(date +%s) - baslangic )) sn"

sleep 15  # WebView giriş sayfasını yüklesin
adb exec-out screencap -p > "$EKRAN" || true
echo "--- Python ve uygulama günlüğü ---"
adb logcat -d -s python.stdout:V python.stderr:V SocialEmpires:V AndroidRuntime:E | tail -80

[ "$hazir" = 1 ] || { echo "Sunucu 4 dakika içinde hazır olmadı"; exit 1; }
curl -fsS http://127.0.0.1:5050/saglik; echo
kod=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5050/ruffle/0.7.1/ruffle.js)
[ "$kod" = 200 ] || { echo "Ruffle uygulamayla gelmemiş ($kod)"; exit 1; }
adb shell pidof "$PAKET" >/dev/null || { echo "Uygulama kapanmış"; exit 1; }
echo "Tamam: sunucu hazır, Ruffle var, uygulama açık."
