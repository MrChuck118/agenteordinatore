# Prompt Log

Diario operativo delle interazioni e delle decisioni prese durante il lavoro sul progetto.

## 2026-06-08 - Audit peso progetto e ottimizzazione build

### Interazione

L'utente ha chiesto inizialmente di verificare se la copia locale del progetto e la repository GitHub `MrChuck118/agenteordinatore` fossero sincronizzate. Il confronto ha confermato che `main` locale e `origin/main` puntano allo stesso commit `01cccbd3be857aedfbd4265cd46047c1112806d4`.

Successivamente l'utente ha chiesto un audit in sola lettura per capire perche' il progetto pesasse circa 700 MB. L'audit ha misurato circa 1.297 MB nella cartella locale, con peso concentrato in `.venv`, `dist` e `build`, mentre i file tracciati da Git pesano circa 305 KB.

L'utente ha poi chiesto come ridurre il peso mantenendo un eseguibile scaricabile e avviabile su PC Windows senza installare Python. La strategia proposta e' stata: build isolata, uso di un ambiente dedicato, riduzione delle dipendenze PyInstaller, esclusione di librerie non usate, valutazione di `PySide6-Essentials`, mantenimento dei modelli GGUF fuori dall'eseguibile.

L'utente ha approvato di procedere e ha aggiunto una nuova regola operativa: da questo momento in avanti il progetto deve contenere un prompt log dettagliato di ogni interazione. Dopo la sistemazione del progetto deve inoltre essere prodotta una specifica tecnica.

### Decisioni operative

- Creare questo file `PROMPT_LOG.md` prima di ogni altra modifica.
- Registrare le richieste dell'utente, il piano, le modifiche applicate, le verifiche e gli esiti.
- Procedere con modifiche di build strettamente mirate.
- Non cancellare modelli o dati utente.
- Rigenerare solo artefatti di build ignorati da Git quando necessario.
- Produrre una specifica tecnica finale del progetto dopo le modifiche.

### Modifiche applicate

- Aggiunto `.venv-build/` a `.gitignore` per ignorare l'ambiente dedicato alla build.
- Modificato `requirements.txt` per usare `PySide6-Essentials` invece del metapacchetto completo `PySide6`.
- Modificato `AgentOrdinatore.spec` per non usare piu' `collect_submodules("llama_cpp")`, aggiungere solo `llama_cpp` come hidden import e bloccare librerie pesanti non usate come `django`, `pandas`, `scipy`, `pyarrow`, `boto3`, `botocore`, `fastapi`, `starlette`, `torch`, `tensorflow` e moduli Qt WebEngine.
- Modificato `build_exe.bat` per creare/usare `.venv-build`, installare li' dipendenze runtime/build pulite, installare `llama-cpp-python` CPU e lanciare PyInstaller dall'ambiente isolato.

### Baseline prima della nuova build

- Cartella progetto locale: circa 1.297 MB.
- `.venv`: circa 777,82 MB.
- `dist`: circa 416,06 MB.
- `build`: circa 102,58 MB.
- File tracciati da Git: circa 305 KB.

### Prima build isolata

La prima esecuzione di `build_exe.bat` e' fallita nella fase di creazione di `.venv-build`. Causa: dentro il blocco `if (...)` del batch, `PYTHON_EXE` veniva letto con `%PYTHON_EXE%` prima che il valore impostato dal ciclo `for` fosse disponibile. Correzione applicata: usare `!PYTHON_EXE!` per echo e comando `python -m venv` dentro il blocco con delayed expansion.

### Build riuscita e verifiche

La seconda esecuzione di `build_exe.bat` e' riuscita. L'ambiente PyInstaller
risultante e' `C:\Users\user\Desktop\ultimate version\Agente Ordinatore\.venv-build`
con Python 3.12.10 e PyInstaller 6.20.0.

Risultati peso:

- `dist`: da circa 416,06 MB a circa 142,82 MB.
- `build`: da circa 102,58 MB a circa 35,27 MB.
- `.venv-build`: circa 361,05 MB, ignorato da Git e non distribuito.

Controlli pacchetto:

- Assenti in `dist`: `pyarrow`, pacchetto `scipy`, `django`, `pandas`, `botocore`, `boto3`, `fastapi`, `starlette`, `pydantic`, `Qt6WebEngineCore.dll`.
- Presente `numpy.libs\libscipy_openblas...dll`: e' la DLL OpenBLAS di NumPy, non il pacchetto SciPy.

Smoke test eseguiti:

- Import runtime e GUI con `.venv-build\Scripts\python.exe`: OK.
- `main.py --help`: OK.
- `python -m unittest discover -s tests -v`: 20 test eseguiti, tutti OK.

Documentazione aggiornata:

- `PACKAGING.md` aggiornato per descrivere `.venv-build` e gli exclude.
- `GUIDA_BUILD_WINDOWS.md` aggiornata per il nuovo flusso build.
- Creata `SPEC_TECNICA.md` con architettura, runtime, packaging, sicurezza, dati persistenti e verifiche.

### Richiesta pubblicazione GitHub

L'utente ha chiesto di eseguire commit e push del progetto per poter scaricare da
casa la versione aggiornata e alleggerita. Piano operativo:

- Verificare stato locale e remoto.
- Includere nel commit solo modifiche al flusso build, documentazione tecnica e
  prompt log.
- Non includere artefatti ignorati come `.venv`, `.venv-build`, `build/` e `dist/`.
- Creare un commit descrittivo e fare push su `origin/main`.

Esito commit:

- Branch: `main`.
- Remoto controllato con `git fetch origin`.
- Divergenza prima del commit: `0 0` tra `HEAD` e `origin/main`.
- File inclusi: `.gitignore`, `AgentOrdinatore.spec`, `GUIDA_BUILD_WINDOWS.md`,
  `PACKAGING.md`, `PROMPT_LOG.md`, `SPEC_TECNICA.md`, `build_exe.bat`,
  `requirements.txt`.
- Messaggio commit: `Optimize portable build size`.
