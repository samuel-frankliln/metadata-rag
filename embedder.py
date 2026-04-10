"""
embedder.py — Embed document chunks using Ollama (nomic-embed-text)
and persist them in a ChromaDB vector store.
"""

import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from rich.console import Console

console = Console()

PERSIST_DIR = "vectorstore/"
EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "metadata_rag_docs"


def _get_embeddings():
    """Return an Ollama embeddings instance."""
    try:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=EMBED_MODEL)
    except ImportError:
        console.print("[red]✗ langchain-ollama not installed. Run: pip install langchain-ollama[/red]")
        raise


def build_vectorstore(docs: List[Document], persist_dir: str = PERSIST_DIR):
    """Embed documents and persist to ChromaDB. Overwrites existing store."""
    from langchain_community.vectorstores import Chroma

    if not docs:
        console.print("[yellow]⚠ No documents to embed.[/yellow]")
        return None

    console.print(f"[cyan]→ Embedding {len(docs)} chunks with '{EMBED_MODEL}'...[/cyan]")
    console.print("[dim]  (This may take a minute on first run while Ollama loads the model)[/dim]")

    embeddings = _get_embeddings()

    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=COLLECTION_NAME,
    )

    console.print(f"[green]✓ Vector store built and saved to '{persist_dir}'[/green]")
    return db


def load_vectorstore(persist_dir: str = PERSIST_DIR):
    """Load an existing ChromaDB vector store from disk."""
    from langchain_community.vectorstores import Chroma

    if not Path(persist_dir).exists():
        console.print(f"[yellow]⚠ No vector store found at '{persist_dir}'. Run ingestion first.[/yellow]")
        return None

    embeddings = _get_embeddings()
    db = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )
    count = db._collection.count()
    console.print(f"[green]✓ Loaded vector store: {count} chunks from '{persist_dir}'[/green]")
    return db


def vectorstore_exists(persist_dir: str = PERSIST_DIR) -> bool:
    """Check if a persisted vector store already exists."""
    p = Path(persist_dir)
    return p.exists() and any(p.iterdir())


def retrieve_context(db, query: str, k: int = 5) -> str:
    """Retrieve the top-k relevant chunks for a query string."""
    if db is None:
        return ""
    retriever = db.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(query)
    if not docs:
        return ""
    return "\n\n---\n\n".join(d.page_content for d in docs)
