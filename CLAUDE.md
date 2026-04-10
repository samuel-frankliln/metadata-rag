# metadata-rag — Local RAG Metadata Generator

## Project purpose
Generate structured metadata for CSV/Excel datasets using:
- Local LLMs via Ollama (no data leaves the machine)
- RAG over reference documents (PDF, TXT, DOCX) in data/
- ChromaDB as the vector store
- nomic-embed-text for embeddings

## Stack
- Python 3.10+
- LangChain + langchain-ollama + langchain-community
- ChromaDB (local persistence in vectorstore/)
- Ollama (must be running on localhost:11434)
- Rich + Typer for CLI

## Commands
```bash
python main.py                        # Process all CSVs in data/
python main.py --file data/x.csv      # Single file
python main.py --rebuild              # Force re-embed docs
python main.py --model mistral        # Different model
python main.py --no-rag               # Schema only, no RAG
python main.py --format json          # JSON output only
python main.py --setup                # Pull Ollama models
python main.py --check                # Check environment
```

## File structure
```
data/          ← user drops CSV, Excel, PDF, TXT, DOCX here
vectorstore/   ← ChromaDB auto-created here
output/        ← generated metadata JSON + Markdown
ingest.py      ← document loading + chunking
schema.py      ← column name + sample value parser
embedder.py    ← Ollama embeddings + ChromaDB
generator.py   ← LLM prompt + JSON output
main.py        ← CLI orchestrator (Typer)
```

## Key design decisions
- All LLM and embedding calls go through Ollama — no OpenAI or external APIs
- Privacy-first: no data sent outside localhost
- generator.py uses temperature=0.1 for consistent metadata output
- schema.py infers logical types (identifier, datetime, currency, etc.)
- Output saved as both JSON and Markdown by default

## Models
- Default LLM: llama3
- Embedding: nomic-embed-text
- Alternatives: mistral, llama3:70b, phi3

## Common issues
- "Ollama not running": run `ollama serve` in a separate terminal
- "Model not found": run `python main.py --setup`
- "No JSON in output": model too small; try llama3 or mistral
- Slow first run: normal — Ollama loads model into memory on first call

## When modifying prompts
The main prompt is in generator.py → METADATA_PROMPT_TEMPLATE.
Keep the JSON schema structure intact. Add few-shot examples above
the schema block for better quality on specific domains.
