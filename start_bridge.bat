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
echo Starte Digico×Soundscape Launcher...
"%PY%" -m bridge.main
