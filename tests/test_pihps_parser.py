from datetime import date
from decimal import Decimal

import pytest

from panganlens.ingestion.pihps_interface import PihpsInterfaceError
from panganlens.ingestion.pihps_parser import parse_grid_rows, parse_source_price


def test_parse_grid_rows_handles_dynamic_date_columns():
    rows = [
        {
            "no": "1",
            "level": "province",
            "name": "Contoh Wilayah",
            "13/08/2026": "15.000",
            "14/08/2026": "16,000",
        }
    ]
    result = parse_grid_rows(
        rows,
        start_date=date(2026, 8, 13),
        end_date=date(2026, 8, 14),
    )
    assert len(result.points) == 2
    assert result.points[0].observation_date == date(2026, 8, 13)
    assert result.points[0].price == Decimal("15000")
    assert result.points[1].price == Decimal("16000")
    assert result.missing_price_cells == 0


def test_parse_grid_rows_counts_missing_prices_without_converting_to_zero():
    rows = [
        {
            "no": "1",
            "level": "province",
            "name": "Contoh Wilayah",
            "14/08/2026": "-",
        }
    ]
    result = parse_grid_rows(rows)
    assert result.points == ()
    assert result.missing_price_cells == 1


def test_parse_grid_rows_fails_closed_on_unreviewed_static_field():
    rows = [
        {
            "no": "1",
            "level": "province",
            "name": "Contoh Wilayah",
            "unexpected": "x",
            "14/08/2026": "15000",
        }
    ]
    with pytest.raises(PihpsInterfaceError, match="unreviewed"):
        parse_grid_rows(rows)


def test_parse_source_price_rejects_ambiguous_decimal_fraction():
    with pytest.raises(PihpsInterfaceError, match="not recognized safely"):
        parse_source_price("12,50")


def test_parse_source_price_rejects_zero():
    with pytest.raises(PihpsInterfaceError, match="positive"):
        parse_source_price(0)
