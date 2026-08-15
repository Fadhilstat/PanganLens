"""Probe undocumented PIHPS website endpoints before using them in production."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


REFERENCE_ENDPOINTS = {
    "provinces": "/WebSite/TabelHarga/GetRefProvince",
    "commodities": "/WebSite/TabelHarga/GetRefCommodityAndCategory",
}

GRID_ENDPOINT = "/WebSite/TabelHarga/GetGridDataKomoditas"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Small diagnostic result for a candidate endpoint."""

    name: str
    url: str
    status_code: int | None
    content_type: str | None
    is_json: bool
    item_count: int | None
    error: str | None = None


class PihpsCandidateProbe:
    """Check candidate JSON endpoints without treating them as a public API contract."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def probe_reference(self, name: str) -> ProbeResult:
        if name not in REFERENCE_ENDPOINTS:
            raise KeyError(f"unknown reference endpoint: {name}")

        path = REFERENCE_ENDPOINTS[name]
        url = f"{self.base_url}{path}"
        headers = self._headers()

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            content_type = response.headers.get("content-type")
            data = self._try_json(response)
            return ProbeResult(
                name=name,
                url=url,
                status_code=response.status_code,
                content_type=content_type,
                is_json=data is not None,
                item_count=_infer_item_count(data),
                error=None,
            )
        except requests.RequestException as exc:
            return ProbeResult(
                name=name,
                url=url,
                status_code=None,
                content_type=None,
                is_json=False,
                item_count=None,
                error=str(exc),
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{self.base_url}/TabelHarga/PasarTradisionalKomoditas",
            "User-Agent": "PanganLens/0.1 (+public-data-analytics)",
            "X-Requested-With": "XMLHttpRequest",
        }

    @staticmethod
    def _try_json(response: Any) -> Any | None:
        try:
            return response.json()
        except (ValueError, TypeError):
            return None


def _infer_item_count(data: Any) -> int | None:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("data", "items", "rows"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
    return None
