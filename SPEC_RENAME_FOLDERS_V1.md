# Spec V1 - Rinomina Prudente Cartelle

## Obiettivo

Permettere ad Agent Ordinatore di proporre nuovi nomi per cartelle esistenti in base ai file contenuti, senza usare il rename come azione automatica nascosta.

La V1 deve essere prudente: analisi, anteprima, selezione manuale e poi esecuzione solo delle cartelle confermate.

## Ambito

- Analizza solo le cartelle selezionate dall'utente.
- Non sposta file.
- Non crea cluster nuovi.
- Non rinomina sottocartelle ricorsivamente.
- Non rinomina cartelle se l'opzione globale e' disattivata.
- Non rinomina cartelle che sembrano progetti o cartelle intenzionali, salvo scelta manuale futura.

## Regole

1. Il rename cartelle e' disattivato di default in configurazione.
2. L'utente puo' abilitarlo dalle Impostazioni.
3. L'analisi produce una preview con cartella attuale, nome suggerito, confidenza, decisione e motivazione breve.
4. Il nome attuale non va ignorato sempre: se e' coerente col contenuto resta, se e' generico puo' essere sostituito, se sembra intenzionale viene preservato.
5. Cartelle che sembrano progetti sono protette per default.
6. Ogni rename reale deve passare da una funzione sicura dedicata.
7. Ogni rename reale deve essere registrato nei log con azione `RENAME_FOLDER`.
8. In caso di conflitto nome, il programma deve creare un nome alternativo sicuro senza sovrascrivere nulla.
9. La CLI resta in dry-run di default e richiede `--execute` per rinominare.
10. La GUI richiede anteprima e checkbox selettiva.

## Euristiche Locali

Nomi deboli o generici:

- `Nuova cartella`
- `New folder`
- `Varie`
- `Misc`
- `Roba`
- `Desktop`
- `Backup`
- `Temp`
- nomi molto brevi o puramente numerici

Marker progetto:

- `.git`
- `package.json`
- `pyproject.toml`
- `requirements.txt`
- `Cargo.toml`
- `go.mod`
- `.sln`
- `.csproj`
- `node_modules`

Se sono presenti marker progetto, la decisione predefinita e' `keep`.

## Prompt AI

Il modello riceve nome corrente, profilo locale del nome, numero file, riepilogo estensioni, campione di file ed eventuali marker progetto.

Il modello restituisce solo JSON:

```json
{
  "action": "rename",
  "suggested_name": "Amministrazione",
  "confidence": 0.86,
  "reason": "Contiene soprattutto fatture, bollette e documenti amministrativi."
}
```

Azioni valide:

- `keep`
- `rename`

## GUI

Aggiungere una tab dedicata: `Rinomina cartelle`.

Funzioni:

- selezione di una cartella madre;
- analisi delle sottocartelle immediate;
- preview selettiva con checkbox;
- esecuzione solo delle righe selezionate;
- stato/progresso;
- voce in Cronologia.

Se l'opzione globale e' disattivata, la tab mostra un messaggio e non esegue rename.

## CLI

Aggiungere comando:

```cmd
python main.py rename-folders "C:\Percorso"
python main.py rename-folders "C:\Percorso" --execute
python main.py rename-folders "C:\Percorso" --include-root
```

Comportamento:

- analizza le sottocartelle immediate;
- dry-run di default;
- con `--execute` rinomina solo le proposte `rename`;
- con `--include-root` include anche la cartella passata.

## Criteri Di Accettazione

- Il rename non parte se `allow_folder_rename` e' falso.
- La GUI permette selezione per singola cartella.
- La CLI mostra preview senza modificare nulla se manca `--execute`.
- I nomi proposti sono sanitizzati.
- I conflitti non sovrascrivono cartelle esistenti.
- Ogni rename riuscito finisce in `moves.log` con `RENAME_FOLDER`.
- README e schema progetto documentano la nuova modalita.
