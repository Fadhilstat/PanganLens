"""Anonymous, dependency-free smoke test for the published PanganLens website.

Uses no GitLab token, browser session, cloud credentials, or VPS.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

PUBLIC_SITE = "https://panganlens-679cd2.gitlab.io/"
ASSETS = (
    "styles.css",
    "app.js",
    "dashboard_metrics.js",
    "price_playground.js",
    "data/dashboard.json",
)


def _fetch_public(url: str) -> bytes:
    expected_host = urlparse(url).hostname
    request = Request(url, headers={"User-Agent": "PanganLens-Public-Site-Smoke/1.0"})
    with urlopen(request, timeout=12) as response:
        final_url = response.geturl()
        if response.status != 200:
            raise ValueError(f"website HTTP status: {response.status}")
        if urlparse(final_url).hostname != expected_host:
            raise ValueError("website redirected outside the public Pages host")
        payload = response.read(500_001)
        if len(payload) > 500_000:
            raise ValueError("website asset exceeds the smoke-test size limit")
        return payload


def verify_public_site(base_url: str, fetcher=None) -> dict[str, object]:
    """Return observed facts only after HTML, all assets and JSON pass."""
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ValueError("public Pages URL must use an HTTPS host")
    if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("public Pages URL must point to the website root")
    base = base_url.rstrip("/") + "/"
    read = fetcher or _fetch_public
    html = read(base).decode("utf-8")
    if "<html" not in html or "PanganLens Indonesia" not in html:
        raise ValueError("public URL is not the PanganLens website")
    if 'id="price-calculator"' not in html or 'id="data-notice"' not in html:
        raise ValueError("public website is missing its calculator or data status")
    if f'<link rel="canonical" href="{base}">' not in html:
        raise ValueError("public website is not yet serving the launch metadata")
    if f'<meta property="og:url" content="{base}">' not in html:
        raise ValueError("public website is missing the social sharing URL")

    resources = {}
    for asset in ASSETS:
        payload = read(urljoin(base, asset))
        if not payload:
            raise ValueError(f"public website asset is empty: {asset}")
        resources[asset] = len(payload)

    for script in ("app.js", "dashboard_metrics.js", "price_playground.js"):
        if f'src="{script}"' not in html:
            raise ValueError(f"public website does not load {script}")
    if 'href="styles.css"' not in html:
        raise ValueError("public website does not load its stylesheet")

    data = json.loads(read(urljoin(base, "data/dashboard.json")).decode("utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ValueError("public dashboard JSON has no reviewed schema version")
    if data["schema_version"] != 1:
        raise ValueError("public dashboard JSON version is unsupported")
    national = data.get("national_prices")
    regions = data.get("province_prices")
    if not isinstance(national, list) or not isinstance(regions, list):
        raise ValueError("public dashboard prices must be arrays")
    state = data.get("publish_state")
    if state is None:
        if national or regions:
            raise ValueError("public website shows prices without a publish state")
        mode = "portfolio-preview"
    else:
        if not isinstance(state, dict) or state.get("active_run_status") != "SUCCESS":
            raise ValueError("public website has no successful publication state")
        day = state.get("active_observation_date")
        if not isinstance(day, str):
            raise ValueError("public website observation date is absent")
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("public website observation date format is invalid")
        except ValueError as exc:
            raise ValueError("public website observation date is invalid") from exc
        if state.get("freshness_label") not in {"Terkini", "Perlu diperiksa", "Data lama"}:
            raise ValueError("public website freshness label is unreviewed")
        mode = "validated-snapshot"

    return {"url": base, "mode": mode, "assets": resources, "html_bytes": len(html)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check anonymous PanganLens Pages access")
    parser.add_argument("--url", default=PUBLIC_SITE)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)
    if not 1 <= args.attempts <= 5:
        parser.error("--attempts must be 1 to 5")

    for attempt in range(1, args.attempts + 1):
        try:
            result = verify_public_site(args.url)
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            print(f"Public Pages attempt {attempt}/{args.attempts}: FAIL ({exc})",
                  file=sys.stderr)
            if attempt == args.attempts:
                return 1
            time.sleep(5)
        else:
            print("PUBLIC_PAGES_SMOKE_PASS " + json.dumps(result, sort_keys=True))
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
