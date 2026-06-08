"""
Phase 3 experiment service.

Creates isolated ES indices per experiment variant, seeds data, runs the evaluation
pipeline, and returns a structured comparison report.

Each variant gets index: exp-{exp_id}-{variant_name}-{run_id}
Indices are cleaned up after comparison unless keep=True.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from elasticsearch import Elasticsearch

from app.application.seed_service import SeedService
from app.domain.models.entity_type import SearchMode
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.domain.ranking.basic_ranker import BasicRanker
from app.infrastructure.config import Settings
from app.providers.elasticsearch.client import ensure_index
from app.providers.elasticsearch.index_config import INDEX_MAPPINGS, INDEX_SETTINGS
from app.providers.elasticsearch.provider import ElasticsearchProvider
from app.providers.models import ProviderHit, ProviderSearchRequest, ProviderSearchResponse, SearchDocument


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CaseResult:
    query: str
    mode: str
    expected: dict
    passed: bool
    top_result: dict | None
    rank_of_expected: int | None  # 1-based; None if not in top-N


@dataclass
class VariantReport:
    variant_name: str
    pass_count: int
    total_count: int
    case_results: list[CaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.pass_count / self.total_count if self.total_count else 0.0


@dataclass
class ExperimentReport:
    experiment_id: str
    experiment_name: str
    axis: str
    variants: list[VariantReport] = field(default_factory=list)

    def winner(self) -> str | None:
        if not self.variants:
            return None
        best = max(self.variants, key=lambda v: (v.pass_rate, v.pass_count))
        return best.variant_name

    def summary_lines(self) -> list[str]:
        lines = [
            f"Experiment: {self.experiment_id} — {self.experiment_name}",
            f"Axis: {self.axis}",
            "",
            f"{'Variant':<20} {'Pass':>6} {'Total':>6} {'Rate':>8}",
            "-" * 44,
        ]
        for v in self.variants:
            lines.append(
                f"{v.variant_name:<20} {v.pass_count:>6} {v.total_count:>6} {v.pass_rate:>7.0%}"
            )
        lines.append("")
        lines.append(f"Winner: {self.winner()}")
        return lines


# ---------------------------------------------------------------------------
# Query builders for experiment variants
# ---------------------------------------------------------------------------

def _build_search_query_variant(
    query: str,
    entity_type,
    expanded_terms: list[str],
    limit: int,
    *,
    fuzziness: str = "AUTO",
    code_boost: int = 8,
    flight_boost: int = 8,
    searchable_boost: int = 4,
    aliases_boost: int = 3,
    name_boost: int = 3,
) -> dict:
    from app.providers.elasticsearch.queries import _collect_query_terms, _entity_type_filter
    terms = _collect_query_terms(query, expanded_terms)
    should_clauses = []
    for term in terms:
        should_clauses.append({
            "multi_match": {
                "query": term,
                "fields": [
                    f"iata^{code_boost}",
                    f"icao^{code_boost}",
                    f"iata_flight^{flight_boost}",
                    f"icao_flight^{flight_boost}",
                    f"flight_number^{flight_boost - 2}",
                    f"gate^{code_boost}",
                    f"airport_code^{code_boost - 2}",
                    f"searchable_text^{searchable_boost}",
                    f"aliases^{aliases_boost}",
                    f"name^{name_boost}",
                    "display^2",
                ],
                "type": "best_fields",
                "fuzziness": fuzziness,
            }
        })
    return {
        "size": limit,
        "query": {
            "bool": {
                "filter": _entity_type_filter(entity_type),
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        },
    }


# ---------------------------------------------------------------------------
# Variant ES providers
# ---------------------------------------------------------------------------

class _VariantElasticsearchProvider(ElasticsearchProvider):
    """ES provider with overridable query builder for experiment variants."""

    def __init__(self, *, query_kwargs: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._query_kwargs = query_kwargs

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResponse:
        body = _build_search_query_variant(
            query=request.query,
            entity_type=request.entity_type,
            expanded_terms=request.expanded_terms,
            limit=request.limit,
            **self._query_kwargs,
        )
        return self._execute(body)


class _EsScoreRanker(BasicRanker):
    """Ranker that skips all domain boosts — returns ES hits in ES score order."""

    def _score_hit(self, hit, classification, query_lower, query_compact, *, preferred_entity_id):
        return hit.score, ["es_score_only"]


class _PopularityFirstRanker(BasicRanker):
    """Ranker that sorts primarily by popularity metadata, then ES score."""

    def _score_hit(self, hit, classification, query_lower, query_compact, *, preferred_entity_id):
        popularity = hit.document.metadata.get("popularity", 0)
        score = float(popularity) * 10 + hit.score
        return score, ["popularity_first", "es_score"]


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _load_cases(suite_names: list[str]) -> list[dict]:
    eval_dir = Path(__file__).resolve().parents[3] / "evaluation" / "cases"
    cases: list[dict] = []
    seen: set[tuple] = set()
    name_map = {"phase1": "phase1.yaml", "regression": "regression.yaml"}
    for suite in suite_names:
        path = eval_dir / name_map[suite]
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        for c in data["cases"]:
            key = (c["query"], c.get("mode", "submit"))
            if key not in seen:
                seen.add(key)
                cases.append(c)
    return cases


def _result_matches(result, expect: dict) -> bool:
    if result.type.value != expect["type"]:
        return False
    for field_name, value in expect.items():
        if field_name in ("type", "note"):
            continue
        if field_name == "airport":
            if result.airport_code != value:
                return False
            continue
        if getattr(result, field_name, None) != value:
            return False
    return True


def _rank_of_expected(results, expect: dict) -> int | None:
    for i, r in enumerate(results, start=1):
        if _result_matches(r, expect):
            return i
    return None


# ---------------------------------------------------------------------------
# ExperimentService
# ---------------------------------------------------------------------------

class ExperimentService:
    """
    Run one experiment config against the full evaluation suite.

    Usage:
        service = ExperimentService(es_client)
        report = service.run(config_path)
        for line in report.summary_lines():
            print(line)
    """

    def __init__(self, client: Elasticsearch, seed_dir: Path | None = None) -> None:
        self._client = client
        self._seed_dir = seed_dir

    def run(self, config_path: Path, *, keep_indices: bool = False) -> ExperimentReport:
        with config_path.open(encoding="utf-8") as fh:
            config = yaml.safe_load(fh)

        exp_id = config["id"]
        run_id = uuid.uuid4().hex[:6]
        cases = _load_cases(config["evaluation"]["suites"])
        axis = config["axis"]

        report = ExperimentReport(
            experiment_id=exp_id,
            experiment_name=config["name"],
            axis=axis,
        )

        for variant in config["variants"]:
            index_name = f"{exp_id}-{variant['name']}-{run_id}"
            pipeline = self._build_pipeline(axis, variant, index_name)
            variant_report = self._evaluate(variant["name"], pipeline, cases)
            report.variants.append(variant_report)

            if not keep_indices:
                self._client.indices.delete(index=index_name, ignore_unavailable=True)

        return report

    def _build_pipeline(self, axis: str, variant: dict, index_name: str) -> SearchPipeline:
        settings = Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index=index_name,
        )
        self._client.indices.delete(index=index_name, ignore_unavailable=True)
        ensure_index(self._client, index_name)

        if axis == "fuzzy_tolerance":
            provider = _VariantElasticsearchProvider(
                client=self._client,
                settings=settings,
                auto_create_index=False,
                query_kwargs={"fuzziness": variant["fuzziness"]},
            )
            ranker = BasicRanker()

        elif axis == "field_weights":
            provider = _VariantElasticsearchProvider(
                client=self._client,
                settings=settings,
                auto_create_index=False,
                query_kwargs={
                    "fuzziness": "AUTO",
                    "code_boost": variant["code_boost"],
                    "flight_boost": variant["flight_boost"],
                    "searchable_boost": variant["searchable_boost"],
                    "aliases_boost": variant["aliases_boost"],
                    "name_boost": variant["name_boost"],
                },
            )
            ranker = BasicRanker()

        elif axis == "ranking_strategy":
            provider = ElasticsearchProvider(
                client=self._client,
                settings=settings,
                auto_create_index=False,
            )
            strategy = variant["strategy"]
            if strategy == "es_score":
                ranker = _EsScoreRanker()
            elif strategy == "popularity_first":
                ranker = _PopularityFirstRanker()
            else:
                ranker = BasicRanker()

        else:
            raise ValueError(f"Unknown experiment axis: {axis}")

        SeedService(provider, seed_dir=self._seed_dir).seed()
        self._client.indices.refresh(index=index_name)

        return SearchPipeline(provider=provider, ranker=ranker)

    def _evaluate(
        self, variant_name: str, pipeline: SearchPipeline, cases: list[dict]
    ) -> VariantReport:
        passed = 0
        case_results: list[CaseResult] = []

        for case in cases:
            mode = SearchMode(case.get("mode", "submit"))
            try:
                response = pipeline.run(case["query"], mode=mode, limit=10)
                results = response.results
                top_passed = bool(results) and _result_matches(results[0], case["expect"])
                top = results[0] if results else None
                rank = _rank_of_expected(results, case["expect"]) if results else None
            except Exception as exc:
                top_passed = False
                top = None
                rank = None

            if top_passed:
                passed += 1

            case_results.append(CaseResult(
                query=case["query"],
                mode=case.get("mode", "submit"),
                expected=case["expect"],
                passed=top_passed,
                top_result={
                    "type": top.type.value,
                    "iata": top.iata,
                    "iata_flight": top.iata_flight,
                    "gate": top.gate,
                    "score": top.score,
                } if top else None,
                rank_of_expected=rank,
            ))

        return VariantReport(
            variant_name=variant_name,
            pass_count=passed,
            total_count=len(cases),
            case_results=case_results,
        )
