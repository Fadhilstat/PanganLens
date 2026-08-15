"""Core domain models used before data reaches BigQuery."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class PriceScope(StrEnum):
    """Supported grains for a food price observation."""

    NATIONAL = "national"
    REGION = "region"
    MARKET = "market"


@dataclass(frozen=True, slots=True)
class PriceObservation:
    """A normalized price observation with a strict and explicit grain."""

    observation_date: date
    scope: PriceScope
    commodity_id: str
    channel_id: str
    price: Decimal
    source_capture_id: str
    source_method: str
    region_id: str | None = None
    market_id: str | None = None

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("price must be positive")
        if not self.commodity_id.strip():
            raise ValueError("commodity_id must not be empty")
        if not self.channel_id.strip():
            raise ValueError("channel_id must not be empty")
        if not self.source_capture_id.strip():
            raise ValueError("source_capture_id must not be empty")
        if not self.source_method.strip():
            raise ValueError("source_method must not be empty")

        if self.scope is PriceScope.NATIONAL:
            if self.region_id is not None or self.market_id is not None:
                raise ValueError("national observations cannot have region_id or market_id")
        elif self.scope is PriceScope.REGION:
            if not self.region_id or self.market_id is not None:
                raise ValueError("region observations require region_id and no market_id")
        elif self.scope is PriceScope.MARKET:
            if not self.market_id or self.region_id is not None:
                raise ValueError("market observations require market_id and no region_id")

    def business_key_payload(self) -> dict[str, str]:
        """Return fields that define one unique observation."""

        payload = {
            "observation_date": self.observation_date.isoformat(),
            "scope": self.scope.value,
            "commodity_id": self.commodity_id,
        }
        if self.scope is PriceScope.NATIONAL:
            payload["channel_id"] = self.channel_id
        elif self.scope is PriceScope.REGION:
            payload["channel_id"] = self.channel_id
            payload["region_id"] = self.region_id or ""
        elif self.scope is PriceScope.MARKET:
            payload["market_id"] = self.market_id or ""
        return payload

    def business_key_hash(self) -> str:
        """Hash the business key so duplicate checks remain source independent."""

        return _stable_hash(self.business_key_payload())

    def record_hash(self) -> str:
        """Hash the business key and value, excluding retrieval metadata."""

        payload = self.business_key_payload()
        payload["price"] = format(self.price.normalize(), "f")
        return _stable_hash(payload)


def _stable_hash(payload: dict[str, str]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
