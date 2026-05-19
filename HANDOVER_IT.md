# Documento di Passaggio di Consegne — Italiano
**Progetto:** Sistema di Riepilogo Automatico di Testi Italiani (basato su Ollama)
**Preparato da:** Amir
**Data:** 18 maggio 2026
**Destinatario:** Prossimo Sviluppatore / Manutentore

---

## 1. Di Cosa Si Tratta Questo Progetto

Si tratta di un'**API di riepilogo automatico di testi italiani basata su intelligenza artificiale locale**. Espone un endpoint REST che riceve uno o più documenti in italiano e restituisce riepiloghi compressi a un rapporto di compressione definito dall'utente (es. 30% = il riepilogo è lungo il 30% del testo originale). Il sistema funziona interamente offline grazie a **Ollama** con il modello **LLaMA 3.1** — non sono necessarie chiavi API cloud.

Il sistema è stato progettato per elaborare documenti ufficiali italiani (es. fatture di utenze, testi amministrativi) in modo fedele e sintetico.

---

## 2. Stack Tecnologico

| Livello | Tecnologia |
|---|---|
| Framework API | FastAPI + Uvicorn |
| Inferenza LLM | Ollama (locale) — modello: `llama3.1` |
| Client LLM | libreria Python `ollama` (>= 0.1.6) |
| Validazione Dati | Pydantic v2 |
| HTTP Asincrono | httpx |
| Metriche di Valutazione | `rouge-score`, `bert-score`, `textstat` |
| NLP / NER | spaCy (`it_core_news_md` — italiano) |
| Elaborazione Dati | pandas |
| Containerizzazione | Docker (Python 3.11-slim) |
| Runtime | Python 3.11 |

---

## 3. Struttura del Progetto

```
summarization_ollama/
├── main.py                    # App FastAPI — punto di ingresso
├── config.py                  # Costanti globali (limiti token, timeout)
├── models.py                  # Schema di richiesta Pydantic (SummarizeRequest)
├── metrics.py                 # Tutte le funzioni di valutazione
├── evaluate_batch.py          # CLI: valuta l'API in batch su un corpus di test
├── compare_runs.py            # CLI: confronta due esecuzioni di valutazione
├── whole_code.py              # Versione monolitica legacy — mantenuta come riferimento
├── requirements.txt           # Dipendenze principali runtime
├── requirementsssss.txt       # DA IGNORARE — file duplicato/residuo
├── dockerfile                 # Definizione build Docker
├── package.json               # Config Node minimale (libreria JS openai — attualmente inutilizzata)
├── test_dataset.jsonl         # 5 documenti etichettati per test rapidi
├── long_texts.txt             # Corpus di valutazione (formato DOC_ID: testo)
├── reference_summaries.txt    # Riepiloghi di riferimento umani (gold standard)
│
├── services/
│   ├── summarize.py           # Logica core di riepilogo + pipeline di chunking
│   └── summarize_backup.py    # Vecchia versione sincrona — solo per riferimento
│
├── utils/
│   ├── chunking.py            # split_text_into_chunks() — divide testi lunghi
│   ├── prompts.py             # build_system_prompt() — prompt contestuale italiano
│   └── prompts_backup.py      # Vecchia versione del prompt — solo per riferimento
│
├── examples/
│   ├── summarize_request.json # Esempio di richiesta API (fattura idrica reale)
│   └── Input_JSON.txt         # Ulteriore esempio di formato input
│
└── results/
    └── run_20251009_1234/     # Output di valutazione di esempio
        ├── per_doc.csv        # Metriche per documento
        └── summary_report.json # Statistiche aggregate (media/deviazione standard)
```

> **Nota:** I file denominati `*_backup.py` sono copie legacy/di riferimento. È sicuro mantenerli ma **non devono** essere importati o chiamati dal nuovo codice.

---

## 4. Come Configurare ed Eseguire il Progetto

### Prerequisiti
- Python 3.11+
- [Ollama](https://ollama.com) installato e in esecuzione localmente
- Modello LLaMA 3.1 scaricato: `ollama pull llama3.1`

### Configurazione Locale
```bash
# Entra nella directory del progetto
cd summarization_ollama

# Crea e attiva un ambiente virtuale
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Installa le dipendenze principali
pip install -r requirements.txt

# Scarica il modello spaCy per l'italiano (necessario per le metriche di valutazione)
python -m spacy download it_core_news_md
```

### Avviare il Server API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
L'API sarà disponibile su: `http://localhost:8000`
Documentazione interattiva: `http://localhost:8000/docs`

### Eseguire con Docker
```bash
docker build -t summarizer .
docker run -p 8000:8000 summarizer
```
> **Importante:** Quando si esegue in Docker, Ollama deve comunque girare sulla macchina host. Potrebbe essere necessario modificare l'URL host di Ollama in `config.py` per puntare a `host.docker.internal` (su Mac/Windows) oppure all'IP dell'host (su Linux).

---

## 5. Riferimento API

### `POST /summarize`

**Corpo della richiesta (JSON):**
```json
{
  "docs": {
    "doc1": "Testo italiano completo qui...",
    "doc2": "Un altro documento..."
  },
  "modo": 30,
  "sintesi_aggregata": 0
}
```

| Campo | Tipo | Descrizione |
|---|---|---|
| `docs` | `dict[str, str]` | Mappa ID documento → testo completo |
| `modo` | `int` (1–99) | Rapporto di compressione target (% della lunghezza originale) |
| `sintesi_aggregata` | `int` (0 o 1) | `1` = unisci tutti i documenti in un unico riepilogo aggregato |

**Risposta:** Un dizionario che mappa ogni ID documento al suo riepilogo.

---

## 6. Logica di Riepilogo (Come Funziona)

1. **Controllo dimensione token** — se il documento rientra nei 128K token (finestra di contesto di LLaMA), viene riepilogato in un'unica chiamata.
2. **Chunking** — se troppo grande, il testo viene suddiviso in blocchi da 1000 parole tramite `utils/chunking.py`.
3. **Riepilogo per blocco** — ogni blocco viene riepilogato con lo stesso rapporto `modo`.
4. **Ri-riepilogo** — tutti i riepiloghi dei blocchi vengono concatenati e ri-riepilogati come documento unico.
5. **Applicazione della lunghezza** — l'output viene ridotto frase per frase o parola per parola per rispettare il conteggio target.
6. **Protezione timeout** — viene impostato un allarme OS da 300 secondi intorno a ogni chiamata Ollama.

---

## 7. Valutazione

### Eseguire la Valutazione in Batch
```bash
python evaluate_batch.py \
  --long_texts long_texts.txt \
  --references reference_summaries.txt \
  --modo 30 \
  --outdir results/run_$(date +%Y%m%d_%H%M)
```

Questo chiama l'endpoint `/summarize` per ogni documento in `long_texts.txt`, calcola tutte le metriche rispetto a `reference_summaries.txt` e salva:
- `per_doc.csv` — suddivisione per documento
- `summary_report.json` — media e deviazione standard sull'intero corpus

### Confrontare Due Esecuzioni
```bash
python compare_runs.py results/run_A/summary_report.json results/run_B/summary_report.json
```
Stampa una tabella di delta per verificare se una modifica ha migliorato o peggiorato le metriche.

### Metriche Calcolate

| Metrica | Descrizione |
|---|---|
| Conteggio parole | Originale vs. riepilogo |
| Rapporto di compressione | Raggiunto vs. target |
| Deviazione lunghezza % | Quanto ci si discosta dalla lunghezza target |
| ROUGE-1 / ROUGE-2 / ROUGE-L | Sovrapposizione n-gram con il riferimento |
| BERTScore (P/R/F1) | Similarità semantica (baseline italiana) |
| Indice di leggibilità Flesch | Punteggio di leggibilità |
| Indice SMOG | Livello scolastico di leggibilità |
| Lunghezza media frasi | Indicatore dello stile di scrittura |
| Consistenza entità | Sovrapposizione Jaccard delle entità nominate (NER spaCy) |

> **Nota alla prima esecuzione:** BERTScore scaricherà i pesi del modello italiano da internet la prima volta. È normale.

---

## 8. Configurazione Principale (`config.py`)

| Costante | Default | Descrizione |
|---|---|---|
| `MAX_TOKENS` | 128000 | Dimensione finestra di contesto di LLaMA 3.1 |
| `TOKEN_PER_WORD` | 1.3 | Token stimati per parola italiana |
| `REQUEST_TIMEOUT_SECONDS` | 300 | Tempo massimo per una singola chiamata Ollama |

---

## 9. Cosa È Stato Fatto (Lavoro Completato)

- [x] Servizio REST FastAPI con validazione degli input
- [x] Integrazione Ollama/LLaMA 3.1 per inferenza locale
- [x] Chunking gerarchico per documenti che superano la finestra di contesto
- [x] Applicazione rigida della lunghezza (impacchettamento frasi + ritaglio parole)
- [x] System prompt specifico per l'italiano con vincoli di fedeltà e tono
- [x] Modalità di sintesi aggregata multi-documento (`sintesi_aggregata`)
- [x] Gestione timeout (SIGALRM)
- [x] Suite completa di metriche di valutazione (ROUGE, BERTScore, leggibilità, NER)
- [x] CLI di valutazione in batch asincrona
- [x] Strumento di confronto tra esecuzioni
- [x] Containerizzazione Docker
- [x] Dati di test di esempio (`test_dataset.jsonl`, `long_texts.txt`, `reference_summaries.txt`)
- [x] Esempi di richieste API in `examples/`

---

## 10. Cosa Resta da Fare (Lavoro Futuro)

Queste sono aree identificate ma non ancora implementate:

### Priorità Alta
- [ ] **Autenticazione / Sicurezza API** — L'endpoint `/summarize` è completamente aperto. Aggiungere un header con chiave API o OAuth2 per qualsiasi distribuzione non locale.
- [ ] **Rate limiting** — Non è presente alcun throttling. Sotto carico elevato, le richieste si accodano o vanno in timeout.
- [ ] **Unit test** — Non esistono test automatizzati. Aggiungere almeno test per `chunking.py`, `metrics.py` e il costruttore di prompt.
- [ ] **Docker + Ollama insieme** — Il Dockerfile non include Ollama. Un `docker-compose.yml` che avvii sia il container API che Ollama renderebbe il deployment molto più semplice.

### Priorità Media
- [ ] **Configurabilità del modello** — Il nome del modello Ollama (`llama3.1`) è hardcoded in `services/summarize.py`. Spostarlo in `config.py` permetterebbe di cambiarlo senza toccare la logica del servizio.
- [ ] **Supporto multilingua** — Il sistema è solo in italiano. Astrarre l'impostazione della lingua nei prompt e nel NER permetterebbe l'uso multilingue.
- [ ] **Archiviazione persistente dei risultati** — I risultati di valutazione sono salvati come CSV/JSON locali. Un'integrazione con SQLite o PostgreSQL renderebbe i risultati interrogabili nel tempo.
- [ ] **Risposte in streaming** — Attualmente il riepilogo completo viene restituito tutto in una volta. Lo streaming (SSE o WebSocket) migliorerebbe l'esperienza utente per documenti lunghi.
- [ ] **Versionamento dei prompt** — I file di backup (`*_backup.py`) sono un workaround manuale. Usare un registro di prompt appropriato o almeno versionare le stringhe di prompt in `config.py`.

### Priorità Bassa / Miglioramenti Futuri
- [ ] **Frontend / UI** — `package.json` include la libreria JS `openai` ma non esiste alcun frontend. Una UI web minimale renderebbe lo strumento accessibile agli utenti non tecnici.
- [ ] **Pipeline CI/CD** — Non esistono GitHub Actions o equivalenti. Aggiungere linting (ruff/flake8), testing (pytest) e controlli di build Docker.
- [ ] **Logging strutturato** — Sostituire le istruzioni `print` con logging strutturato (modulo `loguru` o `logging` di Python).
- [ ] **Rimuovere file duplicati** — `requirementsssss.txt` e i file `*_backup.py` dovrebbero essere rimossi una volta che il codebase è stabile.
- [ ] **Valutare altri modelli** — Solo `llama3.1` è stato testato. Sperimentare con `mistral`, `phi3` o modelli multilingue potrebbe dare risultati migliori.

---

## 11. Problemi Noti / Avvertenze

1. **Il timeout basato su signal non funziona in ambienti multi-thread.** `SIGALRM` (usato per il timeout da 300s in `services/summarize.py`) funziona solo su Unix e solo nel thread principale. Se si passa a una configurazione Uvicorn multi-thread o asincrona, sostituirlo con `asyncio.wait_for()`.
2. **Dipendenza internet di BERTScore.** Al primo utilizzo vengono scaricati i pesi del modello italiano. In ambienti air-gapped, scaricare e memorizzare nella cache i pesi manualmente in anticipo.
3. **Il modello spaCy non è in `requirements.txt`.** Eseguire `evaluate_batch.py` senza `it_core_news_md` causerà un crash. Questo passaggio di installazione deve essere documentato o automatizzato.
4. **`requirementsssss.txt` è un residuo** — ignorarlo.
5. **`whole_code.py` usa il client OpenAI che punta a Ollama** (stile API diverso rispetto al codice principale). Non mescolare i due approcci.

---

## 12. Contatti

Lo sviluppatore originale è **Amir**. Per qualsiasi domanda sulle decisioni di progettazione, contattare tramite i canali interni.

In bocca al lupo — l'architettura core è pulita e ben strutturata. La maggior parte del lavoro rimanente riguarda il consolidamento e la messa in produzione.
