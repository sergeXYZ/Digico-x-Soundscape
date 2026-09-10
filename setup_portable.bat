@echo off
cd /d "%~dp0"
set "PY=%~dp0python\python.exe"
set "ROOT=%~dp0"

if not exist "%PY%" (
    echo FEHLER: Portable Python fehlt in %ROOT%python\
    pause
    exit /b 1
)

echo ========================================
echo  Digico-x-Soundscape — Portable Python Setup
echo ========================================
echo.

if not exist "%ROOT%python\Lib\site-packages" mkdir "%ROOT%python\Lib\site-packages"

echo [1/2] pip installieren (offline)...
"%PY%" "%ROOT%get-pip.py" --no-index --find-links="%ROOT%wheels" --no-warn-script-location
if errorlevel 1 (
    echo pip Installation fehlgeschlagen.
    pause
    exit /b 1
)

echo [2/2] Abhaengigkeiten installieren (offline)...
"%PY%" -m pip install --no-index --find-links="%ROOT%wheels" -r "%ROOT%requirements.txt"
if errorlevel 1 (
    echo Paket-Installation fehlgeschlagen.
    pause
    exit /b 1
)

echo ok> "%ROOT%.portable_ready"
echo.
echo Fertig — portable Python ist bereit.
exit /b 0
