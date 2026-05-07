# Packaging Windows

Questo progetto supporta una distribuzione Windows in 3 livelli:

1. build portable con PyInstaller `onedir`;
2. installer Windows con Inno Setup;
3. modelli GGUF esterni al pacchetto, scaricati dall'app in `%LOCALAPPDATA%`.

## Prerequisiti build

- Windows 10 o 11.
- Python compatibile installato sul PC di build.
- Dipendenze installate nel Python utente con `install.bat` senza `.venv`.
- Connessione Internet al primo build per installare `pyinstaller`.
- Inno Setup 6 solo se vuoi creare anche l'installer `.exe`.

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

## Note

- Usa PyInstaller in modalita' `onedir`, non `onefile`, per ridurre falsi positivi antivirus e tempi di avvio.
- Non distribuire `history.json`, log, cache HuggingFace o modelli scaricati.
- Per un rilascio pubblico conviene firmare sia `Agent Ordinatore.exe` sia l'installer.
