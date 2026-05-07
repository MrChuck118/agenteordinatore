@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   Installazione senza venv - Agent Ordinatore
echo ============================================================
echo.

echo [1/3] Verifica Python...

set PYTHON_EXE=
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
    echo.
    echo  [ERRORE] Python non trovato nel sistema.
    echo.
    echo  Installa Python 3.10, 3.11, 3.12 o 3.13 da:
    echo    https://www.python.org/downloads/
    echo.
    echo  Consigliato: spunta "Add Python to PATH".
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

for /f "tokens=2" %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do set PY_VERSION=%%v
for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if "!PY_MAJOR!" NEQ "3" (
    echo  [ERRORE] Richiesto Python 3.10 o superiore.
    echo           Versione rilevata: !PY_VERSION!
    if not defined NO_PAUSE pause
    exit /b 1
)
if !PY_MINOR! LSS 10 (
    echo  [ERRORE] Richiesto Python 3.10 o superiore.
    echo           Versione rilevata: !PY_VERSION!
    if not defined NO_PAUSE pause
    exit /b 1
)

echo   OK - Python !PY_VERSION!
echo   %PYTHON_EXE%
echo.

echo [2/3] Installazione dipendenze Python utente...
echo   (questa operazione puo' richiedere alcuni minuti)
echo.

"%PYTHON_EXE%" -m pip install --upgrade pip --user --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [ATTENZIONE] Aggiornamento pip fallito, continuo ugualmente.
)

"%PYTHON_EXE%" -m pip install --user -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [ERRORE] Installazione dipendenze fallita.
    echo           Controlla la connessione Internet e riprova.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)
echo   OK
echo.

echo [3/3] Installazione motore AI (llama-cpp-python)...
echo.

set CUDA_INDEX=cpu
set CUDA_VER=
set GPU_DESC=CPU-only

nvidia-smi >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%L in ('nvidia-smi 2^>nul ^| findstr /i "CUDA Version"') do (
        for /f "tokens=9" %%v in ("%%L") do set CUDA_VER=%%v
    )
    set CUDA_VER=!CUDA_VER:|=!
    set CUDA_VER=!CUDA_VER: =!

    if defined CUDA_VER (
        for /f "tokens=1 delims=." %%m in ("!CUDA_VER!") do set CUDA_MAJOR=%%m
        if "!CUDA_MAJOR!"=="12" (
            set CUDA_INDEX=cu121
            set GPU_DESC=GPU Nvidia con CUDA !CUDA_VER!
        ) else (
            echo   CUDA !CUDA_VER! rilevato ma non supportato dalle wheel scelte. Uso CPU.
        )
    )
) else (
    echo   Nessuna GPU Nvidia rilevata.
)

echo   Modalita' selezionata : !GPU_DESC!
echo   Indice wheel          : https://abetlen.github.io/llama-cpp-python/whl/!CUDA_INDEX!
echo.

"%PYTHON_EXE%" -m pip install --user "llama-cpp-python>=0.3.0" ^
    --index-url "https://abetlen.github.io/llama-cpp-python/whl/!CUDA_INDEX!" ^
    --extra-index-url "https://pypi.org/simple" ^
    --only-binary=:all: ^
    --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [ERRORE] Installazione llama-cpp-python fallita.
    echo.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo.
echo ============================================================
echo   Installazione completata!
echo.
echo   Modalita' installata : !GPU_DESC!
echo.
echo   Per avviare da sorgente:
echo     "Agent Ordinatore.bat"
echo.
echo   Per creare l'EXE:
echo     build_exe.bat
echo ============================================================
echo.
if not defined NO_PAUSE pause
