"""
main.py — Orchestrate the full metadata RAG pipeline.

Usage:
  python main.py                        # Process all CSVs in data/
  python main.py --file data/mydata.csv # Process a single file
  python main.py --rebuild              # Force re-embed all documents
  python main.py --model mistral        # Use a different Ollama model
  python main.py --no-rag               # Skip RAG, use schema only
"""

import sys
import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

app = typer.Typer(help="Local RAG Metadata Generator using Ollama")
console = Console()


def check_ollama() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=3)
        console.print("[green]✓ Ollama is running[/green]")
        return True
    except Exception:
        console.print(Panel(
            "[red]✗ Ollama is not running or not installed.\n\n"
            "Start it with:  [bold]ollama serve[/bold]\n"
            "Install from:   [bold]https://ollama.com[/bold]",
            title="Ollama not found", border_style="red"
        ))
        return False


def ensure_models(model: str = "llama3"):
    import subprocess
    for m in [model, "nomic-embed-text"]:
        console.print(f"  [dim]Checking model '{m}'...[/dim]")
        result = subprocess.run(["ollama", "pull", m], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"  [green]✓ '{m}' ready[/green]")
        else:
            console.print(f"  [yellow]⚠ Could not pull '{m}': {result.stderr.strip()}[/yellow]")


def run_pipeline(
    file: Optional[str],
    rebuild: bool,
    model: str,
    use_rag: bool,
    output_format: str,
):
    from ingest import load_documents, chunk_documents
    from schema import get_all_csv_schemas, describe_columns
    from embedder import build_vectorstore, load_vectorstore, vectorstore_exists, retrieve_context
    from generator import generate_metadata, save_metadata, save_metadata_markdown

    console.print(Rule("[bold cyan]Metadata RAG Pipeline[/bold cyan]"))

    # ── 1. Build or load vector store ────────────────────────────────────
    if use_rag:
        if rebuild or not vectorstore_exists():
            console.print("\n[bold]Step 1/4: Ingesting documents into vector store[/bold]")
            docs = load_documents("data/")
            chunks = chunk_documents(docs)
            db = build_vectorstore(chunks) if chunks else None
        else:
            console.print("\n[bold]Step 1/4: Loading existing vector store[/bold]")
            db = load_vectorstore()
    else:
        console.print("\n[bold]Step 1/4: Skipping RAG (--no-rag flag)[/bold]")
        db = None

    # ── 2. Find CSV/Excel files to process ───────────────────────────────
    console.print("\n[bold]Step 2/4: Parsing column schemas[/bold]")

    if file:
        targets = [file]
    else:
        data_path = Path("data/")
        targets = [
            str(p) for p in data_path.iterdir()
            if p.suffix.lower() in (".csv", ".xlsx", ".xls")
        ]

    if not targets:
        console.print("[yellow]⚠ No CSV or Excel files found in data/. Add some files and re-run.[/yellow]")
        return

    schemas = {}
    for t in targets:
        try:
            schemas[t] = describe_columns(t)
            console.print(f"  [green]✓ Schema: {Path(t).name}[/green]")
        except Exception as e:
            console.print(f"  [red]✗ Failed: {Path(t).name} — {e}[/red]")

    # ── 3. Retrieve RAG context + generate metadata ───────────────────────
    console.print("\n[bold]Step 3/4: Generating metadata with Ollama[/bold]")

    results = []
    for filepath, schema_text in schemas.items():
        dataset_name = Path(filepath).name
        console.print(f"\n  Processing: [cyan]{dataset_name}[/cyan]")

        # Retrieve relevant context from vector store
        if db and use_rag:
            context = retrieve_context(db, schema_text[:600], k=5)
            console.print(f"  [dim]Retrieved {len(context.split())} words of context[/dim]")
        else:
            context = ""

        # Generate metadata
        try:
            metadata = generate_metadata(
                schema=schema_text,
                context=context,
                dataset_name=dataset_name,
                model=model,
            )
            results.append((dataset_name, metadata))
        except Exception as e:
            console.print(f"  [red]✗ Generation failed for {dataset_name}: {e}[/red]")

    # ── 4. Save outputs ───────────────────────────────────────────────────
    console.print("\n[bold]Step 4/4: Saving outputs[/bold]")

    Path("output/").mkdir(exist_ok=True)

    for dataset_name, metadata in results:
        stem = Path(dataset_name).stem

        if output_format in ("json", "both"):
            json_path = f"output/{stem}_metadata.json"
            save_metadata(metadata, json_path)

        if output_format in ("markdown", "both"):
            md_path = f"output/{stem}_metadata.md"
            save_metadata_markdown(metadata, md_path)

    console.print(Rule())
    console.print(f"[bold green]Done! {len(results)} file(s) processed. Check the output/ folder.[/bold green]")


# ── CLI entry point ───────────────────────────────────────────────────────────

@app.command()
def main(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to a single CSV/Excel file"),
    rebuild: bool = typer.Option(False, "--rebuild", "-r", help="Force re-embed all documents"),
    model: str = typer.Option("llama3", "--model", "-m", help="Ollama model name (e.g. llama3, mistral)"),
    no_rag: bool = typer.Option(False, "--no-rag", help="Skip RAG retrieval, use schema only"),
    output_format: str = typer.Option("both", "--format", help="Output format: json, markdown, or both"),
    setup: bool = typer.Option(False, "--setup", help="Pull required Ollama models and exit"),
    check: bool = typer.Option(False, "--check", help="Check environment and exit"),
):
    """
    Generate structured metadata for your datasets using local LLMs via Ollama.
    Place your CSV/Excel files and reference documents in the data/ folder, then run.
    """

    if check or setup:
        console.print(Rule("[bold]Environment Check[/bold]"))
        ok = check_ollama()
        if ok and setup:
            console.print("\n[bold]Pulling models...[/bold]")
            ensure_models(model)
        return

    # Always verify Ollama is running before starting
    if not check_ollama():
        raise typer.Exit(1)

    run_pipeline(
        file=file,
        rebuild=rebuild,
        model=model,
        use_rag=not no_rag,
        output_format=output_format,
    )


if __name__ == "__main__":
    app()
