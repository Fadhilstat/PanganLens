from datetime import UTC, date, datetime

import pytest

from panganlens.ingestion.orchestration import IngestionContext, IngestionSummary
from panganlens.pipeline import finalize_capture_run
from panganlens.warehouse.promotion import PromotionBlockedError


class FakePromotionRunner:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def promote(self, run_id, ingestion_eligible):
        self.calls.append((run_id, ingestion_eligible))
        if self.error is not None:
            raise self.error
        return object()


class FakeStateManager:
    def __init__(self):
        self.outcomes = []

    def finalize(self, outcome):
        self.outcomes.append(outcome)


def _context():
    return IngestionContext(
        run_id="run-1",
        capture_id="capture-1",
        source_method="pihps_json",
        scope="region",
        captured_at=datetime(2026, 8, 18, 0, 0, tzinfo=UTC),
        normalized_at=datetime(2026, 8, 18, 0, 1, tzinfo=UTC),
        request_parameters={},
        start_date=date(2026, 8, 17),
        end_date=date(2026, 8, 17),
    )


def _summary(**overrides):
    values = {
        "parsed_points": 3,
        "missing_price_cells": 1,
        "staged_rows": 3,
        "exact_duplicates": 0,
        "conflict_rows": 0,
        "quarantined_rows": 0,
        "latest_observation_date": date(2026, 8, 17),
        "promotion_eligible": True,
    }
    values.update(overrides)
    return IngestionSummary(**values)


def _finished_at():
    return datetime(2026, 8, 18, 0, 5, tzinfo=UTC)


def test_success_promotes_and_advances_terminal_state():
    promotion = FakePromotionRunner()
    states = FakeStateManager()

    outcome = finalize_capture_run(
        _summary(),
        _context(),
        promotion,
        states,
        _finished_at(),
    )

    assert outcome.status == "SUCCESS"
    assert outcome.source_observation_date == date(2026, 8, 17)
    assert outcome.rows_received == 4
    assert outcome.rows_clean == 3
    assert outcome.rows_conflict == 0
    assert promotion.calls == [("run-1", True)]
    assert states.outcomes == [outcome]


def test_no_new_data_skips_promotion_and_keeps_publish_pointer_unchanged():
    promotion = FakePromotionRunner()
    states = FakeStateManager()

    outcome = finalize_capture_run(
        _summary(
            parsed_points=0,
            missing_price_cells=3,
            staged_rows=0,
            latest_observation_date=None,
        ),
        _context(),
        promotion,
        states,
        _finished_at(),
    )

    assert outcome.status == "NO_NEW_DATA"
    assert outcome.rows_received == 3
    assert promotion.calls == []
    assert states.outcomes == [outcome]


def test_quarantined_rows_block_promotion():
    promotion = FakePromotionRunner()
    states = FakeStateManager()

    outcome = finalize_capture_run(
        _summary(quarantined_rows=1, promotion_eligible=False),
        _context(),
        promotion,
        states,
        _finished_at(),
    )

    assert outcome.status == "BLOCKED"
    assert outcome.rows_clean == 2
    assert promotion.calls == []
    assert states.outcomes == [outcome]


def test_staging_conflicts_are_counted_and_block_promotion():
    promotion = FakePromotionRunner()
    states = FakeStateManager()

    outcome = finalize_capture_run(
        _summary(
            staged_rows=0,
            conflict_rows=2,
            promotion_eligible=False,
        ),
        _context(),
        promotion,
        states,
        _finished_at(),
    )

    assert outcome.status == "BLOCKED"
    assert outcome.rows_conflict == 2
    assert outcome.rows_clean == 0
    assert promotion.calls == []
    assert states.outcomes == [outcome]


def test_precheck_block_is_recorded_as_blocked():
    promotion = FakePromotionRunner(PromotionBlockedError("duplicate gate failed"))
    states = FakeStateManager()

    outcome = finalize_capture_run(
        _summary(),
        _context(),
        promotion,
        states,
        _finished_at(),
    )

    assert outcome.status == "BLOCKED"
    assert outcome.error_message == "duplicate gate failed"
    assert states.outcomes == [outcome]


def test_unexpected_promotion_error_is_recorded_before_reraising():
    promotion = FakePromotionRunner(RuntimeError("warehouse unavailable"))
    states = FakeStateManager()

    with pytest.raises(RuntimeError, match="warehouse unavailable"):
        finalize_capture_run(
            _summary(),
            _context(),
            promotion,
            states,
            _finished_at(),
        )

    assert len(states.outcomes) == 1
    assert states.outcomes[0].status == "FAILED"
    assert states.outcomes[0].error_message == "promotion failed: RuntimeError"


def test_finished_at_requires_timezone():
    with pytest.raises(ValueError, match="timezone-aware"):
        finalize_capture_run(
            _summary(),
            _context(),
            FakePromotionRunner(),
            FakeStateManager(),
            datetime(2026, 8, 18, 0, 5),
        )
