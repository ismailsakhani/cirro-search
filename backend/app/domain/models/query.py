from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.models.entity_type import EntityType, SearchMode


class QueryType(StrEnum):
    """Classification of a user search query."""

    AIRPORT_ICAO = "airport_icao"
    AIRPORT_IATA = "airport_iata"
    FLIGHT = "flight"
    DIGITS = "digits"
    GATE = "gate"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class FlightIdentifier(BaseModel):
    """Parsed flight query components."""

    code_type: str
    iata_airline_code: str | None = None
    icao_airline_code: str | None = None
    flight_number: str


class ClassificationResult(BaseModel):
    """Output of the query classifier."""

    query_type: QueryType
    normalized_query: str
    confidence: float = 1.0
    matched_pattern: str | None = None
    flight: FlightIdentifier | None = None
    airport_code: str | None = None
    gate: str | None = None
    digits: str | None = None

    @property
    def entity_type(self) -> EntityType | None:
        mapping = {
            QueryType.AIRPORT_ICAO: EntityType.AIRPORT,
            QueryType.AIRPORT_IATA: EntityType.AIRPORT,
            QueryType.FLIGHT: EntityType.FLIGHT,
            QueryType.DIGITS: EntityType.FLIGHT,
            QueryType.GATE: EntityType.GATE,
        }
        return mapping.get(self.query_type)


class SearchQuery(BaseModel):
    """Normalized search input for the pipeline."""

    raw: str
    normalized: str
    mode: SearchMode = SearchMode.SUBMIT


class AliasResolution(BaseModel):
    """Result of alias lookup for ambiguous or compound queries."""

    matched: bool = False
    entity_id: str | None = None
    entity_type: EntityType | None = None
    expanded_terms: list[str] = Field(default_factory=list)
