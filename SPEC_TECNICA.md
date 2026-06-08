# Specifica Tecnica - Agent Ordinatore

Ultimo aggiornamento: 2026-06-08

## Scopo

Agent Ordinatore e' un'app desktop Windows per organizzare file e cartelle usando
un modello AI locale in formato GGUF. L'app offre interfaccia grafica PySide6 e
comandi CLI per classificare file, spostare o copiare elementi, scambiare file
tra cartelle e proporre rinomine sicure di cartelle.

Il progetto mantiene i modelli AI fuori dal pacchetto applicativo: l'eseguibile
portable resta scaricabile, mentre i modelli vengono scaricati e salvati nella
cartella dati utente.

## Piattaforma supportata

- Sistema operativo: Windows 10 o Windows 11.
- Runtime sorgente: Python 3.10 o superiore.
- Distribuzione utente finale: cartella portable PyInstaller `onedir` o installer
  Inno Setup, senza installazione manuale di Python.

## Moduli principali

- `gui.py`: interfaccia desktop PySide6, tab operativi, cronologia, impostazioni,
  download modelli e avvio delle operazioni in thread.
- `main.py`: interfaccia CLI con comandi `organize`, `swap`, `multiswap`,
  `rename-folders` e `setup`.
- `brain.py`: prompt, parsing delle risposte del modello, classificazione file,
  swap, multi-swap e suggerimenti di rinomina cartelle.
- `model_manager.py`: catalogo modelli, download da HuggingFace e gestione file
  GGUF locali.
- `hardware.py`: rilevamento RAM, CPU, GPU NVIDIA e scelta tier consigliato.
- `config.py`: configurazione persistente in `%LOCALAPPDATA%`.
- `logger.py`: log applicativi e log movimenti.
- `utils.py`: scansione cartelle, sanitizzazione path, spostamento/copia file,
  profili cartella e rinomina sicura.

## Dipendenze runtime

Dipendenze dirette dichiarate in `requirements.txt`:

- `huggingface_hub`: download modelli GGUF.
- `platformdirs`: percorsi dati utente cross-platform.
- `psutil`: rilevamento memoria e informazioni sistema.
- `PySide6-Essentials`: UI Qt senza il metapacchetto completo PySide6.
- `Pillow`: supporto utility immagine, principalmente per tooling icona.

`llama-cpp-python` viene installato separatamente dagli script per scegliere la
wheel adatta. Nella build portable viene installata la wheel CPU per massima
compatibilita' tra PC Windows.

## Dati persistenti

Percorso dati principale:

```text
%LOCALAPPDATA%\AgentOrdinatore
```

Sottocartelle e file rilevanti:

- `models\`: modelli GGUF scaricati.
- `logs\`: log applicativi e `moves.log`.
- `config.json`: impostazioni utente.
- `history.json`: cronologia operazioni.

I modelli non devono essere inclusi in Git, `dist/` o installer.

## Modelli AI

I tier definiti in `model_manager.py` sono:

- `lite`: Qwen3.5-0.8B, circa 0,5 GB.
- `standard`: Qwen3.5-2B, circa 1,3 GB.
- `pro`: Qwen3.5-4B, circa 2,7 GB.
- `ultra`: Qwen3.5-9B, circa 5,7 GB.

Il modello viene caricato tramite `llama-cpp-python`. Le strategie operative
per chunk, context window e campionamento sono definite in `brain.py`.

## Flussi operativi

### Organizzazione file

1. Scansione della cartella sorgente.
2. Creazione di un profilo file con nome, dimensione ed estensione.
3. Classificazione AI in una categoria sanitizzata.
4. Anteprima dry-run.
5. Esecuzione opzionale con spostamento o copia.

### Swap tra cartelle

1. Scansione di due cartelle.
2. Costruzione profilo per ogni cartella.
3. Classificazione AI di ciascun file verso cartella A o B.
4. Anteprima.
5. Esecuzione opzionale.
6. Rinomina cartelle opzionale se abilitata.

### Multi-swap

1. Scansione di piu' cartelle.
2. Classificazione dei file verso il miglior target tra piu' cartelle.
3. Uso di chunk calibrati sul tier selezionato.
4. Anteprima ed esecuzione opzionale.

### Rinomina cartelle

1. Profilazione delle sottocartelle immediate.
2. Prompt AI per decidere `keep` o `rename`.
3. Sanitizzazione del nome suggerito.
4. Anteprima o esecuzione con gestione conflitti.

## Sicurezza operativa

- Le modalita' principali partono in dry-run.
- I path vengono sanitizzati per bloccare traversal, path assoluti e nomi Windows
  riservati.
- Le cartelle annidate vengono rifiutate nei flussi di swap.
- Le rinomine usano funzioni dedicate con risoluzione conflitti.
- I log tracciano spostamenti, copie e rinomine.

## Privacy

- L'inferenza AI avviene localmente.
- I file dell'utente non vengono inviati a server esterni.
- La rete e' usata per scaricare modelli da HuggingFace.

## Build portable

Script principale:

```cmd
build_exe.bat
```

Comportamento:

1. Crea o riusa `.venv-build`.
2. Installa dipendenze runtime e build dentro `.venv-build`.
3. Installa `llama-cpp-python` CPU.
4. Rimuove eventuale PySide6 completo dall'ambiente build.
5. Esegue PyInstaller con `AgentOrdinatore.spec`.
6. Rigenera `build/` e `dist\Agent Ordinatore\`.

Output:

```text
dist\Agent Ordinatore\Agent Ordinatore.exe
```

La build usa PyInstaller `onedir`, non `onefile`, per ridurre falsi positivi
antivirus, migliorare tempi di avvio e gestire meglio librerie native Qt e
llama.cpp.

## Ottimizzazione peso build

Audit prima dell'ottimizzazione:

- `dist`: circa 416,06 MB.
- `build`: circa 102,58 MB.
- `.venv`: circa 777,82 MB.

Risultato dopo l'ottimizzazione:

- `dist`: circa 142,82 MB.
- `build`: circa 35,27 MB.
- `.venv-build`: circa 361,05 MB, ignorato da Git e non distribuito.

Interventi applicati:

- Build isolata in `.venv-build`.
- Uso di `PySide6-Essentials` invece di `PySide6` completo.
- Rimozione di `collect_submodules("llama_cpp")`.
- Exclude PyInstaller per librerie non usate: `django`, `pandas`, `pyarrow`,
  `boto3`, `botocore`, `fastapi`, `starlette`, `pydantic`, `torch`,
  `tensorflow`, Qt WebEngine e altre.

Nota: `numpy.libs\libscipy_openblas...dll` puo' comparire nel pacchetto. Non e'
il pacchetto SciPy: e' la DLL OpenBLAS distribuita con NumPy.

## Installer

Script:

```cmd
build_installer.bat
```

Requisito:

- Inno Setup 6.

Output:

```text
installer\Output\AgentOrdinatore_Setup_1.0.0.exe
```

## Test e verifiche

Comandi usati per verifica base:

```cmd
.venv-build\Scripts\python.exe -c "from PySide6.QtWidgets import QApplication; from llama_cpp import Llama; import huggingface_hub, platformdirs, psutil; import gui"
.venv-build\Scripts\python.exe main.py --help
.venv-build\Scripts\python.exe -m unittest discover -s tests -v
```

Risultato ultimo controllo:

- Import runtime e GUI: OK.
- CLI help: OK.
- Test automatici: 20 test, tutti OK.

## File da non distribuire

- `.venv\`
- `.venv-build\`
- `build\`
- `history.json`
- `*.log`
- `.cache\`
- `models\`
- `%LOCALAPPDATA%\AgentOrdinatore\models`
- `%LOCALAPPDATA%\AgentOrdinatore\logs`

## Manutenzione

- Mantenere `build_exe.bat` indipendente dal Python utente.
- Se la build torna a crescere, controllare prima `dist\Agent Ordinatore\_internal`
  e `build\AgentOrdinatore\xref-AgentOrdinatore.html`.
- Non aggiungere hidden import larghi se non necessari.
- Preferire dipendenze esplicite e piccole.
- Ricostruire `.venv-build` da zero solo quando serve validare una build pulita.
