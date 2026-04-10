"""
generator.py — Call a local Ollama LLM to generate structured metadata
for each column, using schema info + RAG context as input.
"""

import json
import re
from typing import Dict, Any

from rich.console import Console

console = Console()

DEFAULT_MODEL = "llama3"

METADATA_PROMPT_TEMPLATE = """You are a data catalog assistant. Your job is to generate high-quality metadata for dataset columns.

You are given:
1. A schema description with column names, types, and sample values
2. Relevant documentation retrieved from reference documents (may be empty)

Your task: For EVERY column in the schema, generate structured metadata.

Schema:
{schema}

Relevant documentation context:
{context}

Instructions:
- Analyze each column's name, data type, sample values, and any documentation context
- Generate metadata for ALL columns listed above
- Return ONLY valid JSON — no markdown, no explanation, no extra text
- Use this exact structure:

{{
  "dataset": "<filename>",
  "columns": [
    {{
      "name": "<column name>",
      "description": "<1-2 sentence plain English description of what this field represents>",
      "logical_type": "<one of: identifier, datetime, currency, boolean, category, integer, decimal, free_text, string>",
      "nullable": <true or false>,
      "example_values": ["<val1>", "<val2>", "<val3>"],
      "business_rules": "<any constraints, relationships, or patterns observed (or 'None identified')>",
      "quality_notes": "<data quality observations like high null rate, inconsistent format, etc. (or 'None')>",
      "tags": ["<tag1>", "<tag2>"]
    }}
  ]
}}
"""


def generate_metadata(
    schema: str,
    context: str,
    dataset_name: str = "dataset",
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Call Ollama LLM to generate metadata JSON for all columns.
    Returns a parsed dict.
    """
    try:
        from langchain_ollama import OllamaLLM
    except ImportError:
        console.print("[red]✗ langchain-ollama not installed.[/red]")
        raise

    llm = OllamaLLM(model=model, temperature=0.1)

    prompt = METADATA_PROMPT_TEMPLATE.format(
        schema=schema,
        context=context if context.strip() else "No documentation context available.",
    )

    console.print(f"[cyan]→ Generating metadata with model '{model}'...[/cyan]")
    console.print("[dim]  (First run may be slow while Ollama loads the model)[/dim]")

    raw_output = llm.invoke(prompt)

    return _parse_llm_output(raw_output, dataset_name)


def _parse_llm_output(raw: str, dataset_name: str) -> Dict[str, Any]:
    """Extract and parse JSON from LLM output robustly."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Remove any leading text before the first {
    brace_start = cleaned.find("{")
    if brace_start > 0:
        cleaned = cleaned[brace_start:]

    # Remove any trailing text after the last }
    brace_end = cleaned.rfind("}")
    if brace_end != -1:
        cleaned = cleaned[:brace_end + 1]

    # Fix Python literals that LLMs sometimes output
    cleaned = cleaned.replace(": True", ": true")
    cleaned = cleaned.replace(": False", ": false")
    cleaned = cleaned.replace(": None", ": null")
    # Fix Python booleans anywhere in the string (not just after ": ")
    cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
    cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
    cleaned = re.sub(r'\bNone\b', 'null', cleaned)
    # Fix trailing commas before } or ] which are invalid JSON
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    try:
        result = json.loads(cleaned)
        if "dataset" not in result:
            result["dataset"] = dataset_name
        console.print("[green]✓ Metadata generated and parsed successfully[/green]")
        return result
    except json.JSONDecodeError as e:
        console.print(f"[yellow]⚠ Could not parse JSON: {e}[/yellow]")
        return {
            "dataset": dataset_name,
            "raw_output": raw,
            "parse_error": "LLM did not return valid JSON. Try a larger model or re-run.",
            "columns": []
        }
    
def save_metadata(metadata: Dict[str, Any], output_path: str):
    """Save metadata dict as a formatted JSON file."""
    import pathlib
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    console.print(f"[green]✓ Metadata saved to '{output_path}'[/green]")


def save_metadata_markdown(metadata: Dict[str, Any], output_path: str):
    """Save metadata as a Markdown table for easy reading."""
    import pathlib
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# Metadata: {metadata.get('dataset', 'dataset')}\n"]
    columns = metadata.get("columns", [])

    if not columns:
        lines.append("_No columns found in metadata._")
    else:
        lines.append("| Column | Type | Description | Example Values | Business Rules | Quality Notes |")
        lines.append("|--------|------|-------------|----------------|----------------|---------------|")
        for col in columns:
            name = col.get("name", "")
            ltype = col.get("logical_type", "")
            desc = col.get("description", "").replace("|", "\\|")
            examples = ", ".join(str(v) for v in col.get("example_values", []))
            rules = col.get("business_rules", "").replace("|", "\\|")
            quality = col.get("quality_notes", "").replace("|", "\\|")
            lines.append(f"| `{name}` | {ltype} | {desc} | {examples} | {rules} | {quality} |")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    console.print(f"[green]✓ Markdown metadata saved to '{output_path}'[/green]")
