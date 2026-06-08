import json
from pathlib import Path

from app.domain.airline_mapping.codes import IATA_TO_AIRLINE_NAME
from app.domain.models.entity_type import EntityType
from app.providers.models import SearchDocument


def default_seed_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "seed"


def _load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}")
    return data


def _build_searchable_text(parts: list[str | None]) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        for token in str(part).lower().split():
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return " ".join(tokens)


def airport_to_document(record: dict) -> SearchDocument:
    aliases = record.get("aliases", [])
    iata = record.get("iata")
    icao = record.get("icao")
    name = record.get("name", "")
    display = f"{iata} - {name}" if iata else name

    searchable_text = _build_searchable_text(
        [iata, icao, name, record.get("city"), *aliases]
    )

    return SearchDocument(
        id=record["id"],
        type=EntityType.AIRPORT,
        display=display,
        searchable_text=searchable_text,
        iata=iata,
        icao=icao,
        name=name,
        city=record.get("city"),
        country=record.get("country"),
        aliases=aliases,
        metadata={"popularity": record.get("popularity", 0)},
    )


def flight_to_document(record: dict) -> SearchDocument:
    aliases = record.get("aliases", [])
    iata_flight = record.get("iata_flight")
    icao_flight = record.get("icao_flight")
    flight_number = record.get("flight_number", "")
    airline = record.get("airline", "")
    display = f"{icao_flight} ({iata_flight}) - {airline}" if iata_flight else icao_flight or ""

    searchable_text = _build_searchable_text(
        [iata_flight, icao_flight, flight_number, airline, *aliases]
    )

    return SearchDocument(
        id=record["id"],
        type=EntityType.FLIGHT,
        display=display,
        searchable_text=searchable_text,
        airline=airline,
        airline_name=IATA_TO_AIRLINE_NAME.get(airline.upper()) if airline else None,
        iata_flight=iata_flight,
        icao_flight=icao_flight,
        flight_number=flight_number,
        aliases=aliases,
        metadata={"popularity": record.get("popularity", 0)},
    )


def gate_to_document(record: dict) -> SearchDocument:
    aliases = record.get("aliases", [])
    airport_code = record.get("airport_code", "")
    gate = record.get("gate", "")
    display = f"{airport_code} - {gate} Departures"

    searchable_text = _build_searchable_text(
        [airport_code, gate, display, *aliases]
    )

    return SearchDocument(
        id=record["id"],
        type=EntityType.GATE,
        display=display,
        searchable_text=searchable_text,
        airport_code=airport_code,
        gate=gate,
        name=record.get("airport_name"),
        city=record.get("airport_city"),
        aliases=aliases,
        metadata={"popularity": record.get("popularity", 0)},
    )


def load_seed_documents(seed_dir: Path | None = None) -> list[SearchDocument]:
    """Load all seed JSON files and convert to SearchDocument objects."""
    base = seed_dir or default_seed_dir()
    documents: list[SearchDocument] = []

    airports = _load_json(base / "airports.json")
    flights = _load_json(base / "flights.json")
    gates = _load_json(base / "gates.json")

    documents.extend(airport_to_document(record) for record in airports)
    documents.extend(flight_to_document(record) for record in flights)
    documents.extend(gate_to_document(record) for record in gates)

    return documents
