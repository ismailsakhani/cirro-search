from typing import Any

from pydantic import BaseModel, Field


class SearchResultSchema(BaseModel):
    id: str
    type: str
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


class PipelineDebugSchema(BaseModel):
    classification: dict[str, Any]
    expansions: list[str] = Field(default_factory=list)
    alias_resolution: dict[str, Any] | None = None
    provider: str
    provider_took_ms: int = 0
    pipeline_took_ms: int = 0
    fallback_used: bool = False


class SearchResponseSchema(BaseModel):
    query: str
    mode: str
    results: list[SearchResultSchema]
    debug: PipelineDebugSchema


class HealthResponseSchema(BaseModel):
    status: str
    provider: str
    provider_status: str
    index: str | None = None
