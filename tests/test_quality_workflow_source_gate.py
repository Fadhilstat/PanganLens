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
    probe_job = text.split("  live-pihps-probe:", maxsplit=1)[1]
    job_header = probe_job.split("    steps:", maxsplit=1)[0]
    assert "if: github.event_name != 'schedule'" not in job_header


def test_narrow_unreviewed_price_sample_never_runs_on_daily_schedule():
    text = WORKFLOW.read_text(encoding="utf-8")
    probe_job = text.split("  live-pihps-probe:", maxsplit=1)[1]
    assert "Collect narrow unreviewed PIHPS research sample" in probe_job
    assert "pihps-unreviewed-research-sample" in probe_job
    assert probe_job.count("if: github.event_name != 'schedule'") >= 2
    assert "export_pihps_research_sample.py" in probe_job


def test_probe_evidence_is_uploaded_even_when_probe_fails():
    text = WORKFLOW.read_text(encoding="utf-8")
    probe = text.split("  live-pihps-probe:", maxsplit=1)[1]

    assert "Upload schema-only probe evidence" in probe
    assert "if: always()" in probe
    assert "pihps-probe-summary" in probe
