"""
Phase 4 — ES vs Baseline provider comparison.

Runs all evaluation cases against both providers and prints a side-by-side table.
Identifies cases where ES wins, baseline wins, or both pass/fail.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from app.application.seed_service import SeedService
from app.domain.models.entity_type import SearchMode
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.infrastructure.config import Settings
from app.providers.baseline.provider import BaselineProvider
from elasticsearch import Elasticsearch

from app.providers.elasticsearch.client import ensure_index
from app.providers.elasticsearch.provider import ElasticsearchProvider


def _load_all_cases() -> list[dict]:
    eval_dir = Path(__file__).resolve().parents[3] / "evaluation" / "cases"
    cases = []
    seen: set[tuple] = set()
    for fname in ("phase1.yaml", "regression.yaml"):
        with (eval_dir / fname).open() as fh:
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
    for field, value in expect.items():
        if field in ("type", "note"):
            continue
        if field == "airport":
            if result.airport_code != value:
                return False
            continue
        if getattr(result, field, None) != value:
            return False
    return True


def _passes(pipeline: SearchPipeline, case: dict) -> tuple[bool, str]:
    try:
        mode = SearchMode(case.get("mode", "submit"))
        response = pipeline.run(case["query"], mode=mode, limit=5)
        if not response.results:
            return False, "no_results"
        top = response.results[0]
        if _result_matches(top, case["expect"]):
            return True, "pass"
        return False, f"got type={top.type.value} iata={top.iata} flight={top.iata_flight}"
    except Exception as e:
        return False, str(e)


def main() -> None:
    import uuid

    client = Elasticsearch(hosts=["http://localhost:9200"], request_timeout=10)

    # ES pipeline
    test_index = f"cirro-compare-{uuid.uuid4().hex[:6]}"
    settings = Settings(elasticsearch_url="http://localhost:9200", elasticsearch_index=test_index)
    client.indices.delete(index=test_index, ignore_unavailable=True)
    ensure_index(client, test_index)
    es_provider = ElasticsearchProvider(client=client, settings=settings, auto_create_index=False)
    SeedService(es_provider).seed()
    client.indices.refresh(index=test_index)
    es_pipeline = SearchPipeline(provider=es_provider)

    # Baseline pipeline
    baseline_provider = BaselineProvider()
    SeedService(baseline_provider).seed()
    baseline_pipeline = SearchPipeline(provider=baseline_provider)

    cases = _load_all_cases()

    es_wins = []
    baseline_wins = []
    both_pass = []
    both_fail = []

    print(f"\n{'Query':<25} {'Mode':<12} {'ES':<8} {'Baseline':<8} {'Outcome'}")
    print("-" * 75)

    for case in cases:
        q = case["query"]
        mode = case.get("mode", "submit")
        es_ok, es_msg = _passes(es_pipeline, case)
        bl_ok, bl_msg = _passes(baseline_pipeline, case)

        es_sym = "✓" if es_ok else "✗"
        bl_sym = "✓" if bl_ok else "✗"

        if es_ok and bl_ok:
            outcome = "both pass"
            both_pass.append(q)
        elif es_ok and not bl_ok:
            outcome = f"ES wins  ← {bl_msg}"
            es_wins.append(q)
        elif bl_ok and not es_ok:
            outcome = f"baseline wins ← {es_msg}"
            baseline_wins.append(q)
        else:
            outcome = "both fail"
            both_fail.append(q)

        print(f"{q:<25} {mode:<12} {es_sym:<8} {bl_sym:<8} {outcome}")

    print("\n" + "=" * 75)
    print(f"Total cases: {len(cases)}")
    print(f"Both pass:    {len(both_pass)}")
    print(f"ES wins:      {len(es_wins)}  {es_wins}")
    print(f"Baseline wins:{len(baseline_wins)}  {baseline_wins}")
    print(f"Both fail:    {len(both_fail)}  {both_fail}")
    print(f"\nES pass rate:       {(len(both_pass) + len(es_wins)) / len(cases):.0%}")
    print(f"Baseline pass rate: {(len(both_pass) + len(baseline_wins)) / len(cases):.0%}")

    client.indices.delete(index=test_index, ignore_unavailable=True)


if __name__ == "__main__":
    main()
