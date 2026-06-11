# Packaging Windows

Questo progetto supporta una distribuzione Windows in 3 livelli:

1. build portable con PyInstaller `onedir`;
2. installer Windows con Inno Setup;
3. modelli GGUF esterni al pacchetto, scaricati dall'app in `%LOCALAPPDATA%`.

## Prerequisiti build

- Windows 10 o 11.
- Python compatibile installato sul PC di build.
- Connessione Internet al primo build per installare le dipendenze in `.venv-build`.
- Inno Setup 6 solo se vuoi creare anche l'installer `.exe`.

Nota: `build_exe.bat` crea e usa un ambiente isolato `.venv-build`. Non usa il
Python utente per PyInstaller, cosi' evita di includere pacchetti estranei
installati globalmente.

## 1. Build portable

Esegui:

```cmd
build_exe.bat
```

Output:

```text
dist/
  Agent Ordinatore/
    Agent Ordinatore.exe
    _internal/
    ...
```

Questa cartella e' portable: puoi copiarla su un altro PC Windows compatibile e avviare `Agent Ordinatore.exe`.

Per usare DeepSeek API nella portable, copia `.env.example` accanto a
`Agent Ordinatore.exe`, rinominalo in `.env` e inserisci `DEEPSEEK_API_KEY`.
In alternativa inserisci la chiave dal tab Impostazioni.

La build portable usa `PySide6-Essentials` e una lista di exclude PyInstaller per
tenere fuori librerie non usate come `django`, `pandas`, `scipy`, `pyarrow`,
`boto3`, `botocore`, `fastapi`, `starlette`, `torch`, `tensorflow` e Qt WebEngine.

## 2. Installer Windows

Installa Inno Setup 6, poi esegui:

```cmd
build_installer.bat
```

Output:

```text
installer/
  Output/
    AgentOrdinatore_Setup_1.0.0.exe
```

L'installer crea collegamenti nel menu Start e puo' creare un collegamento Desktop opzionale.

## 3. Build completa

Per generare prima la cartella portable e poi l'installer:

```cmd
build_release.bat
```

## Modelli AI

I file `.gguf` non vengono inclusi in `dist/` ne' nell'installer. Restano gestiti dall'app:

```text
%LOCALAPPDATA%\AgentOrdinatore\models
```

Questo evita pacchetti enormi e permette di scaricare solo il tier scelto dall'utente.

DeepSeek API non richiede modelli locali ma richiede una API key configurata in
locale. Il modello default e' Flash con fallback automatico a Pro per problemi
recuperabili. Non distribuire `.env` con chiavi personali.

## Note

- Usa PyInstaller in modalita' `onedir`, non `onefile`, per ridurre falsi positivi antivirus e tempi di avvio.
- Non cancellare `.venv-build` se vuoi rebuild piu' rapidi; puoi eliminarla manualmente solo per forzare una build da ambiente nuovo.
- Non distribuire `history.json`, log, cache HuggingFace o modelli scaricati.
- Per un rilascio pubblico conviene firmare sia `Agent Ordinatore.exe` sia l'installer.
