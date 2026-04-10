"""
app.py — Streamlit UI for the Metadata RAG Generator
Run with: streamlit run app.py
"""

import streamlit as st
import json
import pandas as pd
import tempfile
import os
import urllib.request
from pathlib import Path

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Metadata RAG",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Main background */
.stApp {
    background-color: #0f1117;
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #2d3748;
}

/* Cards */
.meta-card {
    background: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s;
}
.meta-card:hover {
    border-color: #4a9eff;
}

.col-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1rem;
    font-weight: 500;
    color: #4a9eff;
    margin-bottom: 0.3rem;
}

.col-type {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 0.6rem;
    font-weight: 500;
}

.type-identifier  { background: #1e3a5f; color: #60a5fa; }
.type-datetime    { background: #1e3d2e; color: #34d399; }
.type-currency    { background: #2d2a1e; color: #fbbf24; }
.type-boolean     { background: #2d1e3a; color: #c084fc; }
.type-category    { background: #1e2d3a; color: #38bdf8; }
.type-integer     { background: #1e2a1e; color: #86efac; }
.type-decimal     { background: #2a2d1e; color: #d9f99d; }
.type-free_text   { background: #2d1e1e; color: #fca5a5; }
.type-string      { background: #1e2535; color: #93c5fd; }
.type-unknown     { background: #2d2d2d; color: #9ca3af; }

.col-desc {
    font-size: 0.9rem;
    color: #cbd5e1;
    line-height: 1.5;
    margin-bottom: 0.5rem;
}

.col-meta-row {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
}

.col-meta-item {
    font-size: 0.78rem;
    color: #64748b;
}

.col-meta-item span {
    color: #94a3b8;
    font-family: 'IBM Plex Mono', monospace;
}

.col-rules {
    font-size: 0.8rem;
    color: #94a3b8;
    border-left: 2px solid #2d3748;
    padding-left: 0.7rem;
    margin-top: 0.5rem;
    font-style: italic;
}

.tag {
    display: inline-block;
    font-size: 0.7rem;
    padding: 1px 7px;
    border-radius: 3px;
    background: #1e2535;
    color: #60a5fa;
    margin-right: 4px;
    font-family: 'IBM Plex Mono', monospace;
}

.status-ok   { color: #34d399; }
.status-warn { color: #fbbf24; }
.status-err  { color: #f87171; }

.stat-box {
    background: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}
.stat-num {
    font-size: 2rem;
    font-weight: 600;
    color: #4a9eff;
    font-family: 'IBM Plex Mono', monospace;
}
.stat-label {
    font-size: 0.78rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

h1, h2, h3 { font-family: 'IBM Plex Sans', sans-serif !important; }

.header-bar {
    padding: 0.5rem 0 1.5rem 0;
    border-bottom: 1px solid #2d3748;
    margin-bottom: 1.5rem;
}
.header-title {
    font-size: 1.6rem;
    font-weight: 600;
    color: #f1f5f9;
    letter-spacing: -0.02em;
}
.header-sub {
    font-size: 0.85rem;
    color: #475569;
    margin-top: 0.2rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_ollama() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def get_available_models() -> list:
    import subprocess
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")[1:]  # skip header
        models = [l.split()[0] for l in lines if l.strip()]
        return models if models else ["llama3"]
    except Exception:
        return ["llama3", "mistral", "phi3"]


def run_generation(uploaded_file, ref_files, model, use_rag, rebuild):
    """Core pipeline — runs inside the app with progress feedback."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    from schema import describe_columns
    from embedder import build_vectorstore, load_vectorstore, vectorstore_exists, retrieve_context
    from generator import generate_metadata
    from ingest import load_documents, chunk_documents

    progress = st.progress(0, text="Starting pipeline...")

    # Save uploaded CSV to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as f:
        f.write(uploaded_file.getvalue())
        csv_path = f.name

    # Save reference docs to temp folder
    ref_dir = tempfile.mkdtemp()
    for ref in ref_files:
        ref_path = os.path.join(ref_dir, ref.name)
        with open(ref_path, "wb") as f:
            f.write(ref.getvalue())

    db = None
    if use_rag:
        progress.progress(15, text="Loading reference documents...")
        docs = load_documents(ref_dir)
        if docs:
            chunks = chunk_documents(docs)
            progress.progress(35, text=f"Embedding {len(chunks)} chunks...")
            vs_dir = "vectorstore/" if not rebuild else "vectorstore_temp/"
            db = build_vectorstore(chunks, persist_dir=vs_dir)
        elif not rebuild and vectorstore_exists():
            progress.progress(35, text="Loading existing vector store...")
            db = load_vectorstore()

    progress.progress(55, text="Parsing column schema...")
    schema_text = describe_columns(csv_path)

    context = ""
    if db:
        progress.progress(65, text="Retrieving relevant context...")
        context = retrieve_context(db, schema_text[:600], k=5)

    progress.progress(75, text=f"Generating metadata with {model}...")
    metadata = generate_metadata(
        schema=schema_text,
        context=context,
        dataset_name=uploaded_file.name,
        model=model,
    )

    progress.progress(100, text="Done!")
    os.unlink(csv_path)
    return metadata, schema_text


def type_badge(logical_type: str) -> str:
    t = logical_type.lower().replace(" ", "_")
    return f'<span class="col-type type-{t}">{logical_type}</span>'


def render_column_card(col: dict):
    name = col.get("name", "unknown")
    desc = col.get("description", "No description generated.")
    ltype = col.get("logical_type", "unknown")
    nullable = col.get("nullable", None)
    examples = col.get("example_values", [])
    rules = col.get("business_rules", "")
    quality = col.get("quality_notes", "")
    tags = col.get("tags", [])

    nullable_str = "nullable" if nullable else "not null"
    examples_str = ", ".join(str(e) for e in examples[:3])
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags) if tags else ""
    rules_html = f'<div class="col-rules">📋 {rules}</div>' if rules and rules.lower() not in ("none", "none identified", "") else ""
    quality_html = f'<div class="col-rules" style="border-color:#fbbf24;color:#fbbf24;">⚠ {quality}</div>' if quality and quality.lower() not in ("none", "") else ""

    st.markdown(f"""
    <div class="meta-card">
        <div class="col-name">{name}</div>
        {type_badge(ltype)}
        <div class="col-desc">{desc}</div>
        <div class="col-meta-row">
            <div class="col-meta-item">Examples: <span>{examples_str}</span></div>
            <div class="col-meta-item">Nullability: <span>{nullable_str}</span></div>
        </div>
        {rules_html}
        {quality_html}
        <div style="margin-top:0.5rem">{tags_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🗂️ Metadata RAG")
    st.markdown("---")

    # Ollama status
    ollama_ok = check_ollama()
    if ollama_ok:
        st.markdown('<span class="status-ok">● Ollama running</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">● Ollama not running</span>', unsafe_allow_html=True)
        st.caption("Start with: `ollama serve`")

    st.markdown("---")
    st.markdown("### ⚙️ Settings")

    models = get_available_models()
    model = st.selectbox("LLM Model", models, index=0)

    use_rag = st.toggle("Use RAG context", value=True,
                        help="Retrieve relevant context from reference documents")
    rebuild = st.toggle("Rebuild vector store", value=False,
                        help="Re-embed reference documents from scratch")

    st.markdown("---")
    st.markdown("### 📁 Reference Documents")
    ref_files = st.file_uploader(
        "Upload PDF, TXT, DOCX",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        help="These documents provide context for metadata generation"
    )
    if ref_files:
        for f in ref_files:
            st.caption(f"📄 {f.name}")

    st.markdown("---")
    st.caption("All processing is local via Ollama.\nNo data leaves your machine.")


# ── Main area ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="header-bar">
    <div class="header-title">Metadata Generator</div>
    <div class="header-sub">Upload a CSV or Excel file to generate structured metadata using local LLMs</div>
</div>
""", unsafe_allow_html=True)

if not ollama_ok:
    st.error("⚠️ Ollama is not running. Start it with `ollama serve` in a terminal, then refresh this page.")
    st.stop()

# File upload
uploaded_file = st.file_uploader(
    "Upload your dataset",
    type=["csv", "xlsx", "xls"],
    help="CSV or Excel file to generate metadata for"
)

if uploaded_file:
    # Preview
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        uploaded_file.seek(0)

        with st.expander(f"📊 Preview: {uploaded_file.name} ({len(df)} rows × {len(df.columns)} cols)", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)

        # Stats row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(df.columns)}</div><div class="stat-label">Columns</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(df)}</div><div class="stat-label">Rows</div></div>', unsafe_allow_html=True)
        with col3:
            null_pct = round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 1)
            st.markdown(f'<div class="stat-box"><div class="stat-num">{null_pct}%</div><div class="stat-label">Null Rate</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(ref_files)}</div><div class="stat-label">Ref Docs</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Could not preview file: {e}")

    # Generate button
    if st.button("⚡ Generate Metadata", type="primary", use_container_width=True):
        if not ollama_ok:
            st.error("Ollama is not running.")
        else:
            try:
                with st.spinner(""):
                    metadata, schema_text = run_generation(
                        uploaded_file=uploaded_file,
                        ref_files=ref_files,
                        model=model,
                        use_rag=use_rag,
                        rebuild=rebuild,
                    )
                st.session_state["metadata"] = metadata
                st.session_state["schema"] = schema_text
                st.success(f"✅ Generated metadata for {len(metadata.get('columns', []))} columns")
            except Exception as e:
                st.error(f"Pipeline failed: {e}")
                st.exception(e)

# ── Results ───────────────────────────────────────────────────────────────────

if "metadata" in st.session_state:
    metadata = st.session_state["metadata"]
    columns = metadata.get("columns", [])

    if not columns:
        st.warning("Metadata was generated but columns could not be parsed. Check the raw output below.")
    else:
        st.markdown("---")
        st.markdown(f"### 📋 Metadata — {metadata.get('dataset', '')}")

        # Filter bar
        filter_col, sort_col = st.columns([3, 1])
        with filter_col:
            search = st.text_input("🔍 Filter columns", placeholder="Search by name or type...")
        with sort_col:
            sort_by = st.selectbox("Sort by", ["Original order", "Name", "Type"])

        # Apply filters
        filtered = columns
        if search:
            filtered = [c for c in filtered if
                        search.lower() in c.get("name", "").lower() or
                        search.lower() in c.get("logical_type", "").lower() or
                        search.lower() in c.get("description", "").lower()]
        if sort_by == "Name":
            filtered = sorted(filtered, key=lambda c: c.get("name", ""))
        elif sort_by == "Type":
            filtered = sorted(filtered, key=lambda c: c.get("logical_type", ""))

        st.caption(f"Showing {len(filtered)} of {len(columns)} columns")

        for col in filtered:
            render_column_card(col)

    # Download buttons
    st.markdown("---")
    st.markdown("### 💾 Export")
    dl1, dl2 = st.columns(2)

    with dl1:
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(metadata, indent=2, default=str),
            file_name=f"{Path(metadata.get('dataset', 'metadata')).stem}_metadata.json",
            mime="application/json",
            use_container_width=True,
        )

    with dl2:
        # Build markdown
        lines = [f"# Metadata: {metadata.get('dataset', '')}\n"]
        if columns:
            lines.append("| Column | Type | Description | Examples | Business Rules |")
            lines.append("|--------|------|-------------|----------|----------------|")
            for col in columns:
                name = col.get("name", "")
                ltype = col.get("logical_type", "")
                desc = col.get("description", "").replace("|", "\\|")
                examples = ", ".join(str(v) for v in col.get("example_values", []))
                rules = col.get("business_rules", "").replace("|", "\\|")
                lines.append(f"| `{name}` | {ltype} | {desc} | {examples} | {rules} |")
        md_content = "\n".join(lines)

        st.download_button(
            "⬇️ Download Markdown",
            data=md_content,
            file_name=f"{Path(metadata.get('dataset', 'metadata')).stem}_metadata.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Raw output expander
    with st.expander("🔍 Raw JSON output"):
        st.json(metadata)

else:
    # Empty state
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center; color:#475569; padding: 3rem 0;">
        <div style="font-size:3rem;margin-bottom:1rem;">🗂️</div>
        <div style="font-size:1.1rem;font-weight:500;color:#64748b;">Upload a CSV or Excel file to get started</div>
        <div style="font-size:0.85rem;margin-top:0.5rem;">Optionally add reference documents in the sidebar for richer metadata</div>
    </div>
    """, unsafe_allow_html=True)
