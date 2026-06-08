from pydantic import BaseModel, Field


class Airport(BaseModel):
    """Airport domain entity."""

    id: str
    iata: str | None = None
    icao: str | None = None
    name: str
    city: str | None = None
    country: str | None = None
    aliases: list[str] = Field(default_factory=list)
