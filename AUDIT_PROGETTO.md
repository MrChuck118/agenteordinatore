# Audit Progetto - Agent Ordinatore

Data audit: 2026-05-08

Ambito: repository attivo `Agente Ordinatore`. La cartella superiore contiene anche `AgentOrdinatore_full_20260430_180841/` e `AgentOrdinatore_full_20260430_180841.zip`, considerati artefatti/copie di distribuzione e non sorgente attivo.

## Aggiornamento Post-Fix V1

Aggiornamento del 2026-05-08 dopo le fasi 1-4:

- Risolto Finding 1 per l'obiettivo V1: l'output CLI in `main.py` usa marker ASCII e non crasha piu' sui comandi verificati.
- Completati marker V1 mancanti: `utils.py` rileva anche file `.sln` e `.csproj` come marker progetto.
- Risolto Finding 4 per la base V1: aggiunta suite `unittest` in `tests/` con test su sanitizzazione, marker progetto, rename sicuro, dry-run CLI e parser rinomina cartelle.
- Verificata prova reale post-swap: `swap` e `multiswap` hanno prodotto `MOVE` e almeno un `RENAME_FOLDER` in `moves.log`.
- Confermato comportamento prudente: nessuna rinomina parte con `allow_folder_rename=False`; i dry-run restano non distruttivi.

Comandi/verifiche post-fix rilevanti:

- `python main.py --help`
- `python main.py setup`
- `python main.py setup --list`
- `python main.py organize` su cartella vuota temporanea
- `python main.py swap` su cartelle temporanee
- `python main.py multiswap` su cartelle temporanee
- `python main.py rename-folders` con rinomina disabilitata
- `python -m unittest discover -s tests -v`: 14 test passati
- prova reale `swap`/`multiswap` con rinomina post-swap e conferma `RENAME_FOLDER` in `moves.log`

Rimangono fuori dalla chiusura V1 e restano validi per lavoro successivo:

- Finding 2: fallback LLM da rendere esplicitamente "incerti".
- Finding 3: concorrenza del classificatore globale.
- Finding 5: lock/pin dipendenze e verifica integrita' modelli.
- Finding 6: undo/manifest operazioni.
- Finding 7: blocco cartelle parent/child in Swap e MultiSwap.
- Finding 9: normalizzazione line ending definitiva.
- Finding 10: rotazione opzionale di `moves.log`.

## Criterio V1 Chiusa

Stato fase 6: V1 chiusa per i criteri concordati.

| Criterio | Stato | Evidenza |
| --- | --- | --- |
| CLI non crasha piu' | OK | Smoke test `setup`, `setup --list`, `organize`, `swap`, `multiswap`, `rename-folders` completati |
| Marker V1 completi | OK | `.sln` e `.csproj` rilevati da `detect_project_markers()` e coperti da test |
| Test automatici base passano | OK | `python -m unittest discover -s tests -v`: 14 test OK |
| Rinomina post-swap verificata su prova reale | OK | Prove reali `swap`/`multiswap` fase 4 completate |
| Log `RENAME_FOLDER` confermato | OK | `moves.log` contiene rinomine reali post-swap e test controllati |
| Nessuna rinomina parte senza `allow_folder_rename` | OK | `rename-folders` con flag falso termina senza eseguire rename |
| Dry-run resta non distruttivo | OK | Coperto da test CLI e smoke test senza `--execute` |

## Sintesi

Il progetto e' in uno stato buono per un prototipo avanzato: struttura chiara, repo Git pulito, dati runtime fuori dalla cartella progetto, modello locale, dry-run CLI di default, anteprima GUI e sanitizzazione path abbastanza robusta.

Le aree piu' deboli sono:

- Fallback LLM troppo permissivi: se il parsing fallisce, alcune modalita' scelgono una destinazione predefinita invece di fermare il file come "incerto".
- Modello LLM globale usato da piu' worker GUI senza blocco applicativo centrale.
- Mancano CI, lock/pin delle dipendenze e controllo integrita' dei modelli.

Priorita consigliata dopo la chiusura V1: correggere prima i punti 2 e 3 sotto.

## Controlli Eseguiti

Comandi/verifiche eseguite:

- `git status --short --branch`: repo pulito, branch `main...origin/main`.
- `git ls-files`: sorgente tracciato piccolo e ordinato.
- `git ls-files -ci --exclude-standard`: nessun file ignorato tracciato.
- `git count-objects -vH`: repository leggero, circa 182 KiB di oggetti Git.
- `python -m py_compile brain.py gui.py main.py model_manager.py hardware.py config.py logger.py utils.py`: passato con Python 3.12.10.
- `python main.py --help`: passato.
- `python main.py setup --list`: passato, rilevati modelli `lite` e `standard` scaricati.
- `python -m pip check`: passato, nessuna dipendenza rotta.
- `python main.py setup`: fallito con `UnicodeEncodeError`.
- `python main.py organize` su cartella vuota: fallito con `UnicodeEncodeError`.
- `python main.py swap` su due cartelle vuote: fallito con `UnicodeEncodeError`.
- Ricerca test: nessun file test trovato.
- Ricerca tool sicurezza locali: `pip-audit` e `bandit` non installati.
- `git ls-files --eol`: `utils.py` risulta con line ending misti nel working tree.

## Punti Positivi

- Il progetto salva config, modelli e log in `%LOCALAPPDATA%\AgentOrdinatore`, non nella cartella installata.
- `.gitignore` esclude `.venv/`, `build/`, `dist/`, log, modelli e cache.
- Le operazioni reali passano da `move_file`, `copy_file` e `rename_folder_safe`, quindi sono centralizzate e loggate.
- `sanitize_category()` blocca path assoluti, `..`, nomi Windows riservati e limita la profondita.
- CLI in dry-run di default: buona scelta per un programma che sposta file.
- GUI con worker `QThread` evita di bloccare l'interfaccia durante analisi/esecuzione.
- La rinomina cartelle e' disattivata di default e richiede abilitazione esplicita.

## Findings

### 1. Alto - La CLI crasha su Windows per output Unicode - RISOLTO V1

Evidenza:

- `python main.py setup` fallisce a `main.py:635` con `UnicodeEncodeError` sul carattere `U+25CB WHITE CIRCLE`.
- `python main.py organize .\_audit_tmp_empty` fallisce a `main.py:165` sul carattere `U+1F50D LEFT-POINTING MAGNIFYING GLASS`.
- `python main.py swap .\_audit_tmp_a .\_audit_tmp_b` fallisce a `main.py:243` sul carattere `U+1F50D LEFT-POINTING MAGNIFYING GLASS`.

Codice coinvolto:

- `main.py:155`, `main.py:165`, `main.py:186`, `main.py:215`, `main.py:233`, `main.py:243`, `main.py:286`, `main.py:340`, `main.py:635`.

Impatto:

La CLI documentata nel README puo' essere inutilizzabile nella console Windows standard, anche prima di classificare file reali.

Raccomandazione:

- Soluzione rapida: sostituire emoji/simboli non CP1252 in `main.py` con ASCII.
- Soluzione migliore: aggiungere un helper output che usa `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` quando possibile e fallback ASCII quando non possibile.
- Aggiungere test/smoke test CLI su Windows o con `PYTHONIOENCODING` controllato.

Stato post-fix:

- Applicata la soluzione rapida: output CLI convertito a marker ASCII.
- Smoke CLI eseguiti con successo su `setup`, `setup --list`, `organize`, `swap`, `multiswap` e `rename-folders`.

### 2. Alto - Fallback LLM possono produrre spostamenti errati

Evidenza:

- `_parse_swap()` ritorna `"A"` se non riesce a interpretare la risposta del modello (`brain.py:291-292`).
- `_parse_index()` ritorna `0` se l'indice multi-swap non e' valido (`brain.py:342-343`).
- GUI/CLI usano poi questi valori come decisioni normali.

Codice coinvolto:

- `brain.py:281-292`
- `brain.py:294-343`
- `gui.py:709-733`
- `gui.py:848-863`
- `main.py:279-320`
- `main.py:409-436`

Impatto:

Se il modello risponde con testo sporco, vuoto, fuori formato o manipolato dal nome file, un file puo' essere marcato come "resta in A" o "sposta nella prima cartella" senza essere segnalato come incerto.

Raccomandazione:

- Cambiare i parser per restituire uno stato esplicito tipo `None`, `"unknown"` o `{"status": "uncertain"}`.
- In GUI, mostrare la riga come non selezionabile e richiedere conferma manuale.
- In CLI, contare il file come errore/incerto e non spostarlo con `--execute`.

### 3. Alto - Classificatore globale non protetto da concorrenza GUI

Evidenza:

- Il modello e' gestito tramite `_classifier` globale (`brain.py:697-707`).
- Ogni tab controlla solo il proprio worker in avvio analisi (`gui.py:1365`, `gui.py:1800`, `gui.py:2408`, `gui.py:2710`).
- `_running_workers()` viene usato per la chiusura finestra, non per impedire analisi parallele fra tab (`gui.py:3419-3433`).

Impatto:

L'utente puo' avviare analisi da tab diverse mentre condividono lo stesso oggetto Llama globale. Questo puo' causare race condition, crash, risultati incrociati o unload mentre un worker usa ancora il modello.

Raccomandazione:

- Introdurre un lock globale per tutte le chiamate al modello.
- Oppure impedire a livello `MainWindow` l'avvio di una seconda analisi quando esiste gia' un worker AI attivo.
- Evitare `unload_model()` mentre un worker sta usando il modello.

### 4. Medio - Nessun test automatico o CI - PARZIALMENTE RISOLTO V1

Evidenza:

- Nessun file `test*` trovato.
- Nessun `pyproject.toml`, `pytest.ini`, workflow `.github` o configurazione lint/type check.
- Le verifiche attuali sono manuali: `py_compile`, `main.py --help`, `pip check`.

Impatto:

Bug come il crash Unicode CLI o regressioni sui parser LLM possono rientrare facilmente.

Raccomandazione:

Aggiungere almeno:

- Test unitari per `sanitize_category`, `sanitize_folder_name`, `_parse_swap`, `_parse_index`, `_parse_folder_rename`.
- Test CLI che controllino `setup`, `organize` e `swap` senza modello caricato quando le cartelle sono vuote.
- Test filesystem con `tmp_path` per conflitti move/copy/rename.
- Workflow GitHub Actions minimo con compile + test.

Stato post-fix:

- Aggiunta suite `unittest` in `tests/`.
- Verificati 14 test passati con `python -m unittest discover -s tests -v`.
- Resta da aggiungere una CI automatica.

### 5. Medio - Dipendenze e modelli non sono riproducibili

Evidenza:

- `requirements.txt` usa solo lower bound: `huggingface_hub>=0.25.0`, `PySide6>=6.7.0`, ecc.
- `build_requirements.txt` usa versioni ampie.
- `model_manager.py:57-59` considera un modello scaricato se il file esiste.
- `model_manager.py:83-87` scarica da HuggingFace senza revision/hash esplicito.

Impatto:

Una build fatta oggi e una fatta in futuro possono usare librerie o file modello diversi. Un file `.gguf` troncato/corrotto puo' essere considerato valido se esiste.

Raccomandazione:

- Aggiungere `constraints.txt` o lock file per build/rilascio.
- Pin di `llama-cpp-python` compatibile con le wheel scelte.
- Per i modelli, salvare `revision` HuggingFace e controllare almeno dimensione minima/attesa; meglio hash se disponibile.

### 6. Medio - Operazioni filesystem non transazionali e senza undo

Evidenza:

- `move_file()` e `copy_file()` eseguono subito l'operazione (`utils.py:336-383`).
- Worker GUI continuano il batch anche dopo errori per singolo file (`gui.py:655-669`, `gui.py:763-777`, `gui.py:901-918`).
- La CLI fa la stessa cosa nelle modalita operative (`main.py:197`, `main.py:291`, `main.py:320`, `main.py:436`).

Impatto:

Se un batch fallisce a meta, i file gia' spostati restano dove sono. I log aiutano, ma non c'e' un undo automatico o manifest applicabile.

Raccomandazione:

- Generare un manifest operazione prima di eseguire.
- Salvare per ogni operazione source/dest finale e offrire comando/azione "annulla ultima operazione".
- In caso di errore, mostrare chiaramente "parzialmente completato".

### 7. Medio - Validazione cartelle non blocca parent/child overlap

Evidenza:

- Swap CLI blocca solo cartelle identiche (`main.py:788-791`).
- MultiSwap CLI blocca solo duplicati esatti (`main.py:810-821`).
- GUI Swap usa solo confronto esatto (`gui.py:1658-1661`).
- GUI MultiSwap deduplica ma non rifiuta cartelle annidate (`gui.py:2233-2252`).

Impatto:

Se l'utente seleziona una cartella e una sua sottocartella, il comportamento puo' diventare confuso o rischioso: file spostati fra parent e child, sample non rappresentativi, rename post-swap su path correlati.

Raccomandazione:

Rifiutare cartelle in relazione parent/child per Swap e MultiSwap, oppure mostrare un warning forte e richiedere conferma esplicita.

### 8. Basso - Artefatti locali pesanti e `.venv` non coerente

Evidenza:

- Cartelle locali rilevate: `.venv` circa 778 MB, `build` circa 103 MB, `dist` circa 416 MB.
- La `.venv` locale punta a Python 3.12 in `pyvenv.cfg`; in sandbox e' risultata non affidabile, mentre il Python utente 3.12.10 funziona.
- `AGENTS.md` e README indicano setup senza `.venv`.

Impatto:

Non e' un problema Git perche sono ignorati, ma sporca il workspace e puo' confondere chi lavora al progetto.

Raccomandazione:

Eliminare o ricreare `.venv` solo se serve davvero; altrimenti seguire la strategia documentata "senza venv". Pulire `build/` e `dist/` prima di zip o backup sorgente.

### 9. Basso - Line ending misti in `utils.py`

Evidenza:

`git ls-files --eol` segnala:

```text
i/lf    w/mixed attr/text eol=lf       utils.py
```

Impatto:

Non rompe l'esecuzione, ma aumenta rumore nei diff e puo' causare patch meno pulite.

Raccomandazione:

Normalizzare line ending con `git add --renormalize .` o riscrivere `utils.py` in LF coerente.

### 10. Basso - `moves.log` non ruota

Evidenza:

`get_moves_logger()` usa `logging.FileHandler` senza rotazione (`logger.py:75-94`).

Impatto:

Scelta comprensibile per cronologia completa, ma su uso intenso il file puo' crescere indefinitamente e contiene path utente personali.

Raccomandazione:

Valutare rotazione opzionale o esportazione cronologia, mantenendo una finestra ragionevole di log locali.

## Rischi Sicurezza

Nessuna evidenza di segreti hardcoded o token nel sorgente.

Rischi principali:

- Prompt injection tramite nomi file: il modello riceve nomi file non fidati e puo' essere influenzato. Il rischio e' mitigato dalla sanitizzazione path, ma non dalla decisione di destinazione.
- Operazioni distruttive: `--execute` e GUI possono spostare/rinominare file reali. Preview e dry-run aiutano, ma manca undo.
- Download modello da rete: dipende da HuggingFace e da repo/file non pinati a commit/hash.

## Dipendenze

Dipendenze runtime dichiarate:

- `huggingface_hub>=0.25.0`
- `platformdirs>=4.0.0`
- `psutil>=5.9.0`
- `PySide6>=6.7.0`
- `Pillow>=10.0.0`
- `llama-cpp-python` installato separatamente da `install.bat`

Versioni installate rilevate:

- `huggingface_hub==1.14.0`
- `llama_cpp_python==0.3.22`
- `pillow==12.2.0`
- `platformdirs==4.9.6`
- `psutil==7.2.2`
- `pyinstaller==6.20.0`
- `pyinstaller-hooks-contrib==2026.5`
- `PySide6==6.11.0`

`pip check`: nessuna dipendenza rotta.

Nota: non e' stato eseguito un vulnerability audit online perche `pip-audit` e `bandit` non sono installati localmente.

## Piano di Correzione Consigliato

1. Cambiare fallback LLM in stato "incerto" non eseguibile.
2. Introdurre lock globale o busy state applicativo per worker AI.
3. Bloccare cartelle parent/child in Swap e MultiSwap.
4. Aggiungere constraints/lock per dipendenze e revision/hash modelli.
5. Aggiungere CI automatica con compile + test.
6. Normalizzare line ending e pulire artefatti locali.
7. Valutare manifest/undo operazioni.

## Esito Finale

Il progetto e' utilizzabile e ben impostato nella struttura generale. Dopo le fasi 1-4 la V1 della rinomina cartelle ha una base molto piu' solida: CLI senza crash Unicode verificati, marker progetto V1 completi, test automatici base e prova reale di rinomina post-swap confermata nei log.

Non lo considererei ancora "robusto da distribuire a utenti non tecnici" finche non vengono risolti:

- fallback LLM che possono produrre destinazioni predefinite;
- concorrenza del modello globale;
- assenza di CI e riproducibilita' forte di dipendenze/modelli.

Una volta corretti questi punti, la base architetturale e' buona e puo' diventare molto piu' affidabile senza riscrivere il progetto.
