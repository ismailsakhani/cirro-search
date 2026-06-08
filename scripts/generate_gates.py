#!/usr/bin/env python3
"""
Generate synthetic gate seed data from airports.json.

Gate layout per popularity tier:
  large  (pop>=90): A/B/C/D terminals, gates 1-30; terminal C also gets 100-120 series
  medium (pop>=70): A/B terminals, gates 1-15
  small  (pop>=50): A terminal, gates 1-8

Usage:
    python scripts/generate_gates.py [airports_json] [output_gates_json]
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LARGE_STANDARD = list(range(1, 31))                    # 1–30
LARGE_C_EXTRA  = list(range(100, 121))                 # 100–120 (covers C101 demo case)
MEDIUM_STANDARD = list(range(1, 16))                   # 1–15
SMALL_STANDARD  = list(range(1, 9))                    # 1–8

TERMINAL_CONFIG: list[tuple[int, list[tuple[str, list[int]]]]] = [
    (90, [
        ("A", LARGE_STANDARD),
        ("B", LARGE_STANDARD),
        ("C", LARGE_STANDARD + LARGE_C_EXTRA),
        ("D", LARGE_STANDARD),
    ]),
    (70, [
        ("A", MEDIUM_STANDARD),
        ("B", MEDIUM_STANDARD),
    ]),
    (50, [
        ("A", SMALL_STANDARD),
    ]),
]


def get_terminal_config(popularity: int) -> list[tuple[str, list[int]]] | None:
    for min_pop, config in TERMINAL_CONFIG:
        if popularity >= min_pop:
            return config
    return None


def build_aliases(airport_code: str, gate: str) -> list[str]:
    code = airport_code.lower()
    g = gate.lower()
    return [
        f"{code} {g}",
        f"{code}-{g}",
        f"{g} {code}",
    ]


def generate_gates(airports: list[dict]) -> list[dict]:
    records = []
    for airport in airports:
        iata = airport.get("iata")
        if not iata:
            continue
        popularity = airport.get("popularity", 0)
        config = get_terminal_config(popularity)
        if not config:
            continue

        gate_popularity = min(popularity, 90)

        airport_name = airport.get("name")
        airport_city = airport.get("city")

        for terminal, gate_numbers in config:
            for num in gate_numbers:
                gate = f"{terminal}{num}"
                records.append({
                    "id": f"gate:{iata}:{gate}",
                    "airport_code": iata,
                    "gate": gate,
                    "airport_name": airport_name,
                    "airport_city": airport_city,
                    "aliases": build_aliases(iata, gate),
                    "popularity": gate_popularity,
                })

    records.sort(key=lambda r: (-r["popularity"], r["airport_code"], r["gate"]))
    return records


def main() -> None:
    airports_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1
        else REPO_ROOT / "data" / "seed" / "airports.json"
    )
    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2
        else REPO_ROOT / "data" / "seed" / "gates.json"
    )

    airports = json.loads(airports_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(airports):,} airports")

    gates = generate_gates(airports)
    print(f"Generated {len(gates):,} gates")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(gates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Written → {output_path}")

    # Verify demo test cases exist
    gate_set = {(g["airport_code"], g["gate"]) for g in gates}
    for airport, gate in [("EWR", "B17"), ("EWR", "C101"), ("ORD", "C17"), ("LHR", "A15"), ("CDG", "D10")]:
        exists = (airport, gate) in gate_set
        print(f"  {airport} {gate}: {'✓' if exists else '✗ MISSING'}")


if __name__ == "__main__":
    main()
