import time

from app.domain.aliases.resolver import AliasResolver
from app.domain.classifier.query_classifier import QueryClassifier
from app.domain.models.entity_type import SearchMode
from app.domain.models.result import PipelineDebug, PipelineResponse
from app.domain.pipeline.stages import (
    build_expansions,
    collect_search_terms,
    normalize_query,
    resolve_entity_type,
)
from app.domain.ranking.basic_ranker import BasicRanker
from app.providers.models import ProviderAutocompleteRequest, ProviderHealth, ProviderSearchRequest
from app.providers.protocol import SearchProvider


class SearchPipeline:
    """Compose domain stages and delegate retrieval to SearchProvider."""

    def __init__(
        self,
        provider: SearchProvider,
        classifier: QueryClassifier | None = None,
        alias_resolver: AliasResolver | None = None,
        ranker: BasicRanker | None = None,
    ) -> None:
        self._provider = provider
        self._classifier = classifier or QueryClassifier()
        self._alias_resolver = alias_resolver or AliasResolver()
        self._ranker = ranker or BasicRanker()

    def health(self) -> ProviderHealth:
        return self._provider.get_health()

    def run(self, query: str, mode: SearchMode = SearchMode.SUBMIT, *, limit: int = 10) -> PipelineResponse:
        started = time.perf_counter()
        normalized = normalize_query(query)
        classification = self._classifier.classify(normalized)
        expansions = build_expansions(classification)
        alias = self._alias_resolver.resolve(normalized, classification)
        entity_type = resolve_entity_type(classification, alias)
        search_terms = collect_search_terms(normalized, expansions, alias)

        provider_response = self._search_provider(
            query=normalized,
            mode=mode,
            entity_type=entity_type,
            search_terms=search_terms,
            limit=limit,
        )
        fallback_used = False

        if not provider_response.hits and mode == SearchMode.SUBMIT:
            fallback_response = self._search_provider(
                query=normalized,
                mode=mode,
                entity_type=None,
                search_terms=search_terms,
                limit=limit,
            )
            if fallback_response.hits:
                provider_response = fallback_response
                fallback_used = True

        ranked = self._ranker.rank(
            provider_response.hits,
            classification,
            normalized,
            preferred_entity_id=alias.entity_id,
        )
        results = self._ranker.to_search_results(ranked)

        pipeline_ms = int((time.perf_counter() - started) * 1000)

        return PipelineResponse(
            query=normalized,
            mode=mode.value,
            results=results,
            debug=PipelineDebug(
                classification={
                    "query_type": classification.query_type.value,
                    "normalized_query": classification.normalized_query,
                    "matched_pattern": classification.matched_pattern,
                    "entity_type": entity_type.value if entity_type else None,
                },
                expansions=search_terms,
                alias_resolution={
                    "matched": alias.matched,
                    "entity_id": alias.entity_id,
                    "entity_type": alias.entity_type.value if alias.entity_type else None,
                }
                if alias.matched
                else None,
                provider=provider_response.provider,
                provider_took_ms=provider_response.took_ms,
                pipeline_took_ms=pipeline_ms,
                fallback_used=fallback_used,
            ),
        )

    def _search_provider(
        self,
        query: str,
        mode: SearchMode,
        entity_type,
        search_terms: list[str],
        limit: int,
    ):
        if mode == SearchMode.AUTOCOMPLETE:
            return self._provider.autocomplete(
                ProviderAutocompleteRequest(
                    query=query,
                    entity_type=entity_type,
                    expanded_terms=search_terms,
                    limit=limit,
                )
            )
        return self._provider.search(
            ProviderSearchRequest(
                query=query,
                mode=mode,
                entity_type=entity_type,
                expanded_terms=search_terms,
                limit=limit,
            )
        )
