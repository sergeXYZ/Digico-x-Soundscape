@echo off
cd /d "%~dp0"
set "PY=%~dp0python\python.exe"
set "ROOT=%~dp0"

if not exist "%PY%" (
    echo FEHLER: Portable Python fehlt. Ordner python\ muss vorhanden sein.
    pause
    exit /b 1
)

if not exist "%ROOT%.portable_ready" (
    echo Erststart — richte portable Python ein (ca. 1 Minute)...
    call "%ROOT%setup_portable.bat"
    if errorlevel 1 exit /b 1
)

set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
echo Starte DiGiCo DS100 Bridge...
echo Browser: http://127.0.0.1:8765/
start http://127.0.0.1:8765/
"%PY%" -m bridge.main
pause
