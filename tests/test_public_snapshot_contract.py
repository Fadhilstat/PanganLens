"""Integration checks for the dependency-free static Pages snapshot validator."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_public_snapshot.py"
CHECKED_IN = ROOT / "website" / "data" / "dashboard.json"


def _run_validator(path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )


def _state(status="SUCCESS", day="2026-10-09", freshness="Terkini"):
    return {
        "active_run_status": status,
        "active_observation_date": day,
        "freshness_label": freshness,
    }


def _payload(state=None, national=None, regions=None, version=1):
    return {
        "schema_version": version,
        "publish_state": state,
        "national_prices": national if national is not None else [],
        "province_prices": regions if regions is not None else [],
    }


def _run_payload(tmp_path, payload):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return _run_validator(path)


def test_checked_in_empty_snapshot_is_safe_to_deploy():
    result = _run_validator(CHECKED_IN)
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_valid_published_snapshot_passes_without_live_data(tmp_path):
    payload = _payload(state=_state(freshness="Data lama"),
                       national=[{"price_idr": "25000"}])
    assert _run_payload(tmp_path, payload).returncode == 0


def test_nonempty_prices_without_publish_state_are_rejected(tmp_path):
    for key in ("national_prices", "province_prices"):
        payload = _payload()
        payload[key] = [{"price_idr": "25000"}]
        result = _run_payload(tmp_path, payload)
        assert result.returncode != 0
        assert "active publish state" in result.stderr


def test_failed_run_or_invalid_active_date_is_rejected(tmp_path):
    for state in (_state(status="FAILED"), _state(day="2026-02-30"),
                  _state(day="not-a-date"), _state(freshness="unknown")):
        assert _run_payload(tmp_path, _payload(state=state)).returncode != 0


def test_wrong_version_or_missing_array_is_rejected(tmp_path):
    for payload in (
        _payload(version=2),
        {"schema_version": 1, "publish_state": None, "national_prices": []},
        {"schema_version": 1, "publish_state": None, "national_prices": {},
         "province_prices": []},
    ):
        assert _run_payload(tmp_path, payload).returncode != 0


def test_malformed_json_is_rejected(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text("{malformed", encoding="utf-8")
    assert _run_validator(path).returncode != 0
