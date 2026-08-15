"""Exact canonical mapping for PIHPS source entities.

Source labels are never promoted to warehouse IDs by guesswork. A row must match
an explicit reviewed mapping key before it can become a validated candidate.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class EntityType(StrEnum):
    """Canonical entity families that may be resolved from PIHPS source data."""

    COMMODITY = "commodity"
    CHANNEL = "channel"
    REGION = "region"
    MARKET = "market"


@dataclass(frozen=True, slots=True)
class SourceMappingKey:
    """Source-side identity used for exact mapping."""

    entity_type: EntityType
    source_system: str
    source_id: str | None = None
    source_name: str | None = None
    source_level: str | None = None
    parent_source_id: str | None = None

    def normalized(self) -> SourceMappingKey:
        """Return a deterministic representation suitable for exact lookup."""

        source_system = _normalize_text(self.source_system)
        if not source_system:
            raise ValueError("source_system must not be empty")

        source_id = _normalize_optional_id(self.source_id)
        source_name = _normalize_optional_text(self.source_name)
        source_level = _normalize_optional_text(self.source_level)
        parent_source_id = _normalize_optional_id(self.parent_source_id)
        if not source_id and not source_name:
            raise ValueError("source_id or source_name must be provided")

        return SourceMappingKey(
            entity_type=self.entity_type,
            source_system=source_system,
            source_id=source_id,
            source_name=source_name,
            source_level=source_level,
            parent_source_id=parent_source_id,
        )


@dataclass(frozen=True, slots=True)
class CanonicalMapping:
    """One reviewed source-to-canonical mapping."""

    key: SourceMappingKey
    canonical_id: str
    mapping_version: int = 1

    def __post_init__(self) -> None:
        if not self.canonical_id.strip():
            raise ValueError("canonical_id must not be empty")
        if self.mapping_version <= 0:
            raise ValueError("mapping_version must be positive")


class MappingRegistry:
    """In-memory exact mapping registry used before staging publication."""

    def __init__(self, mappings: tuple[CanonicalMapping, ...]) -> None:
        index: dict[SourceMappingKey, CanonicalMapping] = {}
        for mapping in mappings:
            normalized_key = mapping.key.normalized()
            if normalized_key in index:
                raise ValueError("duplicate source mapping key")
            index[normalized_key] = mapping
        self._index = index

    def resolve(self, key: SourceMappingKey) -> CanonicalMapping | None:
        """Resolve one source key exactly or return None when it is not reviewed."""

        return self._index.get(key.normalized())

    def require(self, key: SourceMappingKey) -> CanonicalMapping:
        """Resolve one source key and fail closed if no mapping exists."""

        mapping = self.resolve(key)
        if mapping is None:
            raise KeyError("source entity is not mapped to a canonical ID")
        return mapping


def _normalize_optional_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text.strip())
    return text.casefold()
