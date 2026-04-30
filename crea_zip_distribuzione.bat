@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   Crea pacchetto distribuzione - Agent Ordinatore
echo ============================================================
echo.
echo  Questo script crea un file zip contenente solo i file
echo  necessari per distribuire l'app, escludendo:
echo    - .env (segreti)
echo    - .venv (ambiente Python locale)
echo    - __pycache__, .vscode, .claude
echo    - history.json, log personali, cache modelli
echo.

rem Nome archivio con data
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set DT=%%I
set STAMP=%DT:~0,8%_%DT:~8,6%
set ZIPNAME=AgentOrdinatore_dist_%STAMP%.zip
set ZIPPATH=%~dp0..\%ZIPNAME%

echo  Output: %ZIPPATH%
echo.

rem Lista file/cartelle da INCLUDERE (tutti i path sono relativi)
rem Usiamo PowerShell Compress-Archive per costruire lo zip selettivo
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$items = @(); ^
     Get-ChildItem -File -Name '*.py','*.bat','*.ps1','*.md','*.txt','*.spec','icon.*' -ErrorAction SilentlyContinue | ForEach-Object { $items += $_ }; ^
     if (Test-Path 'installer') { Get-ChildItem -Path 'installer' -File -Filter '*.iss' -ErrorAction SilentlyContinue | ForEach-Object { $items += (Join-Path 'installer' $_.Name) } }; ^
     if ($items.Count -eq 0) { Write-Host '[ERRORE] Nessun file da archiviare trovato.'; exit 1 }; ^
     if (Test-Path '%ZIPPATH%') { Remove-Item '%ZIPPATH%' -Force }; ^
     Compress-Archive -Path $items -DestinationPath '%ZIPPATH%' -CompressionLevel Optimal; ^
     Write-Host ''; ^
     Write-Host '  File inclusi nel pacchetto:'; ^
     $items | ForEach-Object { Write-Host ('    - ' + $_) }; ^
     Write-Host ''; ^
     $size = (Get-Item '%ZIPPATH%').Length / 1MB; ^
     Write-Host ('  Dimensione zip: {0:N2} MB' -f $size)"

if errorlevel 1 (
    echo.
    echo  [ERRORE] Creazione zip fallita.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Pacchetto creato con successo!
echo.
echo   File: %ZIPNAME%
echo   Path: %ZIPPATH%
echo.
echo   Ricorda: chi riceve lo zip deve
echo     1. Estrarlo in una cartella
echo     2. Lanciare install.bat
echo     3. Lanciare "Agent Ordinatore.bat"
echo ============================================================
echo.
pause
