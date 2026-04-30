@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   Build portable EXE - Agent Ordinatore
echo ============================================================
echo.

set APP_NAME=Agent Ordinatore
set PYTHON_EXE=.venv\Scripts\python.exe
set DIST_DIR=dist\%APP_NAME%
set EXE_PATH=%DIST_DIR%\%APP_NAME%.exe

if not exist "%PYTHON_EXE%" (
    echo  [ERRORE] Ambiente virtuale non trovato.
    echo          Esegui prima install.bat, poi rilancia questo script.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import sys; sys.exit(0)" >nul 2>&1
if errorlevel 1 (
    echo  [ERRORE] La .venv esistente non e' valida o non e' portabile.
    echo          Esegui install.bat: ora ricrea automaticamente la .venv rotta.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [1/4] Installazione strumenti di build...
"%PYTHON_EXE%" -m pip install -r build_requirements.txt --quiet --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [ERRORE] Impossibile installare PyInstaller.
    echo          Controlla connessione Internet o proxy e riprova.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [2/4] Pulizia build precedenti...
if exist "build" rmdir /s /q "build"
if exist "dist\%APP_NAME%" rmdir /s /q "dist\%APP_NAME%"

echo [3/4] Creazione cartella portable con PyInstaller...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean AgentOrdinatore.spec
if errorlevel 1 (
    echo.
    echo  [ERRORE] Build PyInstaller fallita.
    echo          Controlla l'output sopra per il dettaglio.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [4/4] Verifica artefatto...
if not exist "%EXE_PATH%" (
    echo.
    echo  [ERRORE] EXE non trovato: %EXE_PATH%
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo.
echo ============================================================
echo   Build completata!
echo.
echo   Portable folder:
echo     %CD%\%DIST_DIR%
echo.
echo   Eseguibile:
echo     %CD%\%EXE_PATH%
echo.
echo   Nota: i modelli GGUF non sono inclusi nel pacchetto.
echo         Verranno scaricati dall'app in %%LOCALAPPDATA%%\AgentOrdinatore\models
echo ============================================================
echo.
if not defined NO_PAUSE pause
