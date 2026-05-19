# Project Handover Document — English
**Project:** Italian Text Summarization System (Ollama-based)
**Prepared by:** Amir
**Date:** May 18, 2026
**For:** Next Developer / Maintainer

---

## 1. What This Project Is

This is a **local AI-powered Italian text summarization API**. It exposes a REST endpoint that takes one or more Italian documents and returns compressed summaries at a user-defined compression ratio (e.g., 30% = summary is 30% the length of the original). It runs entirely offline using **Ollama** with the **LLaMA 3.1** model — no cloud API keys required.

The system was designed to process official Italian documents (e.g., utility invoices, administrative texts) faithfully and concisely.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| LLM Inference | Ollama (local) — model: `llama3.1` |
| LLM Client | `ollama` Python library (>= 0.1.6) |
| Data Validation | Pydantic v2 |
| Async HTTP | httpx |
| Evaluation Metrics | `rouge-score`, `bert-score`, `textstat` |
| NLP / NER | spaCy (`it_core_news_md` — Italian) |
| Data Processing | pandas |
| Containerization | Docker (Python 3.11-slim) |
| Runtime | Python 3.11 |

---

## 3. Project Structure

```
summarization_ollama/
├── main.py                    # FastAPI app — entry point
├── config.py                  # Global constants (token limits, timeouts)
├── models.py                  # Pydantic request schema (SummarizeRequest)
├── metrics.py                 # All evaluation metric functions
├── evaluate_batch.py          # CLI: batch-evaluates the API over a test corpus
├── compare_runs.py            # CLI: compares two evaluation run outputs
├── whole_code.py              # Legacy monolithic version — kept as backup reference
├── requirements.txt           # Core runtime dependencies
├── requirementsssss.txt       # IGNORE — duplicate/leftover file
├── dockerfile                 # Docker build definition
├── package.json               # Minimal Node config (openai JS lib — currently unused)
├── test_dataset.jsonl         # 5 labelled documents for quick testing
├── long_texts.txt             # Evaluation corpus (DOC_ID: text format)
├── reference_summaries.txt    # Human reference summaries (gold standard)
│
├── services/
│   ├── summarize.py           # Core summarization logic + chunking pipeline
│   └── summarize_backup.py    # Old synchronous version — for reference only
│
├── utils/
│   ├── chunking.py            # split_text_into_chunks() — splits long texts
│   ├── prompts.py             # build_system_prompt() — Italian context prompt
│   └── prompts_backup.py      # Old prompt version — for reference only
│
├── examples/
│   ├── summarize_request.json # Example API request (real water utility invoice)
│   └── Input_JSON.txt         # Additional input format example
│
└── results/
    └── run_20251009_1234/     # Example evaluation output
        ├── per_doc.csv        # Per-document metric breakdown
        └── summary_report.json # Aggregated mean/std statistics
```

> **Note:** Files named `*_backup.py` are legacy/reference copies. They are safe to keep but should NOT be imported or called by new code.

---

## 4. How to Set Up and Run

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed and running locally
- LLaMA 3.1 pulled: `ollama pull llama3.1`

### Local Setup
```bash
# Clone / enter the project directory
cd summarization_ollama

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install core dependencies
pip install -r requirements.txt

# Download Italian spaCy model (needed for evaluation metrics)
python -m spacy download it_core_news_md
```

### Run the API Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

### Run with Docker
```bash
docker build -t summarizer .
docker run -p 8000:8000 summarizer
```
> **Important:** When running in Docker, Ollama must still run on the host machine. You may need to adjust the Ollama host URL in `config.py` to point to `host.docker.internal` (on Mac/Windows) or the host IP (on Linux).

---

## 5. API Reference

### `POST /summarize`

**Request body (JSON):**
```json
{
  "docs": {
    "doc1": "Full Italian text here...",
    "doc2": "Another document..."
  },
  "modo": 30,
  "sintesi_aggregata": 0
}
```

| Field | Type | Description |
|---|---|---|
| `docs` | `dict[str, str]` | Map of document ID → full text |
| `modo` | `int` (1–99) | Target compression ratio (% of original length) |
| `sintesi_aggregata` | `int` (0 or 1) | `1` = merge all docs into one aggregated summary |

**Response:** A dict mapping each doc ID to its summary string.

---

## 6. Summarization Logic (How It Works)

1. **Token size check** — if the document fits within 128K tokens (LLaMA context window), it's summarized in one pass.
2. **Chunking** — if too large, the text is split into 1000-word chunks using `utils/chunking.py`.
3. **Per-chunk summarization** — each chunk is summarized with the same `modo` ratio.
4. **Re-summarization** — all chunk summaries are concatenated and re-summarized as a whole.
5. **Length enforcement** — the output is trimmed sentence-by-sentence or word-by-word to strictly meet the target word count.
6. **Timeout protection** — a 300-second OS-level signal alarm is set around each Ollama call.

---

## 7. Evaluation

### Run Batch Evaluation
```bash
python evaluate_batch.py \
  --long_texts long_texts.txt \
  --references reference_summaries.txt \
  --modo 30 \
  --outdir results/run_$(date +%Y%m%d_%H%M)
```

This calls the `/summarize` endpoint for each document in `long_texts.txt`, computes all metrics against `reference_summaries.txt`, and saves:
- `per_doc.csv` — row-per-document breakdown
- `summary_report.json` — mean and standard deviation across the corpus

### Compare Two Runs
```bash
python compare_runs.py results/run_A/summary_report.json results/run_B/summary_report.json
```
Prints a delta table so you can see whether a change improved or degraded metrics.

### Metrics Computed

| Metric | Description |
|---|---|
| Word counts | Original vs. summary |
| Compression ratio | Achieved vs. target |
| Length deviation % | How far off the target length |
| ROUGE-1 / ROUGE-2 / ROUGE-L | N-gram overlap with reference |
| BERTScore (P/R/F1) | Semantic similarity (Italian baseline) |
| Flesch reading ease | Readability score |
| SMOG index | Readability grade level |
| Avg sentence length | Writing style indicator |
| Entity consistency | Jaccard overlap of named entities (spaCy NER) |

> **First run note:** BERTScore will download Italian model weights from the internet the first time. This is normal.

---

## 8. Key Configuration (`config.py`)

| Constant | Default | Description |
|---|---|---|
| `MAX_TOKENS` | 128000 | LLaMA 3.1 context window size |
| `TOKEN_PER_WORD` | 1.3 | Estimated tokens per Italian word |
| `REQUEST_TIMEOUT_SECONDS` | 300 | Max time for a single Ollama API call |

---

## 9. What Has Been Done (Completed Work)

- [x] FastAPI REST service with input validation
- [x] Ollama/LLaMA 3.1 integration for local inference
- [x] Hierarchical chunking for documents exceeding the context window
- [x] Hard length enforcement (sentence packing + word trimming)
- [x] Italian-specific system prompt with faithfulness and tone constraints
- [x] Aggregated multi-document synthesis mode (`sintesi_aggregata`)
- [x] Timeout handling (SIGALRM)
- [x] Full evaluation metric suite (ROUGE, BERTScore, readability, NER)
- [x] Async batch evaluation CLI
- [x] Run comparison tool
- [x] Docker containerization
- [x] Sample test data (`test_dataset.jsonl`, `long_texts.txt`, `reference_summaries.txt`)
- [x] Example API requests in `examples/`

---

## 10. What Still Needs to Be Done (Future Work)

These are areas that were identified but not yet implemented:

### High Priority
- [ ] **Authentication / API security** — The `/summarize` endpoint is completely open. Add an API key header or OAuth2 for any non-local deployment.
- [ ] **Rate limiting** — No throttling is in place. Under heavy load, requests will queue or time out.
- [ ] **Unit tests** — No automated tests exist. At minimum, add tests for `chunking.py`, `metrics.py`, and the prompt builder.
- [ ] **Docker + Ollama co-location** — The Dockerfile does not include Ollama. A `docker-compose.yml` that spins up both the API container and Ollama side-by-side would make deployment much easier.

### Medium Priority
- [ ] **Model configurability** — The Ollama model name (`llama3.1`) is hardcoded in `services/summarize.py`. Move it to `config.py` so it can be changed without touching service logic.
- [ ] **Language support** — The system is Italian-only. Abstracting the language setting in prompts and NER would allow multilingual use.
- [ ] **Persistent result storage** — Evaluation results are saved as local CSV/JSON. A simple SQLite or PostgreSQL integration would make results queryable over time.
- [ ] **Streaming responses** — Currently the full summary is returned at once. Streaming (SSE or WebSocket) would improve UX for long documents.
- [ ] **Prompt versioning** — The backup files (`*_backup.py`) are a manual workaround. Use a proper prompt registry or at least version the prompt strings in `config.py`.

### Low Priority / Nice to Have
- [ ] **Frontend / UI** — `package.json` includes the `openai` JS library but no frontend exists. A minimal web UI would make the tool accessible to non-technical users.
- [ ] **CI/CD pipeline** — No GitHub Actions or equivalent. Add linting (ruff/flake8), testing (pytest), and Docker build checks.
- [ ] **Logging** — Replace `print` statements with structured logging (`loguru` or Python `logging` module).
- [ ] **Remove duplicate files** — `requirementsssss.txt`, `*_backup.py` files should be cleaned up once the codebase is stable.
- [ ] **Evaluate other models** — Only `llama3.1` has been tested. Experimenting with `mistral`, `phi3`, or multilingual models could yield better results.

---

## 11. Known Issues / Gotchas

1. **Signal-based timeout doesn't work in threaded environments.** `SIGALRM` (used for the 300s timeout in `services/summarize.py`) only works on Unix and only in the main thread. If you move to a multi-threaded or async Uvicorn config, replace this with `asyncio.wait_for()`.
2. **BERTScore internet dependency.** First use downloads Italian model weights. In air-gapped environments, pre-download and cache the weights manually.
3. **spaCy model not in `requirements.txt`.** Running `evaluate_batch.py` without `it_core_news_md` will crash. This install step must be documented or automated.
4. **`requirementsssss.txt` is a leftover** — ignore it.
5. **`whole_code.py` uses the OpenAI client pointing at Ollama** (different API style from the main code). Do not mix the two approaches.

---

## 12. Contact

The original developer is **Amir**. For any questions about design decisions, reach out through internal channels.

Good luck — the core architecture is clean and well-structured. Most of the remaining work is hardening and productionization.
