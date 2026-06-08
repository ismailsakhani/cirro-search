from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.entity_type import EntityType, SearchMode


class SearchDocument(BaseModel):
    """Unified document shape indexed by any SearchProvider implementation."""

    id: str
    type: EntityType
    display: str
    searchable_text: str
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
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderSearchRequest(BaseModel):
    """Request passed to SearchProvider.search() after pipeline preprocessing."""

    query: str
    mode: SearchMode = SearchMode.SUBMIT
    entity_type: EntityType | None = None
    expanded_terms: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)


class ProviderAutocompleteRequest(BaseModel):
    """Request passed to SearchProvider.autocomplete() for dropdown suggestions."""

    query: str
    entity_type: EntityType | None = None
    expanded_terms: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)


class ProviderHit(BaseModel):
    """A single raw hit returned by the search engine before domain ranking."""

    document: SearchDocument
    score: float
    matched_fields: list[str] = Field(default_factory=list)


class ProviderSearchResponse(BaseModel):
    """Raw response from a SearchProvider search or autocomplete call."""

    hits: list[ProviderHit] = Field(default_factory=list)
    took_ms: int = 0
    provider: str


class BulkIndexResult(BaseModel):
    """Result of a bulk indexing operation."""

    indexed: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)


class ProviderHealthStatus(StrEnum):
    """Health state of the underlying search engine."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ProviderHealth(BaseModel):
    """Health report from a SearchProvider implementation."""

    status: ProviderHealthStatus
    provider: str
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
