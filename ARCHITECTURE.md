# Technical Architecture — Metadata RAG

## Overview

This project implements a **local agentic RAG pipeline** that generates structured metadata for tabular datasets. Every component runs on-device — no data is sent to external APIs. The system combines schema-aware parsing, semantic retrieval, and LLM-based generation into a single orchestrated workflow.

---

## Agentic Workflow

The pipeline follows a **sense → retrieve → reason → output** pattern. Each stage is a discrete, composable agent step:

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Input                               │
│          CSV/Excel file  +  Reference Documents                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │         Stage 1: SENSE          │
              │                                 │
              │  schema.py — Column Parser      │
              │  • Reads every column           │
              │  • Infers logical type          │
              │  • Extracts samples, stats,     │
              │    null rates, cardinality      │
              │  • Outputs structured           │
              │    schema text                  │
              └────────────────┬────────────────┘
                               │
         ┌─────────────────────▼──────────────────────┐
         │            Stage 2: RETRIEVE               │
         │                                            │
         │  ingest.py → embedder.py                   │
         │  • Loads PDF, TXT, DOCX, CSV docs          │
         │  • Chunks with overlap (600 tok, 80 ol)    │
         │  • Embeds via nomic-embed-text (Ollama)    │
         │  • Persists to ChromaDB                    │
         │  • Retrieves top-k chunks relevant         │
         │    to the schema as query                  │
         └─────────────────────┬──────────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │         Stage 3: REASON         │
              │                                 │
              │  generator.py — LLM Prompt      │
              │  • Combines schema + context    │
              │  • Calls Ollama (llama3/mistral) │
              │  • temperature=0.1 for          │
              │    deterministic output         │
              │  • Robust JSON extraction       │
              │    with Python literal fixes    │
              └────────────────┬────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │         Stage 4: OUTPUT         │
              │                                 │
              │  • JSON per dataset             │
              │  • Markdown table               │
              │  • Streamlit UI cards           │
              │  • Downloadable exports         │
              └─────────────────────────────────┘
```

---

## Module Breakdown

### `schema.py` — Schema Intelligence Agent

The schema parser acts as a **structural understanding agent**. It doesn't just read column names — it builds a rich profile of each column before the LLM ever sees it.

**Logical type inference heuristics:**

| Signal | Inferred type |
|--------|--------------|
| Column name contains `_id`, `uuid`, `key` | `identifier` |
| dtype is `datetime64` or name contains `date`, `time`, `created_at` | `datetime` |
| Name contains `price`, `cost`, `revenue`, `salary` | `currency` |
| dtype is `bool` or 2 unique values in `{true,false,yes,no,0,1}` | `boolean` |
| ≤20 unique values + object/category dtype | `category` |
| dtype is `int64` | `integer` |
| dtype is `float64` | `decimal` |
| object dtype + avg string length > 50 chars | `free_text` |
| object dtype + avg string length ≤ 50 chars | `string` |

**For numeric columns**, it also extracts min, max, mean.  
**For low-cardinality columns** (≤15 unique values), it includes full value frequency counts.

This pre-processing enriches the LLM prompt with signal that the model itself couldn't infer from column names alone.

---

### `ingest.py` — Document Ingestion Agent

Handles multi-format document loading with format-specific strategies:

- **PDF** — page-by-page via `PyPDFLoader`, preserves page metadata
- **TXT** — raw text load with UTF-8 encoding
- **DOCX** — full text extraction via `Docx2txtLoader`
- **CSV** — converted to a **summary document** (not row-by-row). This is intentional: embedding every row would pollute the vector store with data rather than documentation. Instead, a single summary document describes column names, types, and representative samples.

**Chunking strategy:**
```
chunk_size    = 600 tokens
chunk_overlap = 80 tokens
separators    = ["\n\n", "\n", ".", " ", ""]
```

The overlap prevents context loss at chunk boundaries. The separator hierarchy ensures splits happen at natural language boundaries before falling back to character-level splitting.

---

### `embedder.py` — Semantic Memory Agent

Uses **nomic-embed-text** running locally via Ollama for all embeddings. This model produces 768-dimensional vectors and is optimised for retrieval tasks.

**Vector store:** ChromaDB with SQLite backend, persisted to `vectorstore/`. On subsequent runs the store is loaded from disk — re-embedding only happens when `--rebuild` is passed.

**Retrieval:** The schema text (first 600 chars) is used as the query. This means the retriever looks for documentation chunks that are semantically similar to the column descriptions, pulling in relevant business context, data dictionary entries, or domain documentation.

```python
retriever = db.as_retriever(search_kwargs={"k": 5})
```

Top-5 chunks by cosine similarity are returned and concatenated as the RAG context block.

---

### `generator.py` — Reasoning Agent

The LLM generation step with three key design decisions:

**1. Low temperature (0.1)**  
Metadata generation is a deterministic task — we want consistent, factual descriptions, not creative variation. Temperature 0.1 keeps the model focused.

**2. Structured prompt with explicit JSON schema**  
The prompt provides the exact JSON structure the model must output, including field names and allowed enum values for `logical_type`. This reduces hallucination of field names and enforces a consistent schema.

**3. Robust output parsing**  
LLMs frequently wrap JSON in markdown fences or add preamble text. The parser handles this with a four-stage recovery:
1. Strip ` ```json ` fences
2. Trim everything before the first `{` and after the last `}`
3. Fix Python boolean literals (`True`→`true`, `False`→`false`, `None`→`null`)
4. Fix trailing commas (invalid in JSON, common in LLM output)
5. Fallback: return raw output with parse error flag

---

### `main.py` — Orchestrator

The CLI orchestrator manages the full pipeline with state awareness:

- **Vectorstore caching** — checks if `vectorstore/` exists before re-embedding. Saves several minutes on repeat runs against the same document set.
- **Selective targeting** — `--file` flag processes a single dataset without touching the vector store
- **Model switching** — `--model` passes through to the Ollama call, allowing model comparison without code changes
- **RAG bypass** — `--no-rag` skips retrieval entirely, useful for datasets where no reference documents exist

---

### `app.py` — Streamlit UI

The UI wraps the same pipeline with:

- **In-memory temp files** — uploaded files are written to `tempfile.NamedTemporaryFile`, never persisted to disk beyond the session
- **Session state caching** — `st.session_state["metadata"]` persists results across rerenders without re-running the pipeline
- **Live progress bar** — `st.progress()` gives stage-by-stage feedback during the pipeline run
- **Filter + sort** — client-side column filtering by name, type, or description without re-querying the LLM
- **Direct downloads** — `st.download_button` serves JSON and Markdown directly from memory

---

## Data Flow Diagram

```
data/
├── customers.csv        ──► schema.py ──► schema_text (str)
├── data_dictionary.txt  ──┐
├── spec.pdf             ──┼─► ingest.py ──► chunks ──► embedder.py ──► ChromaDB
└── glossary.docx        ──┘                                               │
                                                                           │ top-k retrieval
                                                              schema_text ─┘
                                                                           │
                                                                    context (str)
                                                                           │
                                        schema_text + context ──► generator.py
                                                                           │
                                                                    metadata (dict)
                                                                           │
                                              ┌────────────────────────────┤
                                              ▼                            ▼
                                   output/metadata.json      output/metadata.md
```

---

## Prompt Engineering

The metadata generation prompt is structured in four sections:

```
1. Role definition
   "You are a data catalog assistant..."

2. Input description
   What the model is receiving and why

3. Schema block
   [Injected: column names, types, samples, stats]

4. Context block
   [Injected: RAG-retrieved documentation chunks]

5. Output specification
   Exact JSON schema with field names and type constraints
```

**Key decisions:**
- The JSON schema in the prompt includes a `logical_type` enum — this constrains the model to use one of 9 defined types rather than inventing its own
- The `business_rules` and `quality_notes` fields are explicitly optional (`'None identified'` is a valid value) — this prevents the model from hallucinating rules that don't exist
- The prompt asks for ALL columns in one pass rather than one API call per column — this is more efficient and allows the model to reason about inter-column relationships

---

## Extending the Pipeline

### Add a new file format
In `ingest.py`, add a new branch in `load_documents()`:
```python
elif fpath.suffix.lower() == ".parquet":
    docs.extend(_load_parquet(fpath))
```

### Add a new metadata field
In `generator.py`, add the field to `METADATA_PROMPT_TEMPLATE` JSON schema block. The parser will automatically include it in the output.

### Use a different embedding model
In `embedder.py`, change `EMBED_MODEL`:
```python
EMBED_MODEL = "mxbai-embed-large"  # 1024-dim, higher quality
```
Then run `python main.py --rebuild` to re-embed with the new model.

### Use a different LLM
```powershell
ollama pull mistral
python main.py --model mistral
```
No code changes needed.

---

## Privacy & Security Model

- **No external API calls** — all LLM and embedding inference runs on `localhost:11434` via Ollama
- **No telemetry** — ChromaDB local mode sends no data externally
- **Temp file cleanup** — Streamlit uploads are written to OS temp dir and unlinked after processing
- **ngrok tunnel** — optional, disabled by default. When enabled, only the Streamlit port is exposed. Use `--basic-auth` flag for password protection.

---

## Known Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Python 3.14 incompatibility with Pydantic v1 | Warnings on startup, potential crashes | Use Python 3.11 |
| LLM JSON formatting inconsistency | Occasional parse failures | Parser has 4-stage recovery; re-run or use larger model |
| nomic-embed-text max 8192 tokens | Very long documents truncated at chunk boundary | Reduce `chunk_size` in `ingest.py` |
| ChromaDB SQLite WAL mode | Vectorstore files show as modified in git | Add `vectorstore/` to `.gitignore` |
| Single-threaded pipeline | Large document sets are slow | Run `--no-rag` for quick iterations |
