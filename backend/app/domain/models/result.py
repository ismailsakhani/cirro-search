from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.entity_type import EntityType


class SearchResult(BaseModel):
    """A single search result returned by the pipeline."""

    id: str
    type: EntityType
    display: str
    score: float
    iata: str | None = None
    icao: str | None = None
    name: str | None = None
    city: str | None = None
    country: str | None = None
    airline: str | None = None
    airline_name: str | None = None
    iata_flight: str | None = None
    icao_flight: str | None = None
    flight_number: str | None = None
    airport_code: str | None = None
    gate: str | None = None
    matched_fields: list[str] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankedResult(SearchResult):
    rank: int


class PipelineDebug(BaseModel):
    """Debug metadata attached to pipeline responses."""

    classification: dict[str, Any]
    expansions: list[str] = Field(default_factory=list)
    alias_resolution: dict[str, Any] | None = None
    provider: str
    provider_took_ms: int = 0
    pipeline_took_ms: int = 0
    fallback_used: bool = False


class PipelineResponse(BaseModel):
    """Full pipeline output."""

    query: str
    mode: str
    results: list[SearchResult]
    debug: PipelineDebug
