"""
ingest.py — Load and chunk documents from the /data folder.
Supports: PDF, TXT, CSV, DOCX
"""

import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

console = Console()


def load_documents(folder: str = "data/") -> List[Document]:
    """Load all supported documents from the data folder."""
    docs: List[Document] = []
    data_path = Path(folder)

    if not data_path.exists():
        console.print(f"[yellow]⚠ Data folder '{folder}' not found. Creating it.[/yellow]")
        data_path.mkdir(parents=True)
        return docs

    files = list(data_path.iterdir())
    if not files:
        console.print(f"[yellow]⚠ No files found in '{folder}'. Add PDF, TXT, or CSV files.[/yellow]")
        return docs

    for fpath in files:
        if fpath.suffix.lower() == ".pdf":
            docs.extend(_load_pdf(fpath))
        elif fpath.suffix.lower() == ".txt":
            docs.extend(_load_txt(fpath))
        elif fpath.suffix.lower() == ".csv":
            docs.extend(_load_csv_as_text(fpath))
        elif fpath.suffix.lower() == ".docx":
            docs.extend(_load_docx(fpath))
        else:
            console.print(f"[dim]  Skipping unsupported file: {fpath.name}[/dim]")

    console.print(f"[green]✓ Loaded {len(docs)} document chunks from {folder}[/green]")
    return docs


def _load_pdf(path: Path) -> List[Document]:
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(str(path))
        docs = loader.load()
        console.print(f"  [cyan]PDF[/cyan] {path.name} → {len(docs)} pages")
        return docs
    except Exception as e:
        console.print(f"  [red]✗ Failed to load PDF {path.name}: {e}[/red]")
        return []


def _load_txt(path: Path) -> List[Document]:
    try:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(str(path), encoding="utf-8")
        docs = loader.load()
        console.print(f"  [cyan]TXT[/cyan] {path.name} → {len(docs)} doc(s)")
        return docs
    except Exception as e:
        console.print(f"  [red]✗ Failed to load TXT {path.name}: {e}[/red]")
        return []


def _load_csv_as_text(path: Path) -> List[Document]:
    """Load CSV as a text description (not row-by-row) for context retrieval."""
    try:
        import pandas as pd
        df = pd.read_csv(path)
        lines = [f"File: {path.name}", f"Columns: {', '.join(df.columns.tolist())}",
                 f"Rows: {len(df)}", "", "Column summaries:"]
        for col in df.columns:
            sample = df[col].dropna().head(5).tolist()
            dtype = str(df[col].dtype)
            lines.append(f"  - {col} ({dtype}): {sample}")
        text = "\n".join(lines)
        doc = Document(page_content=text, metadata={"source": str(path), "type": "csv_summary"})
        console.print(f"  [cyan]CSV[/cyan] {path.name} → summary doc ({len(df.columns)} cols)")
        return [doc]
    except Exception as e:
        console.print(f"  [red]✗ Failed to load CSV {path.name}: {e}[/red]")
        return []


def _load_docx(path: Path) -> List[Document]:
    try:
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(str(path))
        docs = loader.load()
        console.print(f"  [cyan]DOCX[/cyan] {path.name} → {len(docs)} doc(s)")
        return docs
    except Exception as e:
        console.print(f"  [red]✗ Failed to load DOCX {path.name}: {e}[/red]")
        return []


def chunk_documents(docs: List[Document], chunk_size: int = 600, chunk_overlap: int = 80) -> List[Document]:
    """Split documents into chunks for embedding."""
    if not docs:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    console.print(f"[green]✓ Split into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})[/green]")
    return chunks
