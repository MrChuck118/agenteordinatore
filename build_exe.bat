@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   Build portable EXE - Agent Ordinatore
echo ============================================================
echo.

set APP_NAME=Agent Ordinatore
set DIST_DIR=dist\%APP_NAME%
set EXE_PATH=%DIST_DIR%\%APP_NAME%.exe
set PYTHON_EXE=

rem Cerca prima installazioni Python utente comuni, poi PATH/launcher.
for %%V in (313 312 311 310) do (
    if not defined PYTHON_EXE (
        if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
            set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python%%V\python.exe"
        )
    )
)

if not defined PYTHON_EXE (
    for %%P in (python py) do (
        if not defined PYTHON_EXE (
            %%P --version >nul 2>&1
            if not errorlevel 1 set "PYTHON_EXE=%%P"
        )
    )
)

if not defined PYTHON_EXE (
    echo  [ERRORE] Python non trovato.
    echo          Installa Python 3.10+ o esegui install.bat.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo  Python:
echo    %PYTHON_EXE%
echo.

"%PYTHON_EXE%" -c "import PySide6, llama_cpp" >nul 2>&1
if errorlevel 1 (
    echo  [ERRORE] Dipendenze runtime mancanti.
    echo          Esegui install.bat, poi rilancia build_exe.bat.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [1/4] Installazione strumenti di build...
"%PYTHON_EXE%" -m pip install --user -r build_requirements.txt --quiet --no-warn-script-location
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
