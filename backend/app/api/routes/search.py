from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_search_pipeline
from app.api.schemas import SearchResponseSchema, SearchResultSchema, PipelineDebugSchema
from app.application.search_service import SearchService
from app.domain.models.entity_type import SearchMode
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.infrastructure.analytics_store import AnalyticsStore, get_analytics_store

router = APIRouter(prefix="/api/v1", tags=["search"])


def get_search_service(
    pipeline: SearchPipeline = Depends(get_search_pipeline),
) -> SearchService:
    return SearchService(pipeline)


@router.get("/suggestions", response_model=SearchResponseSchema)
def suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    service: SearchService = Depends(get_search_service),
    analytics: AnalyticsStore = Depends(get_analytics_store),
) -> SearchResponseSchema:
    response = service.suggest(q, limit=limit)
    analytics.record(q, "autocomplete", result_count=len(response.results))
    return _to_schema(response)


@router.get("/search", response_model=SearchResponseSchema)
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    analytics: AnalyticsStore = Depends(get_analytics_store),
) -> SearchResponseSchema:
    response = service.search(q, limit=limit)
    analytics.record(q, "submit", result_count=len(response.results))
    return _to_schema(response)


@router.get("/analytics/stats")
def analytics_stats(
    analytics: AnalyticsStore = Depends(get_analytics_store),
) -> dict:
    return analytics.stats()


@router.get("/trending")
def trending(
    limit: int = Query(default=10, ge=1, le=50),
    analytics: AnalyticsStore = Depends(get_analytics_store),
) -> dict:
    return {
        "queries": [
            {"query": q, "count": c}
            for q, c in analytics.top_queries(limit)
        ]
    }


def _to_schema(response) -> SearchResponseSchema:
    return SearchResponseSchema(
        query=response.query,
        mode=response.mode,
        results=[SearchResultSchema.model_validate(r.model_dump()) for r in response.results],
        debug=PipelineDebugSchema(**response.debug.model_dump()),
    )
