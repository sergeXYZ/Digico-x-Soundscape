@echo off
cd /d "%~dp0"
if not exist Digico-x-Soundscape.exe (
    echo Digico-x-Soundscape.exe nicht gefunden. Zuerst build_exe.bat ausfuehren.
    pause
    exit /b 1
)
Digico-x-Soundscape.exe
