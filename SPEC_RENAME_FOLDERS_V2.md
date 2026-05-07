# Spec V2 - Normalizzazione Semantica Cartelle

## Obiettivo

Evolvere Agent Ordinatore da semplice rinomina prudente a sistema di normalizzazione delle cartelle: rendere i gruppi di file piu' omogenei possibile e poi nominare le cartelle risultanti.

La V2 e' piu' ambiziosa della V1: puo' proporre spostamenti, creazione di nuove cartelle e rinomina finale.

## Ambito

- Analizza un insieme di cartelle.
- Valuta omogeneita dei contenuti.
- Propone spostamenti/copie tra cartelle.
- Propone nuove cartelle se emerge un gruppo non rappresentato.
- Rinomina le cartelle finali in base al contenuto.
- Mantiene anteprima e conferma utente prima di ogni modifica.

## Differenze Rispetto Alla V1

| Tema | V1 | V2 |
| --- | --- | --- |
| Obiettivo | Rinomina prudente, anche post-swap opzionale | Normalizzazione completa |
| File spostati | Solo nei flussi Swap/MultiSwap gia' esistenti | Si, con piano dedicato |
| Nuove cartelle | No | Si, se utili |
| Ricorsione | No | Possibile, configurabile |
| Rischio | Basso | Medio |
| UI | Tab dedicata + opzione in Swap/MultiSwap | Wizard/preview piu' avanzata |

## Flusso Proposto

1. L'utente seleziona due o piu' cartelle o una cartella madre.
2. Il programma costruisce un profilo per ogni cartella.
3. Il programma misura l'omogeneita dei file.
4. I file fuori posto vengono candidati a spostamento.
5. Se un gruppo di file non ha una cartella coerente, viene proposta una nuova cartella.
6. Il programma suggerisce nomi finali per ogni cartella risultante.
7. L'utente vede una preview completa.
8. L'esecuzione applica solo le azioni selezionate.

## Concetto Di Omogeneita

La V2 dovrebbe combinare piu' segnali:

- estensioni prevalenti;
- parole ricorrenti nei nomi file;
- dimensioni tipiche;
- date o pattern numerici;
- somiglianza tra file e cartelle candidate;
- nome cartella attuale come segnale a peso variabile;
- marker di progetto o cartella intenzionale.

## Protezioni

- Dry-run di default.
- Conferma esplicita.
- Log separati per rename e move/copy tramite `moves.log`.
- Protezione progetti.
- Protezione cartelle con pochi file o contenuto ambiguo.
- Possibilita di bloccare cartelle manualmente.
- Piano di rollback esportabile.

## GUI V2

Probabile wizard:

1. Selezione cartelle.
2. Analisi omogeneita.
3. Preview spostamenti.
4. Preview nomi cartelle.
5. Esecuzione.

Ogni riga deve essere selezionabile e modificabile manualmente.

## CLI V2

Possibili comandi futuri:

```cmd
python main.py normalize "C:\Root"
python main.py normalize "C:\Root" --execute
python main.py normalize "C:\A" "C:\B" "C:\C" --execute
```

## Fuori Ambito Per Ora

- Lettura contenuto interno di PDF/DOCX/immagini.
- Embedding vettoriali.
- Addestramento o fine-tuning.
- Rollback automatico completo.
- Sincronizzazione cloud.

## Criterio Di Passaggio Da V1 A V2

Procedere alla V2 solo dopo che la V1 e' stabile, con:

- rename sicuro verificato;
- log affidabili;
- preview chiara;
- nessuna rinomina indesiderata in cartelle progetto;
- feedback pratico su cartelle reali dell'utente.
