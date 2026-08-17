"""Provider contracts for external food price sources."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from panganlens.domain.models import PriceObservation


@dataclass(frozen=True, slots=True)
class FetchRequest:
    """A provider-neutral request for a date range."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")


class PriceProvider(Protocol):
    """Interface implemented by every ingestion method."""

    provider_name: str
    source_method: str

    def fetch(self, request: FetchRequest) -> Sequence[PriceObservation]:
        """Fetch and normalize observations for the requested period."""
        ...
