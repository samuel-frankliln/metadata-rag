# Metadata RAG — Local LLM Metadata Generator

Generate structured metadata for your datasets using **local LLMs via Ollama**.
No data ever leaves your machine.

## How it works

1. Drop your **CSV/Excel** files (the data to describe) into `data/`
2. Optionally drop **PDF, TXT, or DOCX** reference documents into `data/` too
3. Run `python main.py`
4. Get JSON + Markdown metadata in `output/`

The pipeline embeds your reference documents into a local ChromaDB vector store,
then for each CSV column it retrieves relevant context and asks the LLM to describe it.

## Quick start

```bash
# 1. One-time setup (installs packages + pulls Ollama models)
python setup.py

# 2. Make sure Ollama is running (in a separate terminal)
ollama serve

# 3. Run on the included sample data
python main.py

# 4. Check results
cat output/sample_customers_metadata.json
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- ~4GB disk for llama3 model, ~270MB for nomic-embed-text

## Usage

```bash
python main.py                          # All CSVs in data/
python main.py --file data/mydata.csv   # Single file
python main.py --rebuild                # Re-embed reference docs
python main.py --model mistral          # Use a different LLM
python main.py --no-rag                 # Schema only, no RAG
python main.py --format json            # JSON output only
python main.py --check                  # Verify environment
python main.py --setup                  # Pull Ollama models
```

## Output example

```json
{
  "dataset": "sample_customers.csv",
  "columns": [
    {
      "name": "customer_id",
      "description": "Unique alphanumeric identifier assigned at registration. Primary key.",
      "logical_type": "identifier",
      "nullable": false,
      "example_values": ["C001", "C002", "C003"],
      "business_rules": "Format: C + 3 digits. Never reused.",
      "quality_notes": "None",
      "tags": ["primary_key", "identifier"]
    }
  ]
}
```

## Project structure

```
metadata-rag/
├── data/                  ← your CSV + reference docs go here
├── vectorstore/           ← ChromaDB (auto-created)
├── output/                ← generated metadata (auto-created)
├── ingest.py              ← document loader + chunker
├── schema.py              ← column parser + type inference
├── embedder.py            ← Ollama embeddings + ChromaDB
├── generator.py           ← LLM prompt + JSON parser
├── main.py                ← CLI (run this)
├── setup.py               ← one-time setup script
├── CLAUDE.md              ← context file for Claude Code
└── requirements.txt
```

## Using with Claude Code

This project is set up for use with Claude Code. Open the folder in VS Code,
start Claude Code, and you can ask it to:

- "Add support for Parquet files"
- "Improve the metadata prompt for financial data"
- "Add a --preview flag that shows the schema without calling the LLM"
- "Export metadata to Excel format"
