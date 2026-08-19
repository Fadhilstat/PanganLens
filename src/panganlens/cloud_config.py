"""Validation helpers for PanganLens Google Cloud repository variables."""

from __future__ import annotations

import re

from panganlens.warehouse.loader import PROJECT_ID_PATTERN

WIF_PROVIDER_PATTERN = re.compile(
    r"^projects/[1-9][0-9]*/locations/global/"
    r"workloadIdentityPools/panganlens-github/providers/panganlens-repo$"
)


def validate_cloud_variables(project_id: str, wif_provider: str) -> None:
    """Reject malformed or unexpected Google Cloud activation variables."""

    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("GCP_PROJECT_ID is not a valid Google Cloud project ID")
    if not WIF_PROVIDER_PATTERN.fullmatch(wif_provider):
        raise ValueError(
            "GCP_WIF_PROVIDER must use the reviewed panganlens-github pool "
            "and panganlens-repo provider with a numeric project number"
        )
