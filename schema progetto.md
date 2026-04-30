# Schema Progetto: Agent Ordinatore

## Descrizione Generale

**Agent Ordinatore** e' uno strumento Python per l'organizzazione e la classificazione intelligente dei file. Puo' essere usato sia tramite interfaccia grafica desktop sia da riga di comando.

Il progetto usa esclusivamente **modelli LLM locali** tramite `llama-cpp-python` e pesi GGUF della famiglia **Qwen3.5**. I file analizzati non vengono inviati a servizi esterni: l'applicazione funziona offline dopo il download iniziale del modello da HuggingFace. Il vecchio supporto cloud/API Anthropic e' stato rimosso dal codice sorgente operativo.

Le tre modalita' principali sono:

- **Organizza**: analizza i file presenti in una singola directory e li classifica in sottocartelle logiche, ad esempio `Documenti/PDF`, `Immagini/Foto`, `Codice/Python`.
- **Swap**: confronta due directory e individua i file fuori posto, proponendo lo spostamento o la copia nella cartella piu' coerente.
- **Swap multiplo**: confronta due o piu' directory e sceglie per ogni file la cartella piu' coerente tra tutte, usando un torneo a chunk calibrato sul tier del modello.

L'applicazione e' sviluppata in Python, con UI desktop basata su **PySide6**, inferenza locale tramite **llama-cpp-python**, download modelli tramite **huggingface_hub** e storage dati utente in `%LOCALAPPDATA%\AgentOrdinatore`.

---

## Struttura della Directory

```text
Agente Ordinatore/
|-- .claude/                    # Configurazione locale/tooling AI dell'ambiente di sviluppo
|-- .vscode/                    # Impostazioni locali di Visual Studio Code
|-- installer/
|   `-- AgentOrdinatore.iss     # Script Inno Setup per creare l'installer Windows
|-- .gitignore                  # Esclude venv, build, dist, cache, log, modelli e dati personali
|-- Agent Ordinatore.bat        # Launcher Windows della GUI tramite pythonw.exe
|-- AgentOrdinatore.spec        # Configurazione PyInstaller per build onedir della GUI
|-- avvia_debug.bat             # Launcher debug con console visibile
|-- brain.py                    # Core AI locale: caricamento modello, prompt, parsing risposte e classificazione
|-- build_exe.bat               # Crea la build portable con PyInstaller
|-- build_installer.bat         # Crea l'installer Windows usando Inno Setup
|-- build_release.bat           # Esegue build portable + installer
|-- build_requirements.txt      # Dipendenze usate solo per packaging/build
|-- config.py                   # Preferenze utente in %LOCALAPPDATA%\AgentOrdinatore\config.json
|-- crea_collegamento.ps1       # Script PowerShell per creare collegamenti Windows
|-- crea_zip_distribuzione.bat  # Crea uno ZIP distribuibile del progetto/build
|-- generate_icon.py            # Generatore icone tramite Pillow
|-- gui.py                      # Interfaccia grafica PySide6 con tab Organizza, Swap, Cronologia e Impostazioni
|-- GUIDA_BUILD_WINDOWS.md      # Guida operativa completa per build EXE/installer su Windows
|-- hardware.py                 # Rilevamento CPU/RAM/GPU/VRAM e suggerimento tier modello
|-- history.json                # Cronologia legacy/fallback; la GUI salva in %LOCALAPPDATA%
|-- icon.ico / icon.png         # Asset icona applicazione
|-- install.bat                 # Setup ambiente Python e installazione llama-cpp-python CPU/CUDA
|-- logger.py                   # Logging centralizzato app.log, moves.log e cartella logs
|-- main.py                     # CLI: organize, swap e setup modelli
|-- model_manager.py            # Gestione download/eliminazione modelli GGUF in %LOCALAPPDATA%
|-- PACKAGING.md                # Note sintetiche su packaging portable, installer e modelli esterni
|-- README.md                   # Documentazione utente principale
|-- requirements.txt            # Dipendenze runtime Python, escluso llama-cpp-python
|-- schema progetto.md          # Questo documento
`-- utils.py                    # Scansione file, sanitizzazione categorie, move/copy sicuri e formattazione size
```

Note sulla struttura:

- `.env` non fa piu' parte del progetto operativo. E' solo ignorato da `.gitignore` per sicurezza.
- `.venv/`, `__pycache__/`, `build/`, `dist/`, `installer/Output/`, cache HuggingFace, log e modelli scaricati sono artefatti locali o generati e non vanno considerati sorgente del progetto.
- I modelli `.gguf` non vengono salvati nella cartella progetto: sono gestiti in `%LOCALAPPDATA%\AgentOrdinatore\models`.

---

## Flusso dei Dati e Architettura

### 1. Interazione utente

- **`gui.py`** implementa la GUI desktop con PySide6.
  - Tab principali: Organizza, Swap, Swap multiplo, Cronologia, Impostazioni.
  - Usa worker `QThread` dedicati: `OrganizeAnalyzeWorker`, `OrganizeExecuteWorker`, `SwapAnalyzeWorker`, `SwapExecuteWorker`, `MultiSwapAnalyzeWorker`, `MultiSwapExecuteWorker`, `ModelDownloadWorker`.
  - Usa `Signal` Qt per aggiornare tabelle, progress bar e stato senza bloccare l'interfaccia.
  - Protegge da avvii multipli dello stesso worker e disabilita i pulsanti durante analisi/esecuzione.
  - Supporta anteprima, selezione file tramite checkbox, esecuzione reale, copia invece di spostamento e cronologia operazioni.
  - Reindirizza `stdout`/`stderr` a `libs.log` quando l'app parte con `pythonw.exe`, evitando crash di librerie che scrivono su console assente.
  - Espone il pulsante **Apri cartella log** tramite `QDesktopServices.openUrl()`.
  - All'avvio apre il tab Impostazioni se nessun modello e' scaricato.

- **`main.py`** implementa la CLI.
  - Comandi disponibili: `organize`, `swap`, `multiswap`, `setup`.
  - Modalita' dry-run di default, con `--execute` per applicare le modifiche.
  - Opzione `--copy` per copiare invece di spostare.
  - Opzione `--tier` per scegliere il modello da CLI.
  - Comandi setup: `--download`, `--list`, `--delete`.

### 2. Configurazione e dati applicazione

Le preferenze e i dati generati dall'app sono salvati fuori dal workspace:

```text
%LOCALAPPDATA%\AgentOrdinatore\
|-- config.json
|-- models\
|   `-- *.gguf
`-- logs\
    |-- app.log
    |-- moves.log
    `-- libs.log
```

- **`config.py`**
  - Gestisce `selected_tier`, `theme`, `auto_detect` e `gpu_offload`.
  - Migra eventuale vecchio `settings.json` dal progetto.
  - Scrive su disco solo quando serve aggiungere default, migrare o salvare modifiche.

- **`model_manager.py`**
  - Definisce i tier modello disponibili.
  - Scarica i GGUF da HuggingFace con `hf_hub_download`.
  - Salva i file in `%LOCALAPPDATA%\AgentOrdinatore\models`.
  - Permette controllo, elenco ed eliminazione dei modelli scaricati.

### 3. Core AI locale

- **`brain.py`**
  - Carica il modello selezionato tramite `llama_cpp.Llama`.
  - Usa prompt rigidi per ottenere risposte strutturate:
    - `CLASSIFY_SYSTEM_PROMPT` per categorizzare un file.
    - `SWAP_SYSTEM_PROMPT` per scegliere se un file appartiene alla cartella A o B.
    - `MULTI_SWAP_SYSTEM_PROMPT` per scegliere una cartella vincitrice tra N candidate tramite indice numerico.
  - Definisce `TIER_STRATEGY` con `chunk_size`, `n_ctx` e `sample_files` per adattare contesto e torneo al tier scelto.
  - Per lo Swap multiplo usa `classify_for_multi_swap()`: se le cartelle candidate superano `chunk_size`, divide le opzioni in chunk, seleziona vincitori locali e ricorre fino a un solo vincitore.
  - Nei sample di Swap e Swap multiplo il file target viene escluso dalla cartella di origine per path completo, evitando bias verso "resta dove si trova".
  - Effettua parsing robusto delle risposte:
    - JSON diretto.
    - JSON contenuto in testo sporco.
    - Regex sul campo `category`.
    - parsing numerico con range check per le risposte multi-swap.
    - fallback sicuro.
  - Usa `sanitize_category()` da `utils.py` per trasformare l'output AI in path relativo sicuro.
  - Gestisce GPU offload in base alla VRAM disponibile e all'opzione `gpu_offload`.
  - Espone `unload_model()` per liberare il modello in chiusura GUI.

### 4. Filesystem e sicurezza path

- **`utils.py`**
  - `scan_folder()` elenca solo file diretti della cartella, ignorando sottocartelle e file nascosti che iniziano con `.`.
  - `format_size()` converte byte in formato leggibile.
  - `sanitize_category()` rende sicure le categorie proposte dall'AI:
    - blocca path assoluti Windows/UNC/POSIX e `~`;
    - rimuove `.` e `..`;
    - sostituisce caratteri non validi su Windows;
    - evita nomi riservati come `CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1`;
    - limita la profondita' a 2 livelli;
    - restituisce sempre un path relativo.
  - `move_file()` e `copy_file()` creano la destinazione se serve e gestiscono conflitti aggiungendo timestamp con microsecondi.
  - Ogni move/copy reale viene registrato in `moves.log`.

### 5. Hardware e scelta modello

- **`hardware.py`**
  - Rileva RAM, sistema operativo, CPU e GPU.
  - Usa `nvidia-smi` per GPU NVIDIA e tenta un fallback via `GPUtil` se disponibile.
  - Suggerisce un tier in base a RAM e VRAM.

Tier attuali:

| Tier | Modello | Requisito indicativo | chunk_size | n_ctx |
| --- | --- | --- | --- | --- |
| `lite` | Qwen3.5-0.8B | almeno 4 GB RAM | 2 | 4096 |
| `standard` | Qwen3.5-2B | almeno 6 GB RAM | 4 | 8192 |
| `pro` | Qwen3.5-4B | almeno 8 GB RAM o GPU con almeno 4 GB VRAM | 6 | 8192 |
| `ultra` | Qwen3.5-9B | almeno 16 GB RAM o GPU con almeno 8 GB VRAM; consigliato automaticamente anche su CPU-only con 32 GB+ RAM | 8 | 16384 |

### 6. Logging

- **`logger.py`**
  - `get_app_logger()` scrive eventi generali su `app.log` con rotazione `5 x 1 MB`.
  - `get_moves_logger()` scrive la cronologia completa di move/copy su `moves.log`, senza rotazione.
  - `get_logs_dir()` fornisce alla GUI la cartella log.
  - `set_debug_mode(bool)` abilita/disabilita logging DEBUG sull'app logger.
  - Lo Swap multiplo logga in `app.log` avvio/fine analisi, strategia tier, fallback `n_ctx`, parsing fuori range, avvio/fine esecuzione e dettagli torneo a livello DEBUG. Gli spostamenti reali continuano a finire in `moves.log` tramite `move_file()`/`copy_file()`.

Formato principale:

```text
timestamp | livello | logger | messaggio
timestamp | MOVE|COPY | source -> destination
```

---

## Build, Packaging e Distribuzione

Il progetto ora include una pipeline Windows dedicata.

### Build portable

- **`AgentOrdinatore.spec`**
  - Entry point: `gui.py`.
  - App name: `Agent Ordinatore`.
  - Build PyInstaller in modalita' `onedir`.
  - Include icone e componenti dinamici di `llama_cpp`.
  - Esclude pacchetti non usati come `anthropic`, `jupyter`, `matplotlib`, `pytest`, `tkinter`.

- **`build_exe.bat`**
  - Usa `.venv`.
  - Installa strumenti da `build_requirements.txt`.
  - Produce:

```text
dist\
  Agent Ordinatore\
    Agent Ordinatore.exe
    _internal\
```

### Installer Windows

- **`installer\AgentOrdinatore.iss`**
  - Script Inno Setup 6.
  - Crea installer `AgentOrdinatore_Setup_1.0.0.exe`.
  - Installa la build portable in `Program Files`.
  - Crea collegamento Start Menu e collegamento Desktop opzionale.

- **`build_installer.bat`**
  - Richiede Inno Setup 6 installato.
  - Compila lo script `.iss`.

### Build completa e ZIP

- **`build_release.bat`**
  - Esegue build portable e installer in sequenza.

- **`crea_zip_distribuzione.bat`**
  - Crea un pacchetto ZIP distribuibile, evitando artefatti non necessari.

- **`PACKAGING.md`** e **`GUIDA_BUILD_WINDOWS.md`**
  - Documentano prerequisiti, comandi, output e problemi comuni del packaging Windows.

### Dipendenze

- **`requirements.txt`** contiene le dipendenze runtime principali:
  - `huggingface_hub`
  - `platformdirs`
  - `psutil`
  - `PySide6`
  - `Pillow`

- **`llama-cpp-python`** non e' in `requirements.txt`: viene installato da `install.bat` con wheel precompilata CPU o CUDA.
- **`build_requirements.txt`** contiene solo dipendenze di build:
  - `pyinstaller`
  - `pyinstaller-hooks-contrib`

---

## Responsabilita' dei Moduli

| File | Responsabilita' |
| --- | --- |
| `gui.py` | UI desktop, worker thread, cronologia, impostazioni, download modelli, tema, log folder |
| `main.py` | CLI e orchestrazione comandi `organize`, `swap`, `multiswap`, `setup` |
| `brain.py` | Inferenza locale, prompt, parsing output modello, torneo multi-swap, gestione istanza classificatore |
| `model_manager.py` | Catalogo tier, path modelli, download HuggingFace, delete/list modelli |
| `hardware.py` | Rilevamento hardware e suggerimento tier |
| `config.py` | Preferenze utente e migrazione vecchie impostazioni |
| `utils.py` | Operazioni filesystem sicure, sanitizzazione categorie, move/copy, size formatting |
| `logger.py` | Logger applicazione, logger spostamenti, cartella log e debug mode |
| `generate_icon.py` | Generazione asset icona |
| `AgentOrdinatore.spec` | Configurazione build PyInstaller |
| `installer/AgentOrdinatore.iss` | Configurazione installer Inno Setup |

---

## Stato Attuale

Lo schema e' aggiornato alla struttura corrente del progetto:

- AI solo locale tramite GGUF e `llama-cpp-python`.
- GUI PySide6 con tab Organizza, Swap, Swap multiplo, Cronologia e Impostazioni.
- CLI completa con dry-run, execute, copy, tier, multiswap e setup modelli.
- Storage modelli/config/log in `%LOCALAPPDATA%\AgentOrdinatore`.
- Logging centralizzato con `app.log`, `moves.log`, `libs.log`.
- Sanitizzazione robusta delle categorie AI prima di creare path.
- Pipeline Windows per build portable, installer Inno Setup e ZIP distribuzione.
