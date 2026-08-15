from datetime import date
from decimal import Decimal

import pytest

from panganlens.domain.models import PriceObservation, PriceScope


def make_observation(**overrides):
    values = {
        "observation_date": date(2026, 8, 14),
        "scope": PriceScope.REGION,
        "commodity_id": "com_cabai_rawit_merah",
        "channel_id": "traditional",
        "price": Decimal("60750"),
        "source_capture_id": "capture-1",
        "source_method": "pihps_json",
        "region_id": "province-dki-jakarta",
        "market_id": None,
    }
    values.update(overrides)
    return PriceObservation(**values)


def test_business_key_is_independent_from_retrieval_method():
    first = make_observation(source_capture_id="a", source_method="pihps_json")
    second = make_observation(source_capture_id="b", source_method="pihps_report")

    assert first.business_key_hash() == second.business_key_hash()
    assert first.record_hash() == second.record_hash()


def test_record_hash_changes_when_price_changes():
    first = make_observation(price=Decimal("60750"))
    second = make_observation(price=Decimal("60800"))

    assert first.business_key_hash() == second.business_key_hash()
    assert first.record_hash() != second.record_hash()


def test_region_scope_requires_region_id():
    with pytest.raises(ValueError):
        make_observation(region_id=None)


def test_price_must_be_positive():
    with pytest.raises(ValueError):
        make_observation(price=Decimal("0"))


def test_market_business_key_matches_warehouse_grain():
    first = make_observation(
        scope=PriceScope.MARKET,
        region_id=None,
        market_id="market-1",
        channel_id="traditional",
    )
    second = make_observation(
        scope=PriceScope.MARKET,
        region_id=None,
        market_id="market-1",
        channel_id="alternate-label",
    )

    assert first.business_key_hash() == second.business_key_hash()


def test_market_scope_does_not_duplicate_region_dimension():
    with pytest.raises(ValueError):
        make_observation(
            scope=PriceScope.MARKET,
            region_id="province-dki-jakarta",
            market_id="market-1",
        )
