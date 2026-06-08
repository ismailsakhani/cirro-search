#!/usr/bin/env python3
"""
Generate synthetic flight seed data from OpenFlights airlines.dat.

Usage:
    python scripts/generate_flights.py [airlines_dat] [output_flights_json] [output_codes_py]

Defaults:
    airlines_dat       = ~/Downloads/airlines.dat
    output_flights_json = data/seed/flights.json
    output_codes_py    = backend/app/domain/airline_mapping/codes.py

Also regenerates codes.py so the classifier recognises all airline codes.
"""
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Flight numbers to generate per airline.
# Low range covers common flights; key numbers cover stress-test cases.
FLIGHT_NUMBER_RANGE = list(range(1, 51))          # 1–50
KEY_FLIGHT_NUMBERS = [100, 200, 300, 400, 500,
                      1000, 1500, 2000, 4433]      # stress-test anchors
ALL_FLIGHT_NUMBERS = sorted(set(FLIGHT_NUMBER_RANGE + KEY_FLIGHT_NUMBERS))  # 59 per airline

# Well-known carriers get higher popularity score.
MAJOR_IATA = {
    # US
    "UA", "AA", "DL", "WN", "AS", "B6", "F9", "NK", "G4", "HA",
    # Europe
    "BA", "LH", "AF", "KL", "IB", "AZ", "SK", "LX", "OS", "SN",
    "VY", "FR", "U2", "TP", "TK", "SU", "LO", "OK", "AY",
    # Middle East / Africa
    "EK", "QR", "EY", "SV", "MS", "ET", "SA",
    # Asia Pacific
    "SQ", "CX", "TG", "MH", "GA", "PR", "OZ", "KE", "NH", "JL",
    "AI", "6E", "IX", "SL",
    # Oceania
    "QF", "NZ", "VA",
    # Americas
    "AC", "AM", "LA", "JJ", "AV", "CM", "TA",
}

# Airline name → IATA for classifier's _match_airline_name_flight.
# Only names a user would realistically type.
WELL_KNOWN_NAMES: dict[str, str] = {
    "united": "UA",
    "american": "AA",
    "delta": "DL",
    "southwest": "WN",
    "alaska": "AS",
    "jetblue": "B6",
    "frontier": "F9",
    "spirit": "NK",
    "british airways": "BA",
    "lufthansa": "LH",
    "air france": "AF",
    "klm": "KL",
    "iberia": "IB",
    "alitalia": "AZ",
    "scandinavian": "SK",
    "swiss": "LX",
    "austrian": "OS",
    "emirates": "EK",
    "qatar": "QR",
    "etihad": "EY",
    "saudia": "SV",
    "egyptair": "MS",
    "ethiopian": "ET",
    "singapore": "SQ",
    "cathay": "CX",
    "thai": "TG",
    "malaysia": "MH",
    "garuda": "GA",
    "philippine": "PR",
    "asiana": "OZ",
    "korean": "KE",
    "ana": "NH",
    "jal": "JL",
    "air india": "AI",
    "qantas": "QF",
    "air new zealand": "NZ",
    "air canada": "AC",
    "aeromexico": "AM",
    "latam": "LA",
    "avianca": "AV",
}


def _clean(val: str) -> str | None:
    v = val.strip().strip('"')
    return None if v in ("", r"\N", "-") else v


def load_airlines(path: Path) -> list[dict]:
    """Parse airlines.dat, return active airlines with valid IATA codes."""
    airlines = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 8:
                continue
            active = _clean(row[7])
            if active != "Y":
                continue
            iata = _clean(row[3])
            if not iata or len(iata) != 2 or not iata.isalnum():
                continue
            icao = _clean(row[4])
            name = _clean(row[1]) or iata
            airlines.append({"iata": iata, "icao": icao, "name": name})
    # Deduplicate by IATA (keep first occurrence)
    seen: set[str] = set()
    unique = []
    for a in airlines:
        if a["iata"] not in seen:
            seen.add(a["iata"])
            unique.append(a)
    return unique


def build_aliases(iata: str, icao: str | None, flight_num: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    def add(term: str) -> None:
        t = term.strip().lower()
        if t and t not in seen:
            seen.add(t)
            result.append(t)

    add(f"{iata}{flight_num}")
    if icao:
        add(f"{icao}{flight_num}")
    return result


def generate_flights(airlines: list[dict]) -> list[dict]:
    records = []
    for airline in airlines:
        iata = airline["iata"]
        icao = airline["icao"]
        is_major = iata in MAJOR_IATA
        # Tier 1: original seed carriers get highest popularity for ranker disambiguation
        is_tier1 = iata in {"UA", "AA", "DL"}
        base_popularity = 100 if is_tier1 else (80 if is_major else 40)

        for num in ALL_FLIGHT_NUMBERS:
            flight_num = str(num)
            iata_flight = f"{iata}{flight_num}"
            icao_flight = f"{icao}{flight_num}" if icao else None

            records.append({
                "id": f"flight:{iata_flight}",
                "airline": iata,
                "iata_flight": iata_flight,
                "icao_flight": icao_flight,
                "flight_number": flight_num,
                "aliases": build_aliases(iata, icao, flight_num),
                "popularity": base_popularity,
            })

    # Sort: major airlines first, then by flight number
    records.sort(key=lambda r: (
        0 if r["airline"] in MAJOR_IATA else 1,
        int(r["flight_number"]),
    ))
    return records


def write_codes_py(airlines: list[dict], path: Path) -> None:
    """Regenerate codes.py with full IATA→ICAO table from dataset."""
    iata_to_icao = {
        a["iata"]: a["icao"]
        for a in airlines
        if a["icao"]
    }

    # Build AIRLINE_NAMES from well-known names, filtered to airlines in dataset
    iata_set = {a["iata"] for a in airlines}
    airline_names = {
        name: iata
        for name, iata in WELL_KNOWN_NAMES.items()
        if iata in iata_set
    }

    lines = [
        '"""IATA ↔ ICAO airline code tables — auto-generated by scripts/generate_flights.py"""',
        "",
        "IATA_TO_ICAO: dict[str, str] = {",
    ]
    for iata, icao in sorted(iata_to_icao.items()):
        lines.append(f'    "{iata}": "{icao}",')
    lines += [
        "}",
        "",
        "ICAO_TO_IATA: dict[str, str] = {icao: iata for iata, icao in IATA_TO_ICAO.items()}",
        "",
        "# Sorted longest-first for greedy matching in classifier",
        "ICAO_AIRLINE_CODES: tuple[str, ...] = tuple(",
        "    sorted(IATA_TO_ICAO.values(), key=len, reverse=True)",
        ")",
        "",
        "IATA_AIRLINE_CODES: tuple[str, ...] = tuple(",
        "    sorted(IATA_TO_ICAO.keys(), key=len, reverse=True)",
        ")",
        "",
        "AIRLINE_NAMES: dict[str, str] = {",
    ]
    for name, iata in sorted(airline_names.items()):
        lines.append(f'    "{name}": "{iata}",')
    lines += ["}", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    airlines_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "airlines.dat"
    flights_path = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "data" / "seed" / "flights.json"
    codes_path = Path(sys.argv[3]) if len(sys.argv) > 3 else REPO_ROOT / "backend" / "app" / "domain" / "airline_mapping" / "codes.py"

    print(f"Loading airlines from {airlines_path}...")
    airlines = load_airlines(airlines_path)
    print(f"Loaded {len(airlines)} active airlines with IATA codes")

    print("Generating flights...")
    flights = generate_flights(airlines)
    print(f"Generated {len(flights):,} flights")

    flights_path.parent.mkdir(parents=True, exist_ok=True)
    with flights_path.open("w", encoding="utf-8") as fh:
        json.dump(flights, fh, indent=2, ensure_ascii=False)
    print(f"Written → {flights_path}")

    print("Regenerating codes.py...")
    write_codes_py(airlines, codes_path)
    print(f"Written → {codes_path}")

    # Stress-test report
    with_4433 = sum(1 for f in flights if f["flight_number"] == "4433")
    print(f"\nStress-test: {with_4433} airlines have flight 4433 (UA4433 must rank #1)")


if __name__ == "__main__":
    main()
