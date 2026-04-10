# 🗂️ Metadata RAG — Local LLM Metadata Generator

Generate structured metadata for your datasets using **local LLMs via Ollama**.
No data ever leaves your machine.

---

## What it does

- Upload a **CSV or Excel** file
- Optionally upload **PDF, TXT, or DOCX** reference documents for richer context
- A local LLM (via Ollama) reads the column names, types, and sample values
- RAG retrieves relevant context from your reference documents
- Outputs structured metadata per column: description, type, examples, business rules, quality notes
- Export results as **JSON** or **Markdown**

---

## Quick Start

### 1. Install prerequisites

**Python 3.11** (recommended — 3.14 has compatibility issues with some dependencies):
- Download from https://python.org/downloads/release/python-3119/
- ✅ Check **"Add python.exe to PATH"** during install

**Ollama:**
- Download from https://ollama.com
- Install and launch the Ollama desktop app
- Click **Launch** in the sidebar to start the server

**Node.js** (for Claude Code):
- Download LTS from https://nodejs.org

**Claude Code:**
```powershell
winget install Anthropic.ClaudeCode
```

---

### 2. Clone the repo

```powershell
git clone https://github.com/samuel-frankliln/metadata-rag.git
cd metadata-rag
```

---

### 3. Set up Python environment

```powershell
# Create virtual environment with Python 3.11
py -3.11 -m venv venv

# Activate it
venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt
```

---

### 4. Pull Ollama models

Make sure Ollama is running, then in a terminal:

```powershell
ollama pull llama3
ollama pull nomic-embed-text
```

- `llama3` (~4GB) — the LLM that generates metadata
- `nomic-embed-text` (~270MB) — the embedding model for RAG

---

### 5. Run the Streamlit app

**Terminal 1 — Ollama server:**
```powershell
ollama serve
```

**Terminal 2 — Streamlit app:**
```powershell
python -m streamlit run app.py
```

Open your browser at: **http://localhost:8501**

---

## Using the app

1. Upload your CSV or Excel file in the main area
2. Optionally upload reference documents (PDF, TXT, DOCX) in the sidebar
3. Choose your model and settings in the sidebar
4. Click **⚡ Generate Metadata**
5. Review the column cards with descriptions, types, and quality notes
6. Download results as JSON or Markdown

---

## Accessing from other devices (ngrok tunnel)

You can expose your local app to any device using ngrok.

### Install ngrok

```powershell
winget install ngrok.ngrok
```

Or download from https://ngrok.com/download and place `ngrok.exe` in a folder.

### Connect your ngrok account

Sign up at https://ngrok.com, get your auth token from the dashboard, then:

```powershell
& "C:\Users\YOUR_USERNAME\AppData\Local\Microsoft\WindowsApps\ngrok.exe" config add-authtoken YOUR_TOKEN
```

### Start the tunnel

Make sure Streamlit is already running, then open a third terminal:

```powershell
& "C:\Users\YOUR_USERNAME\AppData\Local\Microsoft\WindowsApps\ngrok.exe" http 8501
```

You will see a forwarding URL like:
```
Forwarding    https://XXXXXXXX.ngrok-free.app -> http://localhost:8501
```

Open that URL in any browser on any device. **Keep all three terminals running** (Ollama, Streamlit, ngrok).

### Add password protection (recommended)

```powershell
& "C:\Users\YOUR_USERNAME\AppData\Local\Microsoft\WindowsApps\ngrok.exe" http 8501 --basic-auth="yourusername:yourpassword"
```

---

## CLI usage (without UI)

```powershell
python main.py                          # All CSVs in data/
python main.py --file data/mydata.csv   # Single file
python main.py --rebuild                # Re-embed reference docs
python main.py --model mistral          # Use a different LLM
python main.py --no-rag                 # Schema only, no RAG
python main.py --format json            # JSON output only
python main.py --check                  # Verify environment
python main.py --setup                  # Pull Ollama models
```

---

## Output example

```json
{
  "dataset": "customers.csv",
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

---

## Project structure

```
metadata-rag/
├── app.py                 ← Streamlit UI (run this)
├── main.py                ← CLI orchestrator
├── ingest.py              ← document loader + chunker
├── schema.py              ← column parser + type inference
├── embedder.py            ← Ollama embeddings + ChromaDB
├── generator.py           ← LLM prompt + JSON parser
├── setup.py               ← one-time setup script
├── requirements.txt
├── CLAUDE.md              ← context file for Claude Code
├── data/                  ← drop your CSV + reference docs here
├── vectorstore/           ← ChromaDB (auto-created)
└── output/                ← generated metadata (auto-created)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Install Python 3.11, check "Add to PATH" |
| `streamlit` not recognized | Use `python -m streamlit run app.py` |
| Ollama not running | Open Ollama app and click Launch, or run `ollama serve` |
| Model not found | Run `ollama pull llama3` and `ollama pull nomic-embed-text` |
| JSON parse error | Re-run — LLM output varies. Try `--model mistral` for better results |
| ngrok endpoint offline | You opened the example URL. Use the real random URL ngrok generates |
| Python 3.14 warnings | Use Python 3.11 — 3.14 has compatibility issues with LangChain |
| `langchain.schema` error | Replace with `langchain_core.documents` in ingest.py and embedder.py |

---

## Using with Claude Code

This project includes a `CLAUDE.md` file so Claude Code has full context immediately.
Open the project folder in VS Code terminal and run:

```powershell
claude
```

Then ask Claude Code to extend the project, for example:
- *"Add support for Parquet files"*
- *"Add a confidence score to each column description"*
- *"Export metadata to Excel format"*
- *"Add a history tab showing past runs"*

---

## Requirements

- Python 3.11+
- Ollama running locally
- ~4.3GB disk space for models (llama3 + nomic-embed-text)
- Windows 10/11, macOS, or Linux
