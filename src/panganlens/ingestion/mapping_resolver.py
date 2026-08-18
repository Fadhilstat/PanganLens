"""Resolve PIHPS entities only through active reviewed BigQuery mappings."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from google.cloud import bigquery

from panganlens.ingestion.orchestration import CanonicalMapping, IngestionContext
from panganlens.ingestion.pihps_parser import GridPricePoint
from panganlens.warehouse.loader import PROJECT_ID_PATTERN

SOURCE_SYSTEM = "PIHPS"


class MappingRegistryError(RuntimeError):
    """Raised when the reviewed mapping registry is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class MappingKey:
    """Exact source identity used to retrieve one reviewed mapping."""

    entity_type: str
    source_id: str | None = None
    source_name_normalized: str | None = None
    source_level: str | None = None
    parent_source_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewedMapping:
    """One active reviewed source-to-canonical mapping."""

    canonical_id: str
    mapping_version: int


class BigQueryReviewedMappingResolver:
    """Resolve PIHPS points with exact active mappings and no fuzzy matching."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = "asia-southeast2",
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)
        self._cache: dict[MappingKey, ReviewedMapping | None] = {}

    def resolve(
        self,
        point: GridPricePoint,
        context: IngestionContext,
    ) -> CanonicalMapping | None:
        context.validate()
        required = self._required_keys(point, context)
        resolved: dict[str, ReviewedMapping] = {}

        for key in required:
            mapping = self._lookup(key)
            if mapping is None:
                return None
            resolved[key.entity_type] = mapping

        versions = {mapping.mapping_version for mapping in resolved.values()}
        if len(versions) != 1:
            raise MappingRegistryError("active mappings do not share one mapping version")

        version = next(iter(versions))
        fingerprint = _mapping_fingerprint(required, resolved, version)
        return CanonicalMapping(
            commodity_id=resolved["commodity"].canonical_id,
            channel_id=resolved["channel"].canonical_id,
            region_id=(
                resolved["region"].canonical_id if "region" in resolved else None
            ),
            market_id=(
                resolved["market"].canonical_id if "market" in resolved else None
            ),
            mapping_version=version,
            mapping_key_fingerprint=fingerprint,
        )

    def _required_keys(
        self,
        point: GridPricePoint,
        context: IngestionContext,
    ) -> tuple[MappingKey, ...]:
        params = context.request_parameters
        comcat_id = _required_param(params, "comcat_id")
        price_type_id = _required_param(params, "price_type_id")
        keys = [
            MappingKey(entity_type="commodity", source_id=comcat_id),
            MappingKey(entity_type="channel", source_id=price_type_id),
        ]

        if context.scope == "region":
            keys.append(
                MappingKey(
                    entity_type="region",
                    source_name_normalized=normalize_source_name(point.source_row_name),
                    source_level=normalize_source_level(point.source_row_level),
                )
            )
        elif context.scope == "market":
            parent_source_id = str(params.get("province_id") or "").strip() or None
            keys.append(
                MappingKey(
                    entity_type="market",
                    source_name_normalized=normalize_source_name(point.source_row_name),
                    source_level=normalize_source_level(point.source_row_level),
                    parent_source_id=parent_source_id,
                )
            )
        return tuple(keys)

    def _lookup(self, key: MappingKey) -> ReviewedMapping | None:
        if key in self._cache:
            return self._cache[key]

        query = """
SELECT canonical_id, mapping_version
FROM panganlens_ops.vw_active_source_entity_mapping
WHERE source_system = @source_system
  AND entity_type = @entity_type
  AND (@source_id IS NULL OR source_id = @source_id)
  AND (
    @source_name_normalized IS NULL
    OR source_name_normalized = @source_name_normalized
  )
  AND (@source_level IS NULL OR LOWER(source_level) = @source_level)
  AND (@parent_source_id IS NULL OR parent_source_id = @parent_source_id)
ORDER BY canonical_id, mapping_version
LIMIT 2
""".strip()
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("source_system", "STRING", SOURCE_SYSTEM),
                bigquery.ScalarQueryParameter("entity_type", "STRING", key.entity_type),
                bigquery.ScalarQueryParameter("source_id", "STRING", key.source_id),
                bigquery.ScalarQueryParameter(
                    "source_name_normalized",
                    "STRING",
                    key.source_name_normalized,
                ),
                bigquery.ScalarQueryParameter(
                    "source_level",
                    "STRING",
                    key.source_level,
                ),
                bigquery.ScalarQueryParameter(
                    "parent_source_id",
                    "STRING",
                    key.parent_source_id,
                ),
            ]
        )
        rows = list(
            self.client.query(
                query,
                job_config=config,
                location=self.location,
            ).result()
        )
        if len(rows) > 1:
            raise MappingRegistryError(
                f"more than one active mapping matched entity type {key.entity_type}"
            )
        if not rows:
            self._cache[key] = None
            return None

        row = rows[0]
        mapping = ReviewedMapping(
            canonical_id=str(row["canonical_id"]),
            mapping_version=int(row["mapping_version"]),
        )
        if not mapping.canonical_id.strip() or mapping.mapping_version <= 0:
            raise MappingRegistryError("active mapping contains invalid canonical metadata")
        self._cache[key] = mapping
        return mapping


def normalize_source_name(value: str) -> str:
    """Normalize source text deterministically without approximate matching."""

    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def normalize_source_level(value: str) -> str:
    """Normalize a source hierarchy label for an exact registry lookup."""

    return normalize_source_name(value)


def _required_param(params: dict[str, Any], name: str) -> str:
    value = str(params.get(name) or "").strip()
    if not value:
        raise ValueError(f"request_parameters must include {name}")
    return value


def _mapping_fingerprint(
    keys: tuple[MappingKey, ...],
    resolved: dict[str, ReviewedMapping],
    version: int,
) -> str:
    payload = {
        "mapping_version": version,
        "keys": [
            {
                "entity_type": key.entity_type,
                "source_id": key.source_id,
                "source_name_normalized": key.source_name_normalized,
                "source_level": key.source_level,
                "parent_source_id": key.parent_source_id,
                "canonical_id": resolved[key.entity_type].canonical_id,
            }
            for key in keys
        ],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
