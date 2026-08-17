from datetime import date
from decimal import Decimal

from panganlens.domain.models import PriceObservation, PriceScope
from panganlens.validation.quality import classify_batch


def row(price: str, capture: str, method: str = "pihps_json") -> PriceObservation:
    return PriceObservation(
        observation_date=date(2026, 8, 14),
        scope=PriceScope.REGION,
        commodity_id="com_cabai_rawit_merah",
        channel_id="traditional",
        price=Decimal(price),
        source_capture_id=capture,
        source_method=method,
        region_id="province-dki-jakarta",
    )


def test_exact_duplicate_keeps_one_clean_row():
    result = classify_batch(
        [
            row("60750", "capture-a", "pihps_json"),
            row("60750", "capture-b", "pihps_report"),
        ]
    )

    assert len(result.clean) == 1
    assert len(result.exact_duplicates) == 1
    assert not result.conflicts
    assert result.can_publish


def test_conflicting_values_quarantine_the_whole_business_key():
    result = classify_batch(
        [
            row("60750", "capture-a"),
            row("60800", "capture-b"),
        ]
    )

    assert not result.clean
    assert not result.exact_duplicates
    assert len(result.conflicts) == 2
    assert not result.can_publish
