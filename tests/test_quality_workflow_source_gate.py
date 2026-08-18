from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "quality.yml"


def test_live_pihps_probe_is_a_hard_pull_request_gate():
    text = WORKFLOW.read_text(encoding="utf-8")
    probe = text.split("  live-pihps-probe:", maxsplit=1)[1]

    assert "pull_request:" in text
    assert "Probe PIHPS website interface" in probe
    assert "continue-on-error:" not in probe


def test_live_pihps_probe_keeps_daily_1800_wib_schedule():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "0 11 * * *"' in text
    assert "live-pihps-probe:" in text
    assert "if: github.event_name != 'schedule'" not in text.split(
        "  live-pihps-probe:", maxsplit=1
    )[1]


def test_probe_evidence_is_uploaded_even_when_probe_fails():
    text = WORKFLOW.read_text(encoding="utf-8")
    probe = text.split("  live-pihps-probe:", maxsplit=1)[1]

    assert "Upload schema-only probe evidence" in probe
    assert "if: always()" in probe
    assert "pihps-probe-summary" in probe
