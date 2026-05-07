# Guida build Windows - Agent Ordinatore

Questo file serve come promemoria passo passo per riprendere il lavoro su un altro PC
o per dare contesto a un'altra chat.

## Obiettivo

Creare una distribuzione Windows professionale di Agent Ordinatore:

1. cartella portable con `Agent Ordinatore.exe`;
2. installer Windows sopra quella cartella;
3. modelli AI `.gguf` lasciati fuori dal pacchetto.

I modelli restano gestiti dall'app e vengono scaricati in:

```text
%LOCALAPPDATA%\AgentOrdinatore\models
```

## Stato attuale del progetto

Sono stati aggiunti questi file:

```text
AgentOrdinatore.spec
build_requirements.txt
build_exe.bat
build_installer.bat
build_release.bat
PACKAGING.md
installer\AgentOrdinatore.iss
GUIDA_BUILD_WINDOWS.md
```

Sono stati aggiornati anche:

```text
.gitignore
crea_zip_distribuzione.bat
install.bat
```

Nota importante: il progetto non richiede piu' `.venv`. `install.bat` usa il
Python utente installato sul sistema e installa le dipendenze con `pip --user`.

## Prerequisiti sul PC di casa

Sul PC dove vuoi creare EXE e installer ti servono:

- Windows 10 o 11.
- Python 3.10, 3.11, 3.12 o 3.13 installato.
- Durante l'installazione di Python: spuntare `Add Python to PATH`.
- Connessione Internet per installare dipendenze e PyInstaller.
- Inno Setup 6 solo se vuoi generare anche l'installer.

Link Inno Setup:

```text
https://jrsoftware.org/isinfo.php
```

## Passo 1 - Apri la cartella progetto

Vai nella cartella:

```text
C:\Users\user\Desktop\ultimate version\Agente Ordinatore
```

Su un altro PC il path puo' essere diverso. L'importante e' entrare nella cartella
dove si trovano `install.bat`, `gui.py`, `main.py`, `build_exe.bat`.

## Passo 2 - Installa o aggiorna le dipendenze Python

Esegui:

```cmd
install.bat
```

Cosa fa:

- verifica Python;
- installa dipendenze base nel Python utente;
- installa `llama-cpp-python` CPU o CUDA, in base al PC;
- non crea e non richiede `.venv`.

Se questo step fallisce, risolvere prima questo. Senza dipendenze runtime valide
non puoi fare ne' build portable ne' installer.

## Passo 3 - Crea la cartella portable con EXE

Esegui:

```cmd
build_exe.bat
```

Cosa fa:

- installa gli strumenti di build da `build_requirements.txt`;
- usa PyInstaller con `AgentOrdinatore.spec`;
- crea una build `onedir`, non `onefile`;
- include PySide6, llama-cpp-python e dipendenze native;
- non include i modelli `.gguf`.

Output atteso:

```text
dist\Agent Ordinatore\Agent Ordinatore.exe
```

Cartella attesa:

```text
dist\Agent Ordinatore\
```

Questa cartella e' la versione portable. Puoi copiarla su un altro PC Windows
compatibile e lanciare:

```text
Agent Ordinatore.exe
```

## Passo 4 - Testa la versione portable

Dopo `build_exe.bat`, apri:

```text
dist\Agent Ordinatore\Agent Ordinatore.exe
```

Controlla:

- la finestra si apre;
- il tab Impostazioni funziona;
- i log vengono creati in `%LOCALAPPDATA%\AgentOrdinatore\logs`;
- se nessun modello e' scaricato, l'app chiede di scaricarne uno;
- il download modello salva i file in `%LOCALAPPDATA%\AgentOrdinatore\models`.

Non serve includere i modelli nel pacchetto.

## Passo 5 - Installa Inno Setup

Per creare l'installer serve Inno Setup 6.

Scarica e installa:

```text
https://jrsoftware.org/isinfo.php
```

Lo script cerca automaticamente `ISCC.exe` nel PATH o nelle cartelle standard:

```text
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
C:\Program Files\Inno Setup 6\ISCC.exe
```

## Passo 6 - Crea l'installer

Dopo aver creato la cartella portable, esegui:

```cmd
build_installer.bat
```

Output atteso:

```text
installer\Output\AgentOrdinatore_Setup_1.0.0.exe
```

L'installer:

- installa l'app;
- crea collegamento nel menu Start;
- puo' creare collegamento Desktop opzionale;
- crea disinstallazione pulita;
- non include i modelli `.gguf`.

## Passo 7 - Build completa in un solo comando

Quando tutto funziona, puoi fare EXE + installer con:

```cmd
build_release.bat
```

Questo esegue in sequenza:

```cmd
build_exe.bat
build_installer.bat
```

## Cosa distribuire

Se vuoi distribuire solo portable:

```text
dist\Agent Ordinatore\
```

Se vuoi distribuire installer:

```text
installer\Output\AgentOrdinatore_Setup_1.0.0.exe
```

Non distribuire:

```text
build\
history.json
*.log
.cache\
models\
%LOCALAPPDATA%\AgentOrdinatore\models
%LOCALAPPDATA%\AgentOrdinatore\logs
```

## Problemi comuni

### build_exe.bat dice che mancano dipendenze runtime

Esegui:

```cmd
install.bat
```

Poi rilancia:

```cmd
build_exe.bat
```

### build_exe.bat non riesce a installare PyInstaller

Controlla:

- connessione Internet;
- proxy/firewall aziendale;
- Python e pip funzionanti;
- eventuale antivirus che blocca download o esecuzione.

### build_installer.bat dice che Inno Setup non e' trovato

Installa Inno Setup 6:

```text
https://jrsoftware.org/isinfo.php
```

Poi rilancia:

```cmd
build_installer.bat
```

### L'EXE si apre ma il modello non c'e'

E' normale. I modelli non sono inclusi.

Vai in:

```text
Impostazioni -> Download Modello
```

Scarica il tier desiderato.

## Contesto tecnico per altra chat

Il progetto e' una app Python/PySide6 chiamata Agent Ordinatore.
Usa `llama-cpp-python` con modelli GGUF scaricati da HuggingFace.

La strategia scelta e':

- PyInstaller `onedir`, non `onefile`;
- entry point GUI: `gui.py`;
- file spec: `AgentOrdinatore.spec`;
- exe finale: `dist\Agent Ordinatore\Agent Ordinatore.exe`;
- installer: Inno Setup con `installer\AgentOrdinatore.iss`;
- modelli AI esterni al pacchetto in `%LOCALAPPDATA%\AgentOrdinatore\models`.

Motivo per evitare `onefile`:

- app piu' grande;
- avvio piu' lento;
- piu' probabilita' di falsi positivi antivirus;
- PySide6 e librerie native di llama-cpp sono piu' stabili in `onedir`.

Ultimo stato verificato:

- sintassi Python e `.spec` compilano;
- `build_exe.bat` e' pronto;
- `build_installer.bat` e' pronto;
- il flusso corrente usa Python utente senza `.venv`.
