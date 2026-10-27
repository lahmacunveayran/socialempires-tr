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
        echo HATA: Paketler kurulamadi. Python 3 kurulu mu?
        pause
        exit /b 1
    )
) else (
    echo [1/2] Python paketleri hazir.
)

if not exist "assets" (
    echo UYARI: assets klasoru yok; oyun varliklari yuklenemeyecek.
)

echo [2/2] Sunucu baslatiliyor: http://127.0.0.1:5050/
start "" http://127.0.0.1:5050/
python server.py
pause
