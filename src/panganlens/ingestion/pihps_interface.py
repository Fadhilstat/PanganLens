"""Client for the PIHPS public website data interface.

The endpoints used here are part of the public PIHPS website implementation, but
Bank Indonesia does not document them as a stable public API. The client keeps
that distinction explicit and validates every response before downstream use.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


REFERENCE_ENDPOINTS = {
    "provinces": "/WebSite/TabelHarga/GetRefProvince",
    "commodities": "/WebSite/TabelHarga/GetRefCommodityAndCategory",
    "regencies": "/WebSite/TabelHarga/GetRefRegency",
}

GRID_ENDPOINT = "/WebSite/TabelHarga/GetGridDataKomoditas"
ROW_CONTAINER_KEYS = ("data", "rows", "result", "items")
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


class PihpsInterfaceError(RuntimeError):
    """Raised when the PIHPS website interface returns an unusable response."""


@dataclass(frozen=True, slots=True)
class GridRequest:
    """Parameters for one PIHPS commodity grid request."""

    price_type_id: int
    comcat_id: str
    province_id: str
    start_date: date
    end_date: date
    regency_ids: tuple[str, ...] = ()
    show_regencies: bool = True
    show_markets: bool = False
    report_type: int = 1

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        if self.price_type_id <= 0:
            raise ValueError("price_type_id must be positive")
        if self.report_type not in (1, 2, 3):
            raise ValueError("report_type must be 1, 2, or 3")
        if not self.comcat_id.strip():
            raise ValueError("comcat_id must not be empty")
        if not self.province_id.strip():
            raise ValueError("province_id must not be empty")

    def as_params(self) -> dict[str, str | int]:
        """Return request parameters expected by the PIHPS grid interface."""

        return {
            "price_type_id": self.price_type_id,
            "comcat_id": self.comcat_id,
            "province_id": self.province_id,
            "regency_id": ",".join(self.regency_ids),
            "showKota": str(self.show_regencies).lower(),
            "showPasar": str(self.show_markets).lower(),
            "tipe_laporan": self.report_type,
            "start_date": _format_source_date(self.start_date),
            "end_date": _format_source_date(self.end_date),
        }


@dataclass(frozen=True, slots=True)
class ResponseShape:
    """Schema-only evidence captured from a PIHPS response."""

    row_count: int
    row_keys: tuple[str, ...]


class PihpsWebsiteClient:
    """Read validated JSON rows from the public PIHPS website interface."""

    def __init__(
        self,
        base_url: str = "https://www.bi.go.id/hargapangan",
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or _build_session()

    def fetch_reference(
        self,
        name: str,
        params: Mapping[str, str | int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch a PIHPS reference list and require a row-oriented JSON response."""

        try:
            path = REFERENCE_ENDPOINTS[name]
        except KeyError as exc:
            raise KeyError(f"unknown reference endpoint: {name}") from exc

        return self._get_rows(
            path=path,
            params=params,
            referer="/TabelHarga/PasarTradisionalKomoditas",
        )

    def fetch_grid(self, request: GridRequest) -> list[dict[str, Any]]:
        """Fetch one commodity grid without interpreting its row values yet."""

        return self._get_rows(
            path=GRID_ENDPOINT,
            params=request.as_params(),
            referer="/TabelHarga/PasarTradisionalKomoditas",
        )

    def _get_rows(
        self,
        path: str,
        params: Mapping[str, str | int] | None,
        referer: str,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{self.base_url}{referer}",
            "User-Agent": "PanganLens/0.1 (+https://github.com/Fadhilstat/PanganLens)",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            response = self.session.get(
                url,
                params=dict(params) if params else None,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise PihpsInterfaceError(f"PIHPS request failed for {path}: {exc}") from exc

        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            content_type = response.headers.get("content-type", "unknown")
            raise PihpsInterfaceError(
                f"PIHPS returned non-JSON content for {path}; content-type={content_type}"
            ) from exc

        return extract_rows(payload)


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract row dictionaries from known PIHPS response container shapes."""

    rows: Any
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ROW_CONTAINER_KEYS:
            value = payload.get(key)
            if value is not None:
                rows = value
                break
        if rows is None:
            raise PihpsInterfaceError(
                "PIHPS JSON response did not contain a recognized row container"
            )
    else:
        raise PihpsInterfaceError("PIHPS JSON response is not a row-oriented structure")

    if not isinstance(rows, list):
        raise PihpsInterfaceError("PIHPS row container is not a list")
    if any(not isinstance(row, dict) for row in rows):
        raise PihpsInterfaceError("PIHPS row container includes a non-object item")

    return [dict(row) for row in rows]


def response_shape(rows: Sequence[Mapping[str, Any]]) -> ResponseShape:
    """Return row count and the union of row keys without exposing row values."""

    keys = sorted({str(key) for row in rows for key in row})
    return ResponseShape(row_count=len(rows), row_keys=tuple(keys))


def pick_reference_id(
    rows: Sequence[Mapping[str, Any]],
    id_keys: Sequence[str],
    preferred: str | None = None,
    required_prefix: str | None = None,
) -> str:
    """Choose a usable reference ID from a PIHPS reference response."""

    candidates: list[str] = []
    for row in rows:
        for key in id_keys:
            value = row.get(key)
            if value is None:
                continue
            candidate = str(value).strip()
            if not candidate:
                continue
            if required_prefix and not candidate.startswith(required_prefix):
                continue
            candidates.append(candidate)
            break

    if preferred and preferred in candidates:
        return preferred
    if candidates:
        return candidates[0]
    raise PihpsInterfaceError("PIHPS reference response did not contain a usable ID")


def _format_source_date(value: date) -> str:
    return f"{value.isoformat()}T00:00:00.000"


def _build_session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=1.0,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    return session
