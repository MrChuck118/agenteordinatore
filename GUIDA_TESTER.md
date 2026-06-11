# Guida Tester - Agent Ordinatore

## Avvio

1. Estrai lo ZIP in una cartella locale.
2. Apri `Agent Ordinatore.exe`.
3. Vai in `Impostazioni` e scegli il provider AI.

## Provider AI

### Qwen locale

- Scegli `Qwen locale`.
- Scarica un modello dal pannello `Modello AI locale`.
- Consigliato: `Standard` se il PC ha abbastanza RAM.

### DeepSeek API

- Scegli `DeepSeek API`.
- Copia `.env.example` in `.env` accanto a `Agent Ordinatore.exe`.
- Inserisci la tua chiave:

```text
DEEPSEEK_API_KEY=sk...
```

In alternativa, inserisci la chiave nel campo mascherato delle Impostazioni e
premi `Salva chiave`.

## Note privacy

- Con `Qwen locale`, l'analisi resta sul PC.
- Con `DeepSeek API`, l'app invia a DeepSeek nomi file/cartelle e campioni dei
  contenuti necessari alla classificazione.

## Feedback utile

Quando segnali un problema, indica:

- versione ZIP usata;
- provider AI selezionato;
- operazione eseguita (`Organizza`, `Swap`, `Swap multiplo`, `Rinomina cartelle`);
- eventuale messaggio visibile nella barra stato;
- se possibile, allega i log da `%LOCALAPPDATA%\AgentOrdinatore\logs`.
