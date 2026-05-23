import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from psycopg2.extras import execute_values
from rich.console import Console
from rich.progress import track
import requests

from db.connection import get_db_connection

console = Console()

VALID_SOURCES = {"CodeScan", "ARM", "Vault", "Guard"}
VALID_CATEGORIES = {"code_quality", "security", "deployment", "backup"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def validate_row(row: dict, row_num: int) -> dict:
    errors = []
    if "category" not in row or row["category"] not in VALID_CATEGORIES:
        errors.append(f"Row {row_num}: invalid category '{row.get('category', '')}'")
    if "severity" not in row or row["severity"] not in VALID_SEVERITIES:
        errors.append(f"Row {row_num}: invalid severity '{row.get('severity', '')}'")
    if "raw_text" not in row or not row["raw_text"].strip():
        errors.append(f"Row {row_num}: raw_text is empty")
    if "insight_date" not in row or not row["insight_date"].strip():
        errors.append(f"Row {row_num}: insight_date is missing")
    else:
        try:
            date.fromisoformat(row["insight_date"])
        except ValueError:
            errors.append(f"Row {row_num}: invalid date format '{row['insight_date']}'")
    if errors:
        raise ValueError("\n".join(errors))
    return row


def generate_embeddings(texts: list) -> list:
    embeddings = []
    for text in texts:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text}
        )
        embeddings.append(response.json()["embedding"])
    return embeddings


def main():
    parser = argparse.ArgumentParser(description="Ingest CSV into DevSecOps Analytics")
    parser.add_argument("--file", required=True, help="Path to CSV file")
    parser.add_argument("--source", required=True, help="Source: CodeScan, ARM, Vault, Guard")
    args = parser.parse_args()

    file = Path(args.file)
    source = args.source

    if source not in VALID_SOURCES:
        console.print(f"[red]Error:[/red] Invalid source '{source}'.")
        sys.exit(1)

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        sys.exit(1)

    console.print(f"[bold blue]Ingesting[/bold blue] {file.name} from {source}...")

    rows = []
    with open(file, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader, start=1):
            validate_row(row, i)
            rows.append(row)

    console.print(f"[green]Validated {len(rows)} rows[/green]")

    all_embeddings = []
    texts = [row["raw_text"] for row in rows]

    for i in track(range(0, len(texts), 50), description="Generating embeddings..."):
        batch = texts[i: i + 50]
        embeddings = generate_embeddings(batch)
        all_embeddings.extend(embeddings)

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reports (file_name, source_system) VALUES (%s, %s) RETURNING id",
            (file.name, source),
        )
        report_id = cur.fetchone()[0]

        values = []
        for row, embedding in zip(rows, all_embeddings):
            tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
            values.append((
                report_id,
                row["category"],
                row["severity"],
                row["insight_date"],
                row["raw_text"],
                tags,
                np.array(embedding),
            ))

        execute_values(
            cur,
            """INSERT INTO insights
               (report_id, category, severity, insight_date, raw_text, tags, embedding)
               VALUES %s""",
            values,
            template="(%s, %s, %s, %s, %s, %s, %s)",
        )
        cur.close()

    console.print(
        f"[bold green]Success![/bold green] Ingested {len(rows)} insights (report_id={report_id})"
    )


if __name__ == "__main__":
    main()