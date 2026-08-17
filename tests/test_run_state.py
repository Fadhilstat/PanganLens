from datetime import UTC, date, datetime

import pytest

from panganlens.warehouse.run_state import BigQueryRunStateManager, PipelineOutcome


class FakeJob:
    def result(self):
        return []


class FakeClient:
    def __init__(self):
        self.calls = []

    def query(self, query, job_config, location):
        self.calls.append((query, job_config, location))
        return FakeJob()


def _outcome(status="SUCCESS", observation_date=date(2026, 8, 17), error_message=None):
    return PipelineOutcome(
        run_id="run-20260817",
        started_at=datetime(2026, 8, 17, 18, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 17, 18, 5, tzinfo=UTC),
        status=status,
        source_observation_date=observation_date,
        rows_received=100,
        rows_clean=98,
        rows_duplicate=2,
        rows_conflict=0,
        rows_quarantined=0,
        error_message=error_message,
    )


def test_success_advances_public_publish_pointer():
    client = FakeClient()
    manager = BigQueryRunStateManager("panganlens-prod", client=client)

    manager.finalize(_outcome())

    query = client.calls[0][0]
    assert "MERGE panganlens_ops.pipeline_run" in query
    assert "MERGE panganlens_ops.publish_state" in query
    assert "source.active_observation_date >= target.active_observation_date" in query


def test_no_new_data_keeps_last_known_good_pointer():
    client = FakeClient()
    manager = BigQueryRunStateManager("panganlens-prod", client=client)

    manager.finalize(_outcome(status="NO_NEW_DATA", observation_date=None))

    query = client.calls[0][0]
    assert "MERGE panganlens_ops.pipeline_run" in query
    assert "MERGE panganlens_ops.publish_state" not in query


@pytest.mark.parametrize("status", ["BLOCKED", "FAILED"])
def test_unsafe_run_never_moves_publish_pointer(status):
    client = FakeClient()
    manager = BigQueryRunStateManager("panganlens-prod", client=client)

    manager.finalize(
        _outcome(
            status=status,
            observation_date=date(2026, 8, 17),
            error_message="quality gate did not pass",
        )
    )

    assert "MERGE panganlens_ops.publish_state" not in client.calls[0][0]


def test_final_status_cannot_change_on_retry():
    query = BigQueryRunStateManager._finalize_query(advance_publish=True)

    assert "pipeline run already finalized with a different status" in query
    assert "AND status != @status" in query


def test_success_requires_observation_date():
    with pytest.raises(ValueError, match="source_observation_date"):
        _outcome(observation_date=None).validate()


def test_blocked_run_requires_reason():
    with pytest.raises(ValueError, match="require error_message"):
        _outcome(status="BLOCKED").validate()


def test_invalid_project_id_is_rejected_before_client_creation():
    with pytest.raises(ValueError, match="project_id"):
        BigQueryRunStateManager("INVALID PROJECT")


def test_query_uses_parameters_instead_of_run_id_interpolation():
    client = FakeClient()
    manager = BigQueryRunStateManager("panganlens-prod", client=client)
    manager.finalize(_outcome())

    query, job_config, _ = client.calls[0]
    assert "run-20260817" not in query
    parameters = {parameter.name: parameter.value for parameter in job_config.query_parameters}
    assert parameters["run_id"] == "run-20260817"
    assert parameters["status"] == "SUCCESS"
