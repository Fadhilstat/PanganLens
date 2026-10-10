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
        "schedule:",
        "curl ",
        "wget ",
    )
    assert all(item not in text for item in forbidden)
    assert "stage: verify" in text
    assert "- verify" in text


def test_gitlab_pages_is_quality_gated_and_default_branch_only():
    text = GITLAB_CI.read_text(encoding="utf-8")
    job = text.split("deploy_portfolio_site:", maxsplit=1)[1]

    assert "stage: deploy" in job
    assert 'needs: ["python_quality", "frontend_quality"]' in job
    assert "pages:" in job
    assert "publish: website" in job
    assert "CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in job
    assert "test -s website/index.html" in job
    assert "test -s website/data/dashboard.json" in job
    assert "GCP_" not in job
    assert "python -m pip install" not in job


def test_gitlab_frontend_quality_uses_node_without_npm_install():
    text = GITLAB_CI.read_text(encoding="utf-8")
    job = text.split("frontend_quality:", maxsplit=1)[1].split(
        "deploy_portfolio_site:", maxsplit=1
    )[0]
    assert "node:22-bookworm-slim" in job
    assert "node --check website/app.js" in job
    assert "node --check website/dashboard_metrics.js" in job
    assert "node --check website/price_playground.js" in job
    assert "node --test tests/dashboard_metrics.test.cjs tests/price_playground.test.cjs" in job
    assert "npm install" not in job


def test_anonymous_smoke_follows_pages_publish_and_is_nonblocking():
    ci = GITLAB_CI.read_text(encoding="utf-8")
    assert "- smoke" in ci
    assert "public_site_smoke:" in ci
    job = ci.split("public_site_smoke:", 1)[1]
    assert "stage: smoke" in job
    assert 'needs: ["deploy_portfolio_site"]' in job
    assert "allow_failure: true" in job
    assert "scripts/check_public_site.py" in job
    assert "CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in job
    assert "GCP_" not in job
