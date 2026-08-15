"""Batch checks for duplicate and conflicting observations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from panganlens.domain.models import PriceObservation


@dataclass(frozen=True, slots=True)
class BatchQualityResult:
    """Classification result before a batch is allowed into the core layer."""

    clean: tuple[PriceObservation, ...]
    exact_duplicates: tuple[PriceObservation, ...]
    conflicts: tuple[PriceObservation, ...]

    @property
    def can_publish(self) -> bool:
        return not self.conflicts


def classify_batch(observations: Iterable[PriceObservation]) -> BatchQualityResult:
    """Separate clean rows, exact duplicates, and value conflicts."""

    by_key: dict[str, list[PriceObservation]] = defaultdict(list)
    for observation in observations:
        by_key[observation.business_key_hash()].append(observation)

    clean: list[PriceObservation] = []
    exact_duplicates: list[PriceObservation] = []
    conflicts: list[PriceObservation] = []

    for group in by_key.values():
        record_hashes = {item.record_hash() for item in group}
        if len(record_hashes) > 1:
            conflicts.extend(group)
            continue

        clean.append(group[0])
        exact_duplicates.extend(group[1:])

    return BatchQualityResult(
        clean=tuple(clean),
        exact_duplicates=tuple(exact_duplicates),
        conflicts=tuple(conflicts),
    )
