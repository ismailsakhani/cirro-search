from app.domain.models.entity_type import SearchMode
from app.domain.models.result import PipelineResponse
from app.domain.pipeline.search_pipeline import SearchPipeline


class SearchService:
    """Application use case for search operations."""

    def __init__(self, pipeline: SearchPipeline) -> None:
        self._pipeline = pipeline

    def suggest(self, query: str, *, limit: int = 10) -> PipelineResponse:
        return self._pipeline.run(query, mode=SearchMode.AUTOCOMPLETE, limit=limit)

    def search(self, query: str, *, limit: int = 10) -> PipelineResponse:
        return self._pipeline.run(query, mode=SearchMode.SUBMIT, limit=limit)
