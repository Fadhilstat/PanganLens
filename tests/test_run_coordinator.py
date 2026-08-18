from datetime import UTC, date, datetime

import pytest

from panganlens.ingestion.orchestration import IngestionContext, IngestionSummary
from panganlens.ingestion.pihps_interface import GridRequest
from panganlens.run_coordinator import execute_grid_run


class FakeSourceClient:
    def __init__(self, source=None, error=None):
        self.source = source
        self.error = error
        self.calls = []

    def fetch_grid_capture(self, request):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.source


class FakeStateManager:
    def __init__(self):
        self.outcomes = []

    def finalize(self, outcome):
        self.outcomes.append(outcome)


class FakePromotionRunner:
    def __init__(self):
        self.calls = []

    def promote(self, run_id, ingestion_eligible):
        self.calls.append((run_id, ingestion_eligible))
        return object()


def _request():
    return GridRequest(
        price_type_id=1,
        comcat_id="com_1",
        province_id="13",
        start_date=date(2026, 8, 17),
        end_date=date(2026, 8, 17),
    )


def _context(**overrides):
    values = {
        "run_id": "run-1",
        "capture_id": "capture-1",
        "source_method": "pihps_json",
        "scope": "region",
        "captured_at": datetime(2026, 8, 18, 11, 0, tzinfo=UTC),
        "normalized_at": datetime(2026, 8, 18, 11, 1, tzinfo=UTC),
        "request_parameters": _request().as_params(),
        "start_date": date(2026, 8, 17),
        "end_date": date(2026, 8, 17),
    }
    values.update(overrides)
    return IngestionContext(**values)


def _summary():
    return IngestionSummary(
        parsed_points=2,
        missing_price_cells=0,
        staged_rows=2,
        exact_duplicates=0,
        conflict_rows=0,
        quarantined_rows=0,
        latest_observation_date=date(2026, 8, 17),
        promotion_eligible=True,
    )


def _finished_at():
    return datetime(2026, 8, 18, 11, 5, tzinfo=UTC)


def test_success_connects_fetch_ingestion_promotion_and_final_state(monkeypatch):
    source = object()
    source_client = FakeSourceClient(source=source)
    state_manager = FakeStateManager()
    promotion_runner = FakePromotionRunner()
    ingestion_calls = []

    def fake_ingest(source_arg, context, resolver, raw_warehouse, staging_writer):
        ingestion_calls.append(
            (source_arg, context, resolver, raw_warehouse, staging_writer)
        )
        return _summary()

    monkeypatch.setattr("panganlens.run_coordinator.ingest_grid_capture", fake_ingest)

    resolver = object()
    raw_warehouse = object()
    staging_writer = object()
    outcome = execute_grid_run(
        _request(),
        _context(),
        source_client,
        resolver,
        raw_warehouse,
        staging_writer,
        promotion_runner,
        state_manager,
        _finished_at(),
    )

    assert source_client.calls == [_request()]
    assert ingestion_calls == [
        (source, _context(), resolver, raw_warehouse, staging_writer)
    ]
    assert promotion_runner.calls == [("run-1", True)]
    assert outcome.status == "SUCCESS"
    assert state_manager.outcomes == [outcome]


def test_source_failure_is_finalized_as_failed_and_reraised():
    source_client = FakeSourceClient(error=RuntimeError("source unavailable"))
    state_manager = FakeStateManager()

    with pytest.raises(RuntimeError, match="source unavailable"):
        execute_grid_run(
            _request(),
            _context(),
            source_client,
            object(),
            object(),
            object(),
            FakePromotionRunner(),
            state_manager,
            _finished_at(),
        )

    assert len(state_manager.outcomes) == 1
    outcome = state_manager.outcomes[0]
    assert outcome.status == "FAILED"
    assert outcome.error_message == "ingestion failed: RuntimeError"
    assert outcome.rows_received == 0


def test_ingestion_failure_after_fetch_is_finalized_as_failed(monkeypatch):
    source_client = FakeSourceClient(source=object())
    state_manager = FakeStateManager()

    def fail_ingest(*args, **kwargs):
        raise ValueError("parser rejected source")

    monkeypatch.setattr("panganlens.run_coordinator.ingest_grid_capture", fail_ingest)

    with pytest.raises(ValueError, match="parser rejected source"):
        execute_grid_run(
            _request(),
            _context(),
            source_client,
            object(),
            object(),
            object(),
            FakePromotionRunner(),
            state_manager,
            _finished_at(),
        )

    assert state_manager.outcomes[0].status == "FAILED"
    assert state_manager.outcomes[0].error_message == "ingestion failed: ValueError"


def test_request_context_mismatch_blocks_before_network_call():
    source_client = FakeSourceClient(source=object())
    context = _context(
        request_parameters={**_request().as_params(), "province_id": "99"}
    )

    with pytest.raises(ValueError, match="province_id"):
        execute_grid_run(
            _request(),
            context,
            source_client,
            object(),
            object(),
            object(),
            FakePromotionRunner(),
            FakeStateManager(),
            _finished_at(),
        )

    assert source_client.calls == []


def test_finished_at_requires_timezone_before_source_call():
    source_client = FakeSourceClient(source=object())

    with pytest.raises(ValueError, match="timezone-aware"):
        execute_grid_run(
            _request(),
            _context(),
            source_client,
            object(),
            object(),
            object(),
            FakePromotionRunner(),
            FakeStateManager(),
            datetime(2026, 8, 18, 11, 5),
        )

    assert source_client.calls == []
