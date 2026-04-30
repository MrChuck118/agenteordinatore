@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   Installazione - Agent Ordinatore
echo ============================================================
echo.

rem ============================================================
rem  STEP 1 - Trova Python (3.10 / 3.11 / 3.12)
rem ============================================================
echo [1/4] Verifica Python...

set PYTHON_CMD=
for %%P in (python py) do (
    if not defined PYTHON_CMD (
        %%P --version >nul 2>&1
        if not errorlevel 1 set PYTHON_CMD=%%P
    )
)

if not defined PYTHON_CMD (
    echo.
    echo  [ERRORE] Python non trovato nel sistema.
    echo.
    echo  Installa Python 3.10, 3.11 o 3.12 scaricandolo da:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANTE: durante l'installazione spunta l'opzione
    echo    "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('!PYTHON_CMD! --version 2^>^&1') do set PY_VERSION=%%v
for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if "!PY_MAJOR!" NEQ "3" (
    echo  [ERRORE] Richiesto Python 3.10 o superiore.
    echo           Versione rilevata: !PY_VERSION!
    pause
    exit /b 1
)
if !PY_MINOR! LSS 10 (
    echo  [ERRORE] Richiesto Python 3.10 o superiore.
    echo           Versione rilevata: !PY_VERSION!
    pause
    exit /b 1
)
if !PY_MINOR! GTR 13 (
    echo  [ATTENZIONE] Python !PY_VERSION! non e' stato ancora testato.
    echo               Continuo al rischio di incompatibilita' delle wheel.
)

echo   OK - Python !PY_VERSION!
echo.

rem ============================================================
rem  STEP 2 - Crea / verifica ambiente virtuale (.venv)
rem ============================================================
echo [2/4] Configurazione ambiente virtuale...

set VENV_OK=0
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 set VENV_OK=1
)

if "!VENV_OK!"=="0" (
    if exist ".venv" (
        echo   Venv esistente non valido o non portabile, lo ricreo...
        rmdir /s /q ".venv"
        if exist ".venv" (
            echo.
            echo  [ERRORE] Impossibile rimuovere la vecchia .venv.
            echo           Chiudi eventuali finestre o processi Python e riprova.
            pause
            exit /b 1
        )
    )
    echo   Creazione venv in corso...
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 (
        echo.
        echo  [ERRORE] Impossibile creare il venv.
        echo           Assicurati che Python sia installato correttamente.
        pause
        exit /b 1
    )
    echo   Venv creato.
) else (
    echo   Venv esistente valido trovato, lo utilizzo.
)
echo   OK
echo.

rem ============================================================
rem  STEP 3 - Dipendenze base (requirements.txt)
rem ============================================================
echo [3/4] Installazione dipendenze...
echo   (questa operazione puo' richiedere alcuni minuti)
echo.

.venv\Scripts\python.exe -m pip install --upgrade pip --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [ATTENZIONE] Aggiornamento pip fallito, continuo ugualmente.
)

.venv\Scripts\pip.exe install -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [ERRORE] Installazione dipendenze fallita.
    echo           Controlla la connessione Internet e riprova.
    pause
    exit /b 1
)
echo   OK
echo.

rem ============================================================
rem  STEP 4 - llama-cpp-python (wheel precompilata, nessun C++)
rem ============================================================
echo [4/4] Installazione motore AI (llama-cpp-python)...
echo.

rem -- Rileva GPU Nvidia via nvidia-smi --------------------------
set CUDA_INDEX=cpu
set CUDA_VER=
set GPU_DESC=CPU-only

nvidia-smi >nul 2>&1
if not errorlevel 1 (
    rem nvidia-smi trovato: leggi la riga "CUDA Version"
    for /f "tokens=*" %%L in ('nvidia-smi 2^>nul ^| findstr /i "CUDA Version"') do (
        for /f "tokens=9" %%v in ("%%L") do set CUDA_VER=%%v
    )
    rem Rimuove eventuali caratteri spurii (pipe | e spazi)
    set CUDA_VER=!CUDA_VER:|=!
    set CUDA_VER=!CUDA_VER: =!

    if defined CUDA_VER (
        for /f "tokens=1 delims=." %%m in ("!CUDA_VER!") do set CUDA_MAJOR=%%m
        if "!CUDA_MAJOR!"=="12" (
            set CUDA_INDEX=cu121
            set GPU_DESC=GPU Nvidia con CUDA !CUDA_VER!
        ) else if "!CUDA_MAJOR!"=="11" (
            echo   CUDA !CUDA_VER! rilevato: versione non supportata dalle wheel.
            echo   Installazione in modalita' CPU.
        ) else (
            echo   Versione CUDA !CUDA_VER! non riconosciuta. Uso CPU.
        )
    ) else (
        echo   GPU Nvidia rilevata ma versione CUDA non determinabile.
        echo   Installazione in modalita' CPU.
    )
) else (
    echo   Nessuna GPU Nvidia rilevata.
)

echo   Modalita' selezionata : !GPU_DESC!
echo   Indice wheel          : https://abetlen.github.io/llama-cpp-python/whl/!CUDA_INDEX!
echo.

.venv\Scripts\pip.exe install "llama-cpp-python>=0.3.0" ^
    --index-url "https://abetlen.github.io/llama-cpp-python/whl/!CUDA_INDEX!" ^
    --extra-index-url "https://pypi.org/simple" ^
    --only-binary=:all: ^
    --no-warn-script-location
set EXIT_CODE=!ERRORLEVEL!
if !EXIT_CODE! NEQ 0 (
    echo  [ERRORE] Installazione llama-cpp-python fallita.
    pause
    exit /b 1
)

echo   OK
echo.

rem ============================================================
rem  COMPLETATO
rem ============================================================
echo ============================================================
echo   Installazione completata con successo!
echo.
echo   Modalita' installata : !GPU_DESC!
echo.
echo   Per avviare Agent Ordinatore fai doppio click su:
echo     "Agent Ordinatore.bat"
echo ============================================================
echo.
pause
