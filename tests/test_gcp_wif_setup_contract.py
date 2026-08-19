from pathlib import Path

DOC = Path("docs/gcp_wif_setup.md")
WORKFLOW_DIR = Path(".github/workflows")
AUTH_ACTION = "google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093"
WORKFLOW_REF_PREFIX = "Fadhilstat/PanganLens/.github/workflows/"
WORKFLOW_REF_SUFFIX = "@refs/heads/main"


def _authenticated_workflow_refs() -> set[str]:
    refs = set()
    for workflow in sorted(WORKFLOW_DIR.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        if AUTH_ACTION in text:
            refs.add(f"{WORKFLOW_REF_PREFIX}{workflow.name}{WORKFLOW_REF_SUFFIX}")
    return refs


def test_wif_setup_uses_immutable_repository_and_owner_ids():
    text = DOC.read_text(encoding="utf-8")

    assert 'attribute.repository_id == "1335081180"' in text
    assert 'attribute.repository_owner_id == "179431732"' in text
    assert 'attribute.ref == "refs/heads/main"' in text


def test_wif_setup_maps_and_restricts_every_authenticated_workflow_ref():
    text = DOC.read_text(encoding="utf-8")
    workflow_refs = _authenticated_workflow_refs()

    assert "attribute.workflow_ref=assertion.workflow_ref" in text
    assert workflow_refs
    for workflow_ref in workflow_refs:
        assert f'attribute.workflow_ref == "{workflow_ref}"' in text


def test_wif_setup_does_not_document_unknown_workflow_refs():
    text = DOC.read_text(encoding="utf-8")
    documented_refs = {
        line.removeprefix("- `").removesuffix("`")
        for line in text.splitlines()
        if line.startswith(f"- `{WORKFLOW_REF_PREFIX}")
    }

    assert documented_refs == _authenticated_workflow_refs()


def test_wif_setup_keeps_direct_read_only_boundary():
    text = DOC.read_text(encoding="utf-8")

    assert "roles/bigquery.jobUser" in text
    assert "roles/bigquery.dataViewer" in text
    assert "Do not create or upload a service account key file" in text
    assert "production write access stays separate" in text.casefold()
