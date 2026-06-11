# Agent Ordinatore

Organizzatore di file basato su Intelligenza Artificiale con backend selezionabile:
**Qwen locale** oppure **DeepSeek API**. Gira su Windows.

## Requisiti

- **Windows 10 o 11**
- **Python 3.10, 3.11, 3.12 o 3.13** scaricabile da https://www.python.org/downloads/
  (durante l'installazione spunta la casella **"Add Python to PATH"**)
- **Almeno 4 GB di RAM** (per il modello più leggero)
- **Connessione Internet** solo per scaricare il modello locale o usare DeepSeek API
- *(Opzionale)* **GPU NVIDIA con CUDA 12** per inferenza accelerata

## Installazione in 2 passi

1. **Doppio click su `install.bat`**

   Installa le dipendenze nel Python utente, senza usare `.venv`.
   Se hai una GPU NVIDIA con CUDA 12, usa automaticamente la wheel accelerata.
   (dura qualche minuto, la prima volta)

2. **Doppio click su `Agent Ordinatore.bat`**

   Avvia l'interfaccia grafica.
   Al primo avvio vai nel tab **Impostazioni** e scegli il provider AI.
   Per Qwen locale scarica un modello AI (consigliato: *Standard* se hai
   almeno 6 GB di RAM). Per DeepSeek API inserisci la chiave nel campo
   mascherato oppure crea un file `.env` partendo da `.env.example`.

   Se la build portable esiste, il launcher apre direttamente l'EXE.

   Opzionale: esegui `build_exe.bat` per creare `dist\Agent Ordinatore\Agent Ordinatore.exe`,
   poi `crea_collegamento.ps1` da PowerShell per creare un collegamento sul Desktop
   con icona.

## Utilizzo

L'app ha quattro modalita' principali:

- **Organizza**: scegli una cartella disordinata, l'AI classifica i file
  in sottocartelle (es. `Immagini/Foto`, `Documenti/PDF`, `Codice/Python`, …)
- **Swap**: scegli due cartelle, l'AI sposta i file fuori posto da una all'altra
  in base al loro "tema"; opzionalmente puo' proporre anche la rinomina finale
  delle due cartelle
- **Swap multiplo**: scegli due o piu' cartelle, l'AI sceglie per ogni file
  la cartella piu' coerente tra tutte usando un torneo a chunk calibrato sul tier;
  opzionalmente puo' proporre la rinomina delle cartelle dopo lo scambio
- **Rinomina cartelle**: analizza le sottocartelle immediate di una cartella madre
  e propone nomi piu' coerenti in base ai file contenuti, con conferma selettiva

Le modalita' operative hanno **anteprima** (puoi vedere dove verranno spostati i file
o rinominate le cartelle prima di confermare) e opzione **Copia** invece di Sposta
dove applicabile. La rinomina cartelle e' disattivata di default: abilitala in
**Impostazioni -> Rinomina cartelle**. In Swap e Swap multiplo resta comunque
una scelta per singola operazione tramite **Proponi rinomina cartelle**.

## Cronologia e Log

- Il tab **Logs** mostra le ultime operazioni eseguite.
- Tutti gli spostamenti, le copie e le rinomine cartelle (`RENAME_FOLDER`) vengono
  tracciati in `moves.log` (cronologia completa, grep-friendly).
- Per aprire la cartella log: **Impostazioni → Apri cartella log**
  (è in `%LOCALAPPDATA%\AgentOrdinatore\logs\`).

## Risoluzione problemi

- **L'app non parte**: lancia `avvia_debug.bat` per vedere l'errore nella console.
- **Download modello bloccato**: chiudi l'app, aspetta 10 secondi, riprova.
  Se persiste, termina eventuali processi `pythonw.exe` dal Task Manager.
- **Errore `NoneType object has no attribute write`** (versioni vecchie):
  aggiorna alla versione più recente, il bug è corretto.

## CLI (uso avanzato)

Per chi preferisce la riga di comando:

```cmd
python main.py organize "C:\Downloads"            :: dry-run
python main.py organize "C:\Downloads" --execute  :: esegui
python main.py swap "C:\A" "C:\B" --execute
python main.py swap "C:\A" "C:\B" --rename-folders
python main.py multiswap "C:\A" "C:\B" "C:\C"     :: dry-run
python main.py multiswap "C:\A" "C:\B" "C:\C" --copy --execute
python main.py multiswap "C:\A" "C:\B" "C:\C" --rename-folders
python main.py rename-folders "C:\Archivio"       :: dry-run
python main.py rename-folders "C:\Archivio" --execute
python main.py setup --list
```

Se nelle Impostazioni hai selezionato DeepSeek API, la CLI usa DeepSeek quando
non passi `--tier`. Se passi `--tier`, il comando forza il modello Qwen locale.

L'output CLI usa marker testuali ASCII come `[INFO]`, `[MOVE]`, `[COPY]` e `[OK]`
per restare compatibile anche con console Windows legacy.

## Test automatici

Per eseguire la verifica base:

```cmd
python -m unittest discover -s tests -v
```

I test coprono sanitizzazione path, marker progetto, rinomina cartelle sicura,
dry-run non distruttivo e parser base della rinomina cartelle.

## Privacy

- Con **Qwen locale**, il modello AI gira interamente sul tuo PC.
- Con **DeepSeek API**, l'app invia a DeepSeek i nomi file/cartelle e i campioni
  necessari alla classificazione.
- Non committare `.env`: usa `.env.example` come modello e inserisci la chiave a mano.
