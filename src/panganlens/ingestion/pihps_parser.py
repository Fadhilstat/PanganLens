"""Strict parser for PIHPS grid rows before canonical ID mapping."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from panganlens.ingestion.pihps_interface import PihpsInterfaceError

DATE_COLUMN_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")
STATIC_GRID_KEYS = frozenset({"name", "level", "no"})
INTEGER_PATTERN = re.compile(r"^\d+$")
THOUSANDS_PATTERN = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")
MISSING_PRICE_MARKERS = frozenset({"", "-", "n/a", "na", "null", "none"})


@dataclass(frozen=True, slots=True)
class GridPricePoint:
    """One parsed source price before region or market ID resolution."""

    observation_date: date
    source_row_name: str
    source_row_level: str
    source_row_no: str
    price: Decimal


@dataclass(frozen=True, slots=True)
class GridParseResult:
    """Parsed points plus rows that were intentionally missing a price."""

    points: tuple[GridPricePoint, ...]
    missing_price_cells: int


def parse_grid_rows(
    rows: Sequence[Mapping[str, Any]],
    start_date: date | None = None,
    end_date: date | None = None,
) -> GridParseResult:
    """Parse dynamic PIHPS date columns and reject unreviewed schema changes."""

    points: list[GridPricePoint] = []
    missing_count = 0
    for row in rows:
        keys = {str(key) for key in row}
        date_keys = {key for key in keys if DATE_COLUMN_PATTERN.fullmatch(key)}
        unexpected = keys - STATIC_GRID_KEYS - date_keys
        if unexpected:
            raise PihpsInterfaceError(
                "PIHPS grid contains unreviewed non-date fields: "
                + ", ".join(sorted(unexpected))
            )
        if not date_keys:
            raise PihpsInterfaceError("PIHPS grid row does not contain any date columns")

        row_name = _required_text(row.get("name"), "name")
        row_level = _required_text(row.get("level"), "level")
        row_no = _required_text(row.get("no"), "no")
        for key in sorted(date_keys, key=_parse_source_date):
            observation_date = _parse_source_date(key)
            if start_date and observation_date < start_date:
                raise PihpsInterfaceError("PIHPS grid contains a date before the request window")
            if end_date and observation_date > end_date:
                raise PihpsInterfaceError("PIHPS grid contains a date after the request window")
            price = parse_source_price(row.get(key))
            if price is None:
                missing_count += 1
                continue
            points.append(
                GridPricePoint(
                    observation_date=observation_date,
                    source_row_name=row_name,
                    source_row_level=row_level,
                    source_row_no=row_no,
                    price=price,
                )
            )
    return GridParseResult(tuple(points), missing_count)


def parse_source_price(value: Any) -> Decimal | None:
    """Parse a positive integer rupiah value without guessing decimal notation."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise PihpsInterfaceError("PIHPS price cannot be boolean")
    if isinstance(value, int):
        return _positive_decimal(Decimal(value))
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise PihpsInterfaceError("PIHPS price contains an unexpected decimal fraction")
        return _positive_decimal(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise PihpsInterfaceError("PIHPS price contains an unexpected decimal fraction")
        return _positive_decimal(Decimal(str(int(value))))

    text = str(value).strip().lower()
    if text in MISSING_PRICE_MARKERS:
        return None
    text = text.removeprefix("rp").strip().replace(" ", "")
    if INTEGER_PATTERN.fullmatch(text):
        normalized = text
    elif THOUSANDS_PATTERN.fullmatch(text):
        normalized = text.replace(".", "").replace(",", "")
    else:
        raise PihpsInterfaceError("PIHPS price format is not recognized safely")
    try:
        return _positive_decimal(Decimal(normalized))
    except InvalidOperation as exc:
        raise PihpsInterfaceError("PIHPS price could not be converted to Decimal") from exc


def _positive_decimal(value: Decimal) -> Decimal:
    if value <= 0:
        raise PihpsInterfaceError("PIHPS price must be positive when present")
    return value


def _required_text(value: Any, field_name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise PihpsInterfaceError(f"PIHPS grid field {field_name} must not be empty")
    return text


def _parse_source_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise PihpsInterfaceError(f"PIHPS date column is invalid: {value}") from exc
