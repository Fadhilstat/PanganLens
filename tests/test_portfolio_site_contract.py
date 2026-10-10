import json
from html.parser import HTMLParser
from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[1] / "website"
GITLAB_CI = WEBSITE.parent / ".gitlab-ci.yml"


class SiteControls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "input":
            self.inputs.append(values)


def test_portfolio_has_calculator_and_case_study():
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")
    parsed = SiteControls()
    parsed.feed(html)
    expected_ids = {"price-calculator", "calc-movement", "calc-region", "simulasi", "studi-kasus"}
    assert expected_ids.issubset(parsed.ids)
    assert {item.get("name") for item in parsed.inputs} == {
        "previous", "current", "average", "region"
    }
    for item in parsed.inputs:
        assert item.get("type") == "number"
        assert "value" not in item
        assert "required" in item
    assert "bukan data PIHPS" in html
    assert 'href="#main-content"' in html


def test_production_snapshot_is_not_populated_with_synthetic_prices():
    snapshot = json.loads((WEBSITE / "data" / "dashboard.json").read_text(encoding="utf-8"))
    assert snapshot["national_prices"] == []
    assert snapshot["province_prices"] == []
    assert snapshot["publish_state"] is None


def test_site_is_accessible_on_mobile_and_respects_motion_settings():
    css = (WEBSITE / "styles.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in css
    assert ".skip-link:focus" in css
    assert 'nav { display: none; }' not in css
    assert "min-height: 44px" in css


def test_gitlab_pages_publish_is_guarded_by_default_branch_and_quality():
    text = GITLAB_CI.read_text(encoding="utf-8")
    assert "deploy_portfolio_site:" in text
    job = text.split("deploy_portfolio_site:", 1)[1]
    assert "publish: website" in job
    assert "stage: deploy" in job
    assert "CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in job
    assert "python_quality" in job
    assert "frontend_quality" in job

def test_metrics_guard_does_not_count_missing_region_gaps_as_zero():
    app = (WEBSITE / "app.js").read_text(encoding="utf-8")
    assert "PanganLensMetrics.selectRegions(rows)" in app
    assert "price_gap_vs_province_average_pct || 0" not in app
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")
    assert 'src="dashboard_metrics.js"' in html


def test_static_site_publishing_has_fail_closed_snapshot_validation():
    project = WEBSITE.parent
    workflow = (project / ".github" / "workflows" / "dashboard_pages.yml").read_text(
        encoding="utf-8"
    )
    gitlab_ci = (project / ".gitlab-ci.yml").read_text(encoding="utf-8")
    command = "python scripts/check_public_snapshot.py website/data/dashboard.json"
    assert command in workflow
    assert workflow.index("Validate public snapshot") < workflow.index("Configure Pages")
    assert command in gitlab_ci
    assert gitlab_ci.index(command) > gitlab_ci.index("deploy_portfolio_site:")


def test_public_portfolio_has_real_preview_links_and_social_metadata():
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")
    public_url = "https://panganlens-portfolio.vercel.app/"
    assert f'<link rel="canonical" href="{public_url}">' in html
    assert f'<meta property="og:url" content="{public_url}">' in html
    assert '<meta property="og:type" content="website">' in html
    assert '<meta name="twitter:card" content="summary">' in html
    assert 'href="#simulasi">Coba kalkulator harga <span aria-hidden="true">↗</span></a>' in html
    assert 'href="#studi-kasus">Baca studi kasus <span aria-hidden="true">↗</span></a>' in html
    assert "Harga PIHPS belum dipublikasikan" in html
    assert "https://github.com/Fadhilstat/PanganLens" in html
    assert "https://gitlab.com/fadhilrusydih/panganlens" in html


def test_launch_links_have_visible_keyboard_and_mobile_targets():
    css = (WEBSITE / "styles.css").read_text(encoding="utf-8")
    assert ".hero-links a { min-height: 44px;" in css
    assert ".hero-link-primary:hover" in css
    assert ".footer-links a {" in css
    assert "width: 100%;" in css
    assert ":focus-visible" in css


def test_vercel_static_config_does_not_cache_price_snapshots():
    config = json.loads((WEBSITE / "vercel.json").read_text(encoding="utf-8"))
    assert config["cleanUrls"] is False
    header_rules = config["headers"]
    snapshot_rules = [rule for rule in header_rules if rule["source"] == "/data/dashboard.json"]
    assert len(snapshot_rules) == 1
    assert {"key": "Cache-Control", "value": "no-store"} in snapshot_rules[0]["headers"]
