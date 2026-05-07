# Guida per Codex / Claude Code

Questo file spiega come riprendere il progetto su un altro PC, configurarlo e
lavorarci senza sporcare il repository. Codex legge automaticamente `AGENTS.md`.
Se usi Claude Code, chiedigli all'inizio della sessione: "leggi AGENTS.md e
segui quelle istruzioni".

## Obiettivo del progetto

Agent Ordinatore e' una app Python/PySide6 per organizzare file con un modello
LLM locale GGUF. Il sorgente e' modificabile nel repository GitHub; il programma
gia' avviabile va distribuito come zip/release separata.

Repository:

```powershell
git clone https://github.com/MrChuck118/agenteordinatore.git
cd agenteordinatore
```

## Setup su un nuovo PC

Per lavorare sul sorgente:

```powershell
install.bat
```

Questo installa le dipendenze nel Python utente, senza `.venv`, e installa
`llama-cpp-python` da wheel precompilata. Python consigliato: 3.10, 3.11 o 3.12.

Avvio app da sorgente:

```powershell
Agent Ordinatore.bat
```

Avvio con console debug:

```powershell
avvia_debug.bat
```

Build portable EXE:

```powershell
build_exe.bat
```

Output atteso:

```text
dist\Agent Ordinatore\Agent Ordinatore.exe
dist\Agent Ordinatore\_internal\
```

## Cosa NON committare

Non aggiungere al repo:

- `.venv/`
- `build/`
- `dist/`
- `history.json`
- `*.log`
- `.cache/`
- `models/`
- file GGUF
- zip/release generati
- config personali o credenziali

Questi file sono gia' esclusi da `.gitignore`. Se un assistente propone di
committarli, fermarsi e correggere.

## Dove stanno dati, modelli e log

L'app non deve salvare dati runtime nella cartella di installazione. Usare sempre
le utility esistenti in `config.py` / `platformdirs`.

Percorso runtime previsto:

```text
%LOCALAPPDATA%\AgentOrdinatore\
```

Qui finiscono config, modelli, log e cronologia utente.

## File principali

- `gui.py`: interfaccia PySide6, tab, worker QThread, cronologia.
- `brain.py`: classificatore locale, prompt, strategie tier, swap/multiswap.
- `main.py`: CLI (`organize`, `swap`, `multiswap`, `setup`).
- `model_manager.py`: download/gestione modelli GGUF.
- `hardware.py`: rilevamento hardware e tier consigliato.
- `utils.py`: scansione cartelle, move/copy sicuri, sanitizzazione categorie.
- `logger.py`: `app.log`, `moves.log`, redirect librerie.
- `schema progetto.md`: schema tecnico del progetto, da tenere aggiornato.
- `README.md`: guida utente breve.

## Regole operative per assistenti

Prima di modificare:

```powershell
git status --short --branch
```

Leggere almeno `README.md`, `schema progetto.md` e i file coinvolti dalla
modifica. Non assumere che la memoria della sessione sia aggiornata.

Quando si cambia comportamento:

- aggiornare anche `schema progetto.md` se cambia architettura, storage, worker,
  CLI, build o flussi principali;
- aggiornare `README.md` se cambia uso utente o comando CLI;
- mantenere `.gitignore` pulito;
- evitare percorsi assoluti locali;
- non salvare mai dentro `.venv` o `Program Files`;
- non mettere token/password in file o prompt.

## Punti delicati del codice

Worker Qt:

- se aggiungi un nuovo `QThread`, registralo in `MainWindow._running_workers()`;
- `closeEvent` deve poter fermare/attendere i worker;
- controllare `isInterruptionRequested()` nei loop lunghi.

Modelli LLM:

- non ricaricare il modello se il tier non cambia;
- usare `init_classifier(tier)` prima delle analisi;
- `TIER_STRATEGY` in `brain.py` controlla `chunk_size`, `n_ctx` e `sample_files`;
- se modifichi `n_ctx`, mantenere fallback sicuro in `_ensure_loaded()`.

Swap / MultiSwap:

- escludere sempre il file target dai sample usando il path completo, non solo il
  nome file;
- cartelle con lo stesso nome vanno disambiguate con path breve quando possibile;
- per nuove funzioni, loggare start/fine/errori in `app.log`;
- spostamenti/copie reali devono passare da `move_file` / `copy_file`, cosi
  finiscono in `moves.log`.

Packaging:

- `AgentOrdinatore.spec` include icone e DLL native di `llama_cpp`;
- l'EXE portable sta in `dist\Agent Ordinatore`;
- i modelli GGUF non vanno inclusi nell'EXE.

## Check consigliati prima di commit/push

Se Python e' disponibile:

```powershell
python -m py_compile brain.py gui.py main.py model_manager.py hardware.py config.py logger.py utils.py
python main.py --help
```

Se hai cambiato packaging:

```powershell
build_exe.bat
```

Smoke test EXE:

```powershell
dist\Agent Ordinatore\Agent Ordinatore.exe
```

Verifica Git:

```powershell
git status --short
git diff --stat
```

## Flusso Git consigliato

Per salvare modifiche:

```powershell
git status --short
git add .
git commit -m "Descrizione breve"
git push
```

Per aggiornare il PC di casa:

```powershell
git pull
```

Se servono file avviabili gia' pronti, usare GitHub Releases e caricare uno zip
del portable o uno zip full con:

```text
sorgente/
programma-portable/
```

Non mettere lo zip o `dist/` nel commit normale.
