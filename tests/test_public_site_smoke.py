"""No-network tests for the anonymous Pages smoke workflow."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import urlparse

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_public_site.py"
SPEC = spec_from_file_location("panganlens_public_site_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PUBLIC_SITE = MODULE.PUBLIC_SITE
verify_public_site = MODULE.verify_public_site

HTML = f"""<html><head><title>PanganLens Indonesia</title>
<link rel="canonical" href="{PUBLIC_SITE}">
<meta property="og:url" content="{PUBLIC_SITE}">
<link rel="stylesheet" href="styles.css"></head>
<body class="dashboard-preview editorial-site">
<section id="data-notice"></section><form id="price-calculator"></form>
<script src="app.js"></script><script src="dashboard_metrics.js"></script>
<script src="price_playground.js"></script></body></html>"""


def fixture_fetch(publish_state=None, with_prices=False, *, html=HTML, missing=None):
    import json

    payload = {
        "schema_version": 1,
        "national_prices": [{"price_idr": "25000"}] if with_prices else [],
        "province_prices": [],
        "publish_state": publish_state,
    }

    def fetch(url):
        name = urlparse(url).path.lstrip("/") or "index.html"
        if name == missing:
            raise OSError("404")
        if name == "index.html":
            return html.encode("utf-8")
        if name == "data/dashboard.json":
            return json.dumps(payload).encode("utf-8")
        return b"/* static asset */"

    return fetch


def test_valid_portfolio_preview_verifies_all_assets():
    result = verify_public_site(PUBLIC_SITE, fixture_fetch())
    assert result["mode"] == "portfolio-preview"
    assert set(result["assets"]) == {
        "styles.css", "app.js", "dashboard_metrics.js",
        "price_playground.js", "data/dashboard.json"
    }


def test_published_data_requires_a_successful_publication_state():
    with pytest.raises(ValueError, match="without a publish state"):
        verify_public_site(PUBLIC_SITE, fixture_fetch(with_prices=True))


def test_successful_reviewed_snapshot_is_allowed():
    state = {
        "active_run_status": "SUCCESS",
        "active_observation_date": "2026-10-09",
        "freshness_label": "Perlu diperiksa",
    }
    result = verify_public_site(
        PUBLIC_SITE, fixture_fetch(publish_state=state, with_prices=True)
    )
    assert result["mode"] == "validated-snapshot"


@pytest.mark.parametrize("missing", [
    "styles.css", "app.js", "dashboard_metrics.js",
    "price_playground.js", "data/dashboard.json"
])
def test_missing_live_assets_fail_before_publication_claim(missing):
    with pytest.raises(OSError):
        verify_public_site(PUBLIC_SITE, fixture_fetch(missing=missing))


def test_old_or_redirected_site_metadata_cannot_pass():
    outdated = HTML.replace('<meta property="og:url" content="' + PUBLIC_SITE + '">', "")
    with pytest.raises(ValueError, match="social sharing URL"):
        verify_public_site(PUBLIC_SITE, fixture_fetch(html=outdated))


def test_invalid_urls_are_rejected_without_network():
    for url in ("http://panganlens-portfolio.vercel.app/",
                "https://panganlens-679cd2.gitlab.io/",
                "https://example.org/", "https://example.org/path",
                "https://example.org/?token=a",
                "https://panganlens-portfolio.vercel.app.evil.example/",
                "https://panganlens-portfolio.vercel.app:444/",
                "https://panganlens-portfolio.vercel.app/#top",
                "file:///tmp/index.html"):
        with pytest.raises(ValueError):
            verify_public_site(url, fixture_fetch())


def test_broken_published_date_is_rejected():
    state = {
        "active_run_status": "SUCCESS",
        "active_observation_date": "2026-02-30",
        "freshness_label": "Terkini",
    }
    with pytest.raises(ValueError, match="observation date"):
        verify_public_site(PUBLIC_SITE, fixture_fetch(publish_state=state))


def test_unreviewed_layout_cannot_pass_as_editorial_release():
    html = HTML.replace('class="dashboard-preview editorial-site"', '')
    with pytest.raises(ValueError, match="editorial release"):
        verify_public_site(PUBLIC_SITE, fixture_fetch(html=html))


def test_vercel_production_root_is_exactly_allowlisted():
    assert PUBLIC_SITE == "https://panganlens-portfolio.vercel.app/"
    for candidate in (
        "https://panganlens-portfolio-fadhil-9768s-projects.vercel.app/",
        "https://panganlens-portfolio.vercel.app@evil.example/",
    ):
        with pytest.raises(ValueError, match="approved HTTPS production host"):
            verify_public_site(candidate, fixture_fetch())
