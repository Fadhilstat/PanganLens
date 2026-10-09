from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITLAB_CI = ROOT / ".gitlab-ci.yml"
GITHUB_QUALITY = ROOT / ".github" / "workflows" / "quality.yml"


def test_gitlab_ci_is_limited_to_merge_requests_and_default_branch():
    text = GITLAB_CI.read_text(encoding="utf-8")

    assert 'CI_PIPELINE_SOURCE == "merge_request_event"' in text
    assert 'CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH' in text
    assert "- when: never" in text
    assert "python:3.11-slim-bookworm" in text
    assert "timeout: 15m" in text


def test_gitlab_ci_reuses_github_quality_checks_and_constraints():
    gitlab = GITLAB_CI.read_text(encoding="utf-8")
    github = GITHUB_QUALITY.read_text(encoding="utf-8")

    commands = (
        'python -m pip install -c constraints/ci.txt -e ".[dev]"',
        "pytest -q",
        "ruff check src scripts tests",
        "python -m compileall -q src scripts tests",
    )
    for command in commands:
        assert command in gitlab
        assert command in github


def test_gitlab_ci_never_inherits_cloud_or_deploy_authority():
    text = GITLAB_CI.read_text(encoding="utf-8").lower()
    forbidden = (
        "gcp_project_id",
        "gcp_wif_provider",
        "id_tokens:",
        "credentials_json",
        "service_account_key",
        "google-github-actions",
        "include:",
        "trigger:",
        "deploy:",
        "pages:",
        "schedule:",
        "curl ",
        "wget ",
    )
    assert all(item not in text for item in forbidden)
    assert "stage: verify" in text
    assert "- verify" in text
