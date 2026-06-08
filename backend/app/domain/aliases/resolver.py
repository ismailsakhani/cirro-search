import json
from pathlib import Path

from app.domain.models.entity_type import EntityType
from app.domain.models.query import AliasResolution, ClassificationResult, QueryType


class AliasResolver:
    """Resolve natural language and compound queries via alias table."""

    def __init__(self, aliases: list[dict] | None = None, seed_path: Path | None = None) -> None:
        if aliases is not None:
            self._aliases = aliases
        else:
            path = seed_path or self._default_seed_path()
            self._aliases = self._load_aliases(path)

        self._by_term = {
            entry["term"].lower(): entry for entry in self._aliases if entry.get("term")
        }

    def resolve(
        self, query: str, classification: ClassificationResult
    ) -> AliasResolution:
        key = query.strip().lower()
        entry = self._by_term.get(key)

        if entry:
            entity_type = EntityType(entry["entity_type"])
            return AliasResolution(
                matched=True,
                entity_id=entry["entity_id"],
                entity_type=entity_type,
                expanded_terms=self._terms_for_entry(entry, query),
            )

        if classification.query_type == QueryType.AMBIGUOUS:
            return AliasResolution(
                matched=False,
                expanded_terms=[query.strip()],
            )

        return AliasResolution(matched=False)

    @staticmethod
    def _terms_for_entry(entry: dict, query: str) -> list[str]:
        terms = [query.strip(), entry["term"]]
        entity_id = entry.get("entity_id", "")

        if entity_id.startswith("airport:"):
            code = entity_id.split(":", 1)[1]
            terms.extend([code, code.lower()])
        elif entity_id.startswith("flight:"):
            flight_id = entity_id.split(":", 1)[1]
            terms.append(flight_id)
            if flight_id[2:].isdigit():
                terms.append(flight_id[2:])
        elif entity_id.startswith("gate:"):
            parts = entity_id.split(":")
            if len(parts) == 3:
                terms.extend([parts[2], parts[1], f"{parts[1]} {parts[2]}".lower()])

        seen: set[str] = set()
        unique: list[str] = []
        for term in terms:
            lowered = term.lower()
            if lowered not in seen:
                seen.add(lowered)
                unique.append(term)
        return unique

    @staticmethod
    def _default_seed_path() -> Path:
        return Path(__file__).resolve().parents[4] / "data" / "seed" / "aliases.json"

    @staticmethod
    def _load_aliases(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
