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
set BUILD_VENV=.venv-build
set BUILD_PY=%BUILD_VENV%\Scripts\python.exe
set PYTHON_EXE=

if not exist "%BUILD_PY%" (
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

    echo [1/5] Creazione ambiente build isolato...
    echo   Python base:
    echo     !PYTHON_EXE!
    echo   Ambiente:
    echo     %CD%\%BUILD_VENV%
    echo.

    "!PYTHON_EXE!" -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo.
        echo  [ERRORE] Creazione ambiente build fallita.
        echo.
        if not defined NO_PAUSE pause
        exit /b 1
    )
) else (
    echo [1/5] Ambiente build isolato gia' presente:
    echo   %CD%\%BUILD_VENV%
    echo.
)

echo [2/5] Installazione dipendenze pulite...
"%BUILD_PY%" -m pip install --upgrade pip --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [ATTENZIONE] Aggiornamento pip fallito, continuo ugualmente.
)

rem Evita che un vecchio ambiente build trascini dentro PySide6 completo.
"%BUILD_PY%" -m pip uninstall -y PySide6 PySide6-Addons >nul 2>&1

"%BUILD_PY%" -m pip install -r requirements.txt -r build_requirements.txt --quiet --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [ERRORE] Impossibile installare dipendenze runtime/build.
    echo          Controlla connessione Internet o proxy e riprova.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

"%BUILD_PY%" -m pip install "llama-cpp-python>=0.3.0" ^
    --index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" ^
    --extra-index-url "https://pypi.org/simple" ^
    --only-binary=:all: ^
    --quiet ^
    --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [ERRORE] Installazione llama-cpp-python CPU fallita.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

"%BUILD_PY%" -c "from PySide6.QtWidgets import QApplication; from llama_cpp import Llama; import huggingface_hub, platformdirs, psutil" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERRORE] Verifica dipendenze build fallita.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [3/5] Pulizia build precedenti...
if exist "build" rmdir /s /q "build"
if exist "dist\%APP_NAME%" rmdir /s /q "dist\%APP_NAME%"

echo [4/5] Creazione cartella portable con PyInstaller...
"%BUILD_PY%" -m PyInstaller --noconfirm --clean AgentOrdinatore.spec
if errorlevel 1 (
    echo.
    echo  [ERRORE] Build PyInstaller fallita.
    echo          Controlla l'output sopra per il dettaglio.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [5/5] Verifica artefatto...
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
