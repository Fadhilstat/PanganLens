from argparse import Namespace
from datetime import UTC, date, datetime

from panganlens.cli import build_context, build_request, main
from panganlens.warehouse.run_state import PipelineOutcome


def _args(**overrides):
    values = {
        "project_id": "panganlens-demo",
        "scope": "region",
        "price_type_id": 1,
        "comcat_id": "com_1",
        "province_id": "13",
        "start_date": date(2026, 8, 17),
        "end_date": date(2026, 8, 18),
        "regency_id": ["3171", "3172"],
        "show_regencies": True,
        "show_markets": False,
        "report_type": 1,
        "run_id": "run-fixed",
        "capture_id": "capture-fixed",
        "location": "asia-southeast2",
    }
    values.update(overrides)
    return Namespace(**values)


def test_build_request_preserves_explicit_source_parameters():
    request = build_request(_args())

    assert request.price_type_id == 1
    assert request.comcat_id == "com_1"
    assert request.province_id == "13"
    assert request.regency_ids == ("3171", "3172")
    assert request.start_date == date(2026, 8, 17)
    assert request.end_date == date(2026, 8, 18)


def test_context_uses_request_params_without_hidden_rewrite():
    captured_at = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    request = build_request(_args())
    context = build_context(_args(), request, captured_at)

    assert context.run_id == "run-fixed"
    assert context.capture_id == "capture-fixed"
    assert context.request_parameters == request.as_params()
    assert context.captured_at == captured_at
    assert context.normalized_at == captured_at


def test_main_returns_zero_for_success_and_prints_machine_readable_summary(monkeypatch, capsys):
    outcome = PipelineOutcome(
        run_id="run-1",
        started_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 18, 12, 1, tzinfo=UTC),
        status="SUCCESS",
        source_observation_date=date(2026, 8, 18),
        rows_received=2,
        rows_clean=2,
        rows_duplicate=0,
        rows_conflict=0,
        rows_quarantined=0,
    )
    monkeypatch.setattr("panganlens.cli.run", lambda args: outcome)

    code = main(
        [
            "--project-id",
            "panganlens-demo",
            "--scope",
            "region",
            "--price-type-id",
            "1",
            "--comcat-id",
            "com_1",
            "--province-id",
            "13",
            "--start-date",
            "2026-08-17",
            "--end-date",
            "2026-08-18",
        ]
    )

    assert code == 0
    text = capsys.readouterr().out
    assert '"status":"SUCCESS"' in text
    assert '"run_id":"run-1"' in text


def test_main_returns_nonzero_for_blocked_run(monkeypatch):
    outcome = PipelineOutcome(
        run_id="run-2",
        started_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 18, 12, 1, tzinfo=UTC),
        status="BLOCKED",
        source_observation_date=date(2026, 8, 18),
        rows_received=2,
        rows_clean=1,
        rows_duplicate=0,
        rows_conflict=0,
        rows_quarantined=1,
        error_message="ingestion quality gate blocked promotion",
    )
    monkeypatch.setattr("panganlens.cli.run", lambda args: outcome)

    code = main(
        [
            "--project-id",
            "panganlens-demo",
            "--scope",
            "region",
            "--price-type-id",
            "1",
            "--comcat-id",
            "com_1",
            "--province-id",
            "13",
            "--start-date",
            "2026-08-17",
            "--end-date",
            "2026-08-18",
        ]
    )

    assert code == 2
