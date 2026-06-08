from enum import StrEnum


class EntityType(StrEnum):
    """Types of searchable aviation entities."""

    AIRPORT = "airport"
    FLIGHT = "flight"
    GATE = "gate"


class SearchMode(StrEnum):
    """How the pipeline is invoked."""

    AUTOCOMPLETE = "autocomplete"
    SUBMIT = "submit"
