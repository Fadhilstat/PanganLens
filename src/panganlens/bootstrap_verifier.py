"""Verify the PanganLens BigQuery bootstrap using metadata only."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import bigquery

from panganlens.schema_contract import (
    REQUIRED_DATASETS,
    WAREHOUSE_LOCATION,
    WAREHOUSE_OBJECTS,
)
from panganlens.warehouse.loader import PROJECT_ID_PATTERN


@dataclass(frozen=True, slots=True)
class BootstrapVerificationCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class BootstrapVerificationReport:
    status: str
    checks: tuple[BootstrapVerificationCheck, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "checks": [asdict(check) for check in self.checks],
        }


class BigQueryBootstrapVerifier:
    """Check bootstrap metadata without reading table rows or changing BigQuery."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = WAREHOUSE_LOCATION,
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        if not location.strip():
            raise ValueError("location must not be empty")

        if client is not None:
            client_project = getattr(client, "project", project_id)
            if client_project != project_id:
                raise ValueError("BigQuery client project does not match project_id")

        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)

    def verify(self) -> BootstrapVerificationReport:
        """Return schema bootstrap status from dataset and table metadata only."""

        checks = [*self._check_datasets(), *self._check_objects()]
        status = (
            "SCHEMA_READY"
            if checks and all(check.status == "PASS" for check in checks)
            else "BLOCKED"
        )
        return BootstrapVerificationReport(status=status, checks=tuple(checks))

    def _check_datasets(self) -> list[BootstrapVerificationCheck]:
        checks: list[BootstrapVerificationCheck] = []
        for dataset_name in REQUIRED_DATASETS:
            resource = f"{self.project_id}.{dataset_name}"
            try:
                dataset = self.client.get_dataset(resource)
            except NotFound:
                checks.append(
                    BootstrapVerificationCheck(
                        name=f"dataset:{dataset_name}",
                        status="FAIL",
                        detail="Dataset belum tersedia",
                    )
                )
            except GoogleAPICallError as exc:
                checks.append(
                    BootstrapVerificationCheck(
                        name=f"dataset:{dataset_name}",
                        status="FAIL",
                        detail=f"Metadata dataset gagal dibaca: {type(exc).__name__}",
                    )
                )
            else:
                actual_location = str(getattr(dataset, "location", "") or "")
                location_matches = actual_location.casefold() == self.location.casefold()
                checks.append(
                    BootstrapVerificationCheck(
                        name=f"dataset:{dataset_name}",
                        status="PASS" if location_matches else "FAIL",
                        detail=(
                            f"Dataset tersedia di {actual_location}"
                            if location_matches
                            else (
                                f"Lokasi dataset {actual_location or 'tidak diketahui'}; "
                                f"diharapkan {self.location}"
                            )
                        ),
                    )
                )
        return checks

    def _check_objects(self) -> list[BootstrapVerificationCheck]:
        checks: list[BootstrapVerificationCheck] = []
        for warehouse_object in WAREHOUSE_OBJECTS:
            resource = (
                f"{self.project_id}.{warehouse_object.dataset}.{warehouse_object.name}"
            )
            try:
                table = self.client.get_table(resource)
            except NotFound:
                checks.append(
                    BootstrapVerificationCheck(
                        name=f"object:{warehouse_object.qualified_name}",
                        status="FAIL",
                        detail=f"{warehouse_object.object_type} belum tersedia",
                    )
                )
            except GoogleAPICallError as exc:
                checks.append(
                    BootstrapVerificationCheck(
                        name=f"object:{warehouse_object.qualified_name}",
                        status="FAIL",
                        detail=f"Metadata object gagal dibaca: {type(exc).__name__}",
                    )
                )
            else:
                actual_type = str(getattr(table, "table_type", "") or "").upper()
                type_matches = actual_type == warehouse_object.object_type
                checks.append(
                    BootstrapVerificationCheck(
                        name=f"object:{warehouse_object.qualified_name}",
                        status="PASS" if type_matches else "FAIL",
                        detail=(
                            f"{warehouse_object.object_type} tersedia"
                            if type_matches
                            else (
                                f"Tipe object {actual_type or 'tidak diketahui'}; "
                                f"diharapkan {warehouse_object.object_type}"
                            )
                        ),
                    )
                )
        return checks
