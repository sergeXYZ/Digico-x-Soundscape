@echo off
cd /d "%~dp0"
set "PY=%~dp0python\python.exe"
set "ROOT=%~dp0"

if not exist "%PY%" (
    echo FEHLER: Portable Python fehlt in python\
    pause
    exit /b 1
)

if not exist "%ROOT%.portable_ready" (
    echo Portable Python noch nicht eingerichtet — Setup startet...
    call "%ROOT%setup_portable.bat"
    if errorlevel 1 exit /b 1
)

set "PYTHONPATH=%ROOT%;%PYTHONPATH%"

echo DiGiCo DS100 Bridge — EXE bauen
echo.

"%PY%" -m pip install --no-index --find-links="%ROOT%wheels" -r "%ROOT%requirements-build.txt"
if errorlevel 1 (
    echo PyInstaller Installation fehlgeschlagen.
    pause
    exit /b 1
)

"%PY%" -m PyInstaller "%ROOT%digibridge.spec" --noconfirm --clean
if errorlevel 1 (
    echo PyInstaller Build fehlgeschlagen.
    pause
    exit /b 1
)

copy /Y "%ROOT%settings.json" "%ROOT%dist\settings.json" >nul 2>&1
copy /Y "%ROOT%dist\Digico-x-Soundscape.exe" "%ROOT%Digico-x-Soundscape.exe" >nul 2>&1

echo.
echo Fertig: dist\Digico-x-Soundscape.exe
echo Optional: Digico-x-Soundscape.exe + settings.json ohne Python-Ordner nutzen.
echo.
pause
