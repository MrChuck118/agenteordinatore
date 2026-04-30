# Agent Ordinatore

Organizzatore di file basato su Intelligenza Artificiale **locale** (nessun dato esce dal tuo PC).
Funziona offline, rispetta la privacy, gira su Windows.

## Requisiti

- **Windows 10 o 11**
- **Python 3.10, 3.11, 3.12 o 3.13** scaricabile da https://www.python.org/downloads/
  (durante l'installazione spunta la casella **"Add Python to PATH"**)
- **Almeno 4 GB di RAM** (per il modello più leggero)
- **Connessione Internet** solo al primo avvio, per scaricare il modello AI
- *(Opzionale)* **GPU NVIDIA con CUDA 12** per inferenza accelerata

## Installazione in 2 passi

1. **Doppio click su `install.bat`**

   Crea un ambiente Python dedicato e installa tutte le dipendenze.
   Se hai una GPU NVIDIA con CUDA 12, usa automaticamente la wheel accelerata.
   (dura qualche minuto, la prima volta)

2. **Doppio click su `Agent Ordinatore.bat`**

   Avvia l'interfaccia grafica.
   Al primo avvio vai nel tab **Impostazioni** e scarica un modello AI
   (consigliato: *Standard* se hai almeno 6 GB di RAM).

   Opzionale: esegui `crea_collegamento.ps1` da PowerShell per creare un
   collegamento sul Desktop che punta al launcher batch.

## Utilizzo

L'app ha tre modalità principali:

- **Organizza**: scegli una cartella disordinata, l'AI classifica i file
  in sottocartelle (es. `Immagini/Foto`, `Documenti/PDF`, `Codice/Python`, …)
- **Swap**: scegli due cartelle, l'AI sposta i file fuori posto da una all'altra
  in base al loro "tema"
- **Swap multiplo**: scegli due o piu' cartelle, l'AI sceglie per ogni file
  la cartella piu' coerente tra tutte usando un torneo a chunk calibrato sul tier

Le modalità operative hanno **anteprima** (puoi vedere dove verranno spostati i file
prima di confermare) e opzione **Copia** invece di Sposta.

## Cronologia e Log

- Il tab **Cronologia** mostra le ultime operazioni eseguite.
- Tutti gli spostamenti vengono tracciati in `moves.log` (cronologia completa,
  grep-friendly).
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
.venv\Scripts\python.exe main.py organize "C:\Downloads"            :: dry-run
.venv\Scripts\python.exe main.py organize "C:\Downloads" --execute  :: esegui
.venv\Scripts\python.exe main.py swap "C:\A" "C:\B" --execute
.venv\Scripts\python.exe main.py multiswap "C:\A" "C:\B" "C:\C"     :: dry-run
.venv\Scripts\python.exe main.py multiswap "C:\A" "C:\B" "C:\C" --copy --execute
.venv\Scripts\python.exe main.py setup --list
```

## Privacy

- Nessun dato viene inviato a server esterni.
- Il modello AI gira interamente sul tuo PC.
- L'unica richiesta di rete è il download iniziale del modello da HuggingFace.
