@echo off
cd /d "%~dp0"
echo Avvio Agent Ordinatore in modalita' debug...
echo.
.venv\Scripts\python.exe gui.py
echo.
if errorlevel 1 echo [ERRORE] Il programma e' terminato con un errore.
pause
