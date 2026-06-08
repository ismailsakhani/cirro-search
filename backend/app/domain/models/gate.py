from pydantic import BaseModel, Field


class Gate(BaseModel):
    """Gate domain entity."""

    id: str
    airport_code: str
    gate: str
    aliases: list[str] = Field(default_factory=list)
