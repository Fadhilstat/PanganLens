"""Runtime configuration for PanganLens."""

from __future__ import annotations

import os
from dataclasses import dataclass

from panganlens.schema_contract import WAREHOUSE_LOCATION


@dataclass(frozen=True, slots=True)
class Settings:
    """Settings loaded from environment variables."""

    bigquery_project: str
    bigquery_location: str = WAREHOUSE_LOCATION
    request_timeout_seconds: int = 30
    source_base_url: str = "https://www.bi.go.id/hargapangan"

    @classmethod
    def from_env(cls) -> Settings:
        project = os.getenv("PANGANLENS_BQ_PROJECT", "").strip()
        if not project:
            raise ValueError("PANGANLENS_BQ_PROJECT must be set")

        timeout_raw = os.getenv("PANGANLENS_REQUEST_TIMEOUT_SECONDS", "30")
        timeout = int(timeout_raw)
        if timeout <= 0:
            raise ValueError("PANGANLENS_REQUEST_TIMEOUT_SECONDS must be positive")

        return cls(
            bigquery_project=project,
            bigquery_location=os.getenv(
                "PANGANLENS_BQ_LOCATION", WAREHOUSE_LOCATION
            ).strip(),
            request_timeout_seconds=timeout,
            source_base_url=os.getenv(
                "PANGANLENS_SOURCE_BASE_URL",
                "https://www.bi.go.id/hargapangan",
            ).rstrip("/"),
        )
