@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  Social Emperors - Turkce gelistirme sunucusu
echo ============================================

python -c "import flask, jsonpatch" >nul 2>&1
if errorlevel 1 (
    echo [1/2] Gerekli Python paketleri kuruluyor...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo HATA: Paketler kurulamadi. Python 3 kurulu mu? Internet var mi?
        pause
        exit /b 1
    )
) else (
    echo [1/2] Python paketleri hazir.
)

if not exist "assets\flash\SocialEmpires0926bsec.swf" (
    echo NOT: Oyun varliklari yerelde yok; ilk acilista internetten indirilecek.
    echo      Hepsini simdi indirmek icin: python varliklari_indir.py
)

echo [2/2] Sunucu baslatiliyor: http://127.0.0.1:5050/
echo       Kapatmak icin bu pencereyi kapatmayin, Ctrl+C yapin.
start "" /b powershell -NoProfile -Command "$u='http://127.0.0.1:5050/saglik/hazir'; for($i=0;$i -lt 120;$i++){ try { $r=Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 1; if($r.StatusCode -eq 200){ Start-Process 'http://127.0.0.1:5050/'; break } } catch {}; Start-Sleep -Milliseconds 500 }"
python server.py
pause
