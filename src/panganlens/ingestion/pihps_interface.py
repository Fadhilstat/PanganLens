"""Guarded client for the PIHPS public website data interface.

Bank Indonesia does not document these website endpoints as a stable public API.
The client therefore validates transport, payload size, content type, and schema
before any response can move into normalization.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse

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
DEFAULT_ALLOWED_HOSTS = frozenset({"www.bi.go.id"})
DEFAULT_MAX_PAYLOAD_BYTES = 2_000_000
JSON_CONTENT_TYPES = ("application/json", "text/json")
DATE_COLUMN_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")


class PihpsInterfaceError(RuntimeError):
    """Raised when the PIHPS website interface returns an unsafe response."""


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
    normalized_keys: tuple[str, ...]
    schema_fingerprint: str


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Integrity and transport metadata retained beside a source response."""

    source_url: str
    source_host: str
    content_type: str
    payload_bytes: int
    payload_sha256: str
    request_fingerprint: str
    schema_fingerprint: str
    requested_at: datetime
    completed_at: datetime
    http_status: int


@dataclass(frozen=True, slots=True)
class SourceRows:
    """Validated source rows paired with transport and integrity evidence."""

    rows: tuple[dict[str, Any], ...]
    payload_text: str
    evidence: SourceEvidence


class PihpsWebsiteClient:
    """Read validated JSON rows from the public PIHPS website interface."""

    def __init__(
        self,
        base_url: str = "https://www.bi.go.id/hargapangan",
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
        allowed_hosts: frozenset[str] = DEFAULT_ALLOWED_HOSTS,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or _build_session()
        self.allowed_hosts = allowed_hosts
        self.max_payload_bytes = max_payload_bytes
        _validate_source_url(self.base_url, self.allowed_hosts)
        if self.max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be positive")

    def fetch_reference(
        self,
        name: str,
        params: Mapping[str, str | int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch a reference list and return validated rows."""

        return list(self.fetch_reference_capture(name, params).rows)

    def fetch_reference_capture(
        self,
        name: str,
        params: Mapping[str, str | int] | None = None,
    ) -> SourceRows:
        """Fetch a reference list with source integrity evidence."""

        try:
            path = REFERENCE_ENDPOINTS[name]
        except KeyError as exc:
            raise KeyError(f"unknown reference endpoint: {name}") from exc
        return self._get_capture(path, params, "/TabelHarga/PasarTradisionalKomoditas")

    def fetch_grid(self, request: GridRequest) -> list[dict[str, Any]]:
        """Fetch one commodity grid without interpreting row values."""

        return list(self.fetch_grid_capture(request).rows)

    def fetch_grid_capture(self, request: GridRequest) -> SourceRows:
        """Fetch one commodity grid with source integrity evidence."""

        return self._get_capture(
            GRID_ENDPOINT,
            request.as_params(),
            "/TabelHarga/PasarTradisionalKomoditas",
        )

    def _get_capture(
        self,
        path: str,
        params: Mapping[str, str | int] | None,
        referer: str,
    ) -> SourceRows:
        url = f"{self.base_url}{path}"
        _validate_source_url(url, self.allowed_hosts)
        request_params = dict(params) if params else {}
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{self.base_url}{referer}",
            "User-Agent": "PanganLens/0.1 (+https://github.com/Fadhilstat/PanganLens)",
            "X-Requested-With": "XMLHttpRequest",
        }
        requested_at = datetime.now(UTC)
        try:
            response = self.session.get(
                url,
                params=request_params or None,
                headers=headers,
                timeout=self.timeout_seconds,
                allow_redirects=False,
                stream=True,
            )
            if 300 <= response.status_code < 400:
                raise PihpsInterfaceError("PIHPS response attempted an unexpected redirect")
            response.raise_for_status()
        except PihpsInterfaceError:
            raise
        except requests.RequestException as exc:
            raise PihpsInterfaceError(f"PIHPS request failed for {path}: {exc}") from exc

        content_type = response.headers.get("content-type", "").lower()
        if not any(content_type.startswith(item) for item in JSON_CONTENT_TYPES):
            shown_type = content_type or "missing"
            raise PihpsInterfaceError(
                f"PIHPS returned unexpected content-type for {path}: {shown_type}"
            )

        declared_length = _parse_content_length(response.headers.get("content-length"))
        if declared_length is not None and declared_length > self.max_payload_bytes:
            raise PihpsInterfaceError("PIHPS payload exceeds the configured size limit")

        payload_bytes = _read_limited_body(response, self.max_payload_bytes)
        try:
            payload_text = payload_bytes.decode("utf-8")
            payload = json.loads(payload_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PihpsInterfaceError("PIHPS returned invalid UTF-8 JSON") from exc

        rows = extract_rows(payload)
        shape = response_shape(rows)
        completed_at = datetime.now(UTC)
        evidence = SourceEvidence(
            source_url=url,
            source_host=urlparse(url).hostname or "",
            content_type=content_type,
            payload_bytes=len(payload_bytes),
            payload_sha256=hashlib.sha256(payload_bytes).hexdigest(),
            request_fingerprint=_request_fingerprint(path, request_params),
            schema_fingerprint=shape.schema_fingerprint,
            requested_at=requested_at,
            completed_at=completed_at,
            http_status=response.status_code,
        )
        return SourceRows(tuple(rows), payload_text, evidence)


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract row dictionaries from known PIHPS response container shapes."""

    rows: Any
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next((payload.get(key) for key in ROW_CONTAINER_KEYS if key in payload), None)
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
    """Return schema evidence without exposing source row values."""

    keys = sorted({str(key) for row in rows for key in row})
    normalized_keys = sorted({_normalize_schema_key(key) for key in keys})
    fingerprint = hashlib.sha256(
        json.dumps(normalized_keys, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ResponseShape(
        row_count=len(rows),
        row_keys=tuple(keys),
        normalized_keys=tuple(normalized_keys),
        schema_fingerprint=fingerprint,
    )


def validate_schema_contract(
    rows: Sequence[Mapping[str, Any]], expected_keys: frozenset[str]
) -> ResponseShape:
    """Reject schema drift while allowing dynamic PIHPS date columns."""

    shape = response_shape(rows)
    actual = frozenset(shape.normalized_keys)
    if actual != expected_keys:
        raise PihpsInterfaceError(
            "PIHPS response schema changed: "
            f"expected {sorted(expected_keys)}, received {sorted(actual)}"
        )
    return shape


def pick_reference_id(
    rows: Sequence[Mapping[str, Any]],
    candidate_keys: Sequence[str],
    preferred: str | None = None,
    required_prefix: str | None = None,
) -> str:
    """Pick a usable reference ID without depending on row order."""

    candidates: list[str] = []
    for row in rows:
        for key in candidate_keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            if required_prefix and not text.startswith(required_prefix):
                continue
            candidates.append(text)
            break
    if preferred and preferred in candidates:
        return preferred
    if not candidates:
        raise PihpsInterfaceError("PIHPS reference response has no usable identifier")
    return sorted(set(candidates))[0]


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def _validate_source_url(url: str, allowed_hosts: frozenset[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("PIHPS source must use HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("credentials are not allowed in PIHPS source URLs")
    if parsed.hostname not in allowed_hosts:
        raise ValueError("PIHPS source host is not allowlisted")


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise PihpsInterfaceError("PIHPS returned an invalid content-length header") from exc
    if parsed < 0:
        raise PihpsInterfaceError("PIHPS returned a negative content-length header")
    return parsed


def _read_limited_body(response: requests.Response, max_payload_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_payload_bytes:
            raise PihpsInterfaceError("PIHPS payload exceeds the configured size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _request_fingerprint(path: str, params: Mapping[str, str | int]) -> str:
    canonical = json.dumps(
        {"path": path, "params": dict(sorted(params.items()))},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_schema_key(key: str) -> str:
    return "<date>" if DATE_COLUMN_PATTERN.fullmatch(key) else key


def _format_source_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")
