@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   Build installer Windows - Agent Ordinatore
echo ============================================================
echo.

set APP_NAME=Agent Ordinatore
set DIST_EXE=dist\%APP_NAME%\%APP_NAME%.exe
set ISS_FILE=installer\AgentOrdinatore.iss
set ISCC_EXE=

if not exist "%DIST_EXE%" (
    echo  [ERRORE] Build portable non trovata.
    echo          Esegui prima build_exe.bat.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

for %%I in (ISCC.exe iscc.exe) do (
    if not defined ISCC_EXE (
        for /f "delims=" %%P in ('where %%I 2^>nul') do (
            if not defined ISCC_EXE set ISCC_EXE=%%P
        )
    )
)

if not defined ISCC_EXE if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not defined ISCC_EXE if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe

if not defined ISCC_EXE (
    echo  [ERRORE] Inno Setup 6 non trovato.
    echo.
    echo          Installa Inno Setup da:
    echo          https://jrsoftware.org/isinfo.php
    echo.
    echo          Poi rilancia questo script.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo  Inno Setup:
echo    %ISCC_EXE%
echo.

"%ISCC_EXE%" "%ISS_FILE%"
if errorlevel 1 (
    echo.
    echo  [ERRORE] Creazione installer fallita.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo.
echo ============================================================
echo   Installer creato!
echo.
echo   Output:
echo     %CD%\installer\Output
echo.
echo   Nota: i modelli GGUF non sono inclusi nell'installer.
echo ============================================================
echo.
if not defined NO_PAUSE pause
