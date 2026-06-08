from pydantic import BaseModel, Field


class Flight(BaseModel):
    """Flight domain entity."""

    id: str
    airline: str
    iata_flight: str | None = None
    icao_flight: str | None = None
    flight_number: str
    aliases: list[str] = Field(default_factory=list)
