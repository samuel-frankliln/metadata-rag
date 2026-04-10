"""
schema.py — Parse column names, types, and sample values from CSV/Excel files.
This feeds directly into the metadata generation prompt.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()


def describe_columns(filepath: str) -> str:
    """
    Returns a structured text description of all columns + sample values.
    Used as input to the LLM metadata generation prompt.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(filepath)
    elif path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}. Use CSV or Excel.")

    return _build_schema_text(df, path.name)


def describe_columns_from_df(df: pd.DataFrame, name: str = "dataframe") -> str:
    """Build schema text directly from a DataFrame."""
    return _build_schema_text(df, name)


def _build_schema_text(df: pd.DataFrame, filename: str) -> str:
    lines = [
        f"Dataset: {filename}",
        f"Total rows: {len(df)}",
        f"Total columns: {len(df.columns)}",
        "",
        "Column details:"
    ]

    for col in df.columns:
        series = df[col].dropna()
        dtype = str(df[col].dtype)
        null_count = df[col].isna().sum()
        null_pct = round((null_count / len(df)) * 100, 1) if len(df) > 0 else 0

        # Get representative samples
        if len(series) == 0:
            samples = []
            unique_count = 0
        else:
            unique_count = series.nunique()
            if unique_count <= 10:
                # Show all unique values if few
                samples = series.unique().tolist()[:10]
            else:
                # Show diverse sample: first, middle, last
                samples = series.head(3).tolist()

        # Infer logical type hint
        type_hint = _infer_logical_type(series, dtype)

        lines.append(f"\n  Column: {col}")
        lines.append(f"    dtype        : {dtype}")
        lines.append(f"    logical_type : {type_hint}")
        lines.append(f"    unique_values: {unique_count}")
        lines.append(f"    null_pct     : {null_pct}%")
        lines.append(f"    samples      : {samples}")

        # Add numeric stats if applicable
        if "int" in dtype or "float" in dtype:
            try:
                lines.append(f"    min/max      : {series.min()} / {series.max()}")
                lines.append(f"    mean         : {round(series.mean(), 2)}")
            except Exception:
                pass

        # Add top value counts for low-cardinality columns
        if 1 < unique_count <= 15:
            top = series.value_counts().head(5).to_dict()
            lines.append(f"    top_values   : {top}")

    return "\n".join(lines)


def _infer_logical_type(series: pd.Series, dtype: str) -> str:
    """Heuristically infer a logical type for a column."""
    if len(series) == 0:
        return "unknown"

    name_lower = str(series.name).lower()

    # ID detection
    if any(k in name_lower for k in ["_id", "id_", " id", "uuid", "key"]):
        return "identifier"

    # Date/time
    if "datetime" in dtype or "timestamp" in dtype:
        return "datetime"
    if any(k in name_lower for k in ["date", "time", "created", "updated", "at"]):
        return "datetime"

    # Currency/money
    if any(k in name_lower for k in ["price", "cost", "amount", "revenue", "salary", "fee", "total"]):
        return "currency"

    # Boolean
    if dtype == "bool":
        return "boolean"
    if series.nunique() == 2:
        vals = set(str(v).lower() for v in series.unique())
        if vals <= {"true", "false", "yes", "no", "1", "0", "y", "n"}:
            return "boolean"

    # Categorical
    if series.nunique() <= 20 and ("object" in dtype or "category" in dtype):
        return "category"

    # Numeric
    if "int" in dtype:
        return "integer"
    if "float" in dtype:
        return "decimal"

    # Text
    if "object" in dtype:
        avg_len = series.astype(str).str.len().mean()
        if avg_len > 50:
            return "free_text"
        return "string"

    return dtype


def get_all_csv_schemas(folder: str = "data/") -> Dict[str, str]:
    """Return schema descriptions for all CSV/Excel files in a folder."""
    schemas = {}
    data_path = Path(folder)
    for fpath in data_path.iterdir():
        if fpath.suffix.lower() in (".csv", ".xlsx", ".xls"):
            try:
                schemas[fpath.name] = describe_columns(str(fpath))
                console.print(f"[green]✓ Schema parsed: {fpath.name}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Schema failed for {fpath.name}: {e}[/red]")
    return schemas


def print_schema_table(filepath: str):
    """Pretty-print a schema table to the console."""
    path = Path(filepath)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    table = Table(title=f"Schema: {path.name}", show_lines=True)
    table.add_column("Column", style="cyan")
    table.add_column("dtype")
    table.add_column("Logical type", style="green")
    table.add_column("Nulls %")
    table.add_column("Unique")
    table.add_column("Samples", max_width=40)

    for col in df.columns:
        series = df[col].dropna()
        dtype = str(df[col].dtype)
        null_pct = f"{round((df[col].isna().sum() / len(df)) * 100, 1)}%"
        unique = str(series.nunique())
        samples = str(series.head(3).tolist())
        logical = _infer_logical_type(series, dtype)
        table.add_row(col, dtype, logical, null_pct, unique, samples)

    console.print(table)
