#!/usr/bin/env python3
"""
Convert OurAirports airports.csv to cirro-search seed format.

Usage:
    python scripts/convert_airports.py [input_csv] [output_json]

Defaults:
    input_csv  = ~/Downloads/airports(1).csv
    output_json = data/seed/airports.json (relative to repo root)
"""
import csv
import json
import sys
from pathlib import Path


INCLUDED_TYPES = {"large_airport", "medium_airport", "small_airport"}
BASE_POPULARITY = {"large_airport": 90, "medium_airport": 60, "small_airport": 30}
REPO_ROOT = Path(__file__).resolve().parent.parent


def build_aliases(row: dict) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    def add(term: str) -> None:
        t = term.strip().lower()
        if t and t not in seen:
            seen.add(t)
            result.append(t)

    add(row["iata_code"])
    add(row["icao_code"])
    add(row["municipality"])
    add(row["name"])
    for kw in row["keywords"].split(","):
        add(kw)
    if row["municipality"].strip():
        add(row["municipality"].strip() + " airport")

    return result


def convert_row(row: dict) -> dict | None:
    iata = row["iata_code"].strip()
    if not iata:
        return None
    if row["type"] not in INCLUDED_TYPES:
        return None

    base = BASE_POPULARITY[row["type"]]
    bonus = 10 if row["scheduled_service"].strip() == "yes" else 0
    popularity = min(base + bonus, 100)

    icao = row["icao_code"].strip() or None

    return {
        "id": f"airport:{iata}",
        "iata": iata,
        "icao": icao,
        "name": row["name"].strip(),
        "city": row["municipality"].strip() or None,
        "country": row["iso_country"].strip() or None,
        "aliases": build_aliases(row),
        "popularity": popularity,
    }


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "airports(1).csv"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "data" / "seed" / "airports.json"

    total = skipped_no_iata = skipped_type = 0
    records: list[dict] = []

    with input_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            total += 1
            if not row["iata_code"].strip():
                skipped_no_iata += 1
                continue
            if row["type"] not in INCLUDED_TYPES:
                skipped_type += 1
                continue
            record = convert_row(row)
            if record:
                records.append(record)

    records.sort(key=lambda r: r["popularity"], reverse=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)

    print(f"Read:    {total:,} rows")
    print(f"Skipped: {skipped_no_iata:,} (no IATA) + {skipped_type:,} (wrong type)")
    print(f"Written: {len(records):,} airports → {output_path}")


if __name__ == "__main__":
    main()
