"""
Phase 3 experiment test runner.

Parametrized over all experiment configs in experiments/configs/.
Each test runs one experiment, asserts the winning variant beats a minimum
pass rate, and prints the comparison table.

Exit criteria:
- All 3 experiments run without error
- Each experiment has a winner with >= 80% pass rate
- Best configs documented in docs/decisions/
"""

from pathlib import Path

import pytest
from elasticsearch import Elasticsearch

from app.application.experiment_service import ExperimentService

pytestmark = pytest.mark.integration

EXPERIMENTS_DIR = Path(__file__).resolve().parents[4] / "experiments" / "configs"
MIN_PASS_RATE = 0.80


def _elasticsearch_available() -> bool:
    try:
        client = Elasticsearch(hosts=["http://localhost:9200"], request_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


def _all_experiment_configs() -> list[Path]:
    return sorted(EXPERIMENTS_DIR.glob("exp-*.yaml"))


@pytest.fixture(scope="module")
def es_client():
    if not _elasticsearch_available():
        pytest.skip("Elasticsearch not available at http://localhost:9200")
    return Elasticsearch(hosts=["http://localhost:9200"], request_timeout=30)


@pytest.mark.parametrize(
    "config_path",
    _all_experiment_configs(),
    ids=lambda p: p.stem,
)
def test_experiment(es_client, config_path: Path, capsys) -> None:
    service = ExperimentService(es_client)
    report = service.run(config_path)

    # Print comparison table (visible with pytest -s)
    with capsys.disabled():
        print(f"\n{'=' * 50}")
        for line in report.summary_lines():
            print(line)

        # Print per-case breakdown for failures
        for variant in report.variants:
            failures = [r for r in variant.case_results if not r.passed]
            if failures:
                print(f"\n  {variant.variant_name} failures:")
                for f in failures:
                    print(
                        f"    query='{f.query}' expected={f.expected} "
                        f"got={f.top_result} rank={f.rank_of_expected}"
                    )
        print(f"{'=' * 50}\n")

    # Assert: at least one variant achieves minimum pass rate
    best_rate = max(v.pass_rate for v in report.variants)
    assert best_rate >= MIN_PASS_RATE, (
        f"Experiment '{report.experiment_id}': best variant only achieves "
        f"{best_rate:.0%} pass rate (minimum {MIN_PASS_RATE:.0%}). "
        f"Variants: {[(v.variant_name, v.pass_rate) for v in report.variants]}"
    )

    # Assert: winning variant is clearly identified
    winner = report.winner()
    assert winner is not None, f"No winner determined for {report.experiment_id}"
