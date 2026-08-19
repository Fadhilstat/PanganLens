from pathlib import Path

DOC = Path("docs/gcp_wif_setup.md")
WORKFLOW_REFS = (
    "Fadhilstat/PanganLens/.github/workflows/gcp_auth_smoke.yml@refs/heads/main",
    "Fadhilstat/PanganLens/.github/workflows/bigquery_readiness.yml@refs/heads/main",
    "Fadhilstat/PanganLens/.github/workflows/dashboard_pages.yml@refs/heads/main",
)


def test_wif_setup_uses_immutable_repository_and_owner_ids():
    text = DOC.read_text(encoding="utf-8")

    assert 'attribute.repository_id == "1335081180"' in text
    assert 'attribute.repository_owner_id == "179431732"' in text
    assert 'attribute.ref == "refs/heads/main"' in text


def test_wif_setup_maps_and_restricts_workflow_ref():
    text = DOC.read_text(encoding="utf-8")

    assert "attribute.workflow_ref=assertion.workflow_ref" in text
    for workflow_ref in WORKFLOW_REFS:
        assert f'attribute.workflow_ref == "{workflow_ref}"' in text


def test_wif_setup_keeps_direct_read_only_boundary():
    text = DOC.read_text(encoding="utf-8")

    assert "roles/bigquery.jobUser" in text
    assert "roles/bigquery.dataViewer" in text
    assert "Do not create or upload a service account key file" in text
    assert "production write access stays separate" in text.casefold()
