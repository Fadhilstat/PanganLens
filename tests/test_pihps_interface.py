from datetime import date

import pytest
import requests

from panganlens.ingestion.pihps_interface import (
    GridRequest,
    PihpsInterfaceError,
    PihpsWebsiteClient,
    extract_rows,
    pick_reference_id,
    response_shape,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, content_type="application/json"):
        self.payload = payload
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_grid_request_builds_stable_params():
    request = GridRequest(
        price_type_id=1,
        comcat_id="com_3",
        province_id="13",
        regency_ids=("3171", "3172"),
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 14),
    )

    params = request.as_params()

    assert params["regency_id"] == "3171,3172"
    assert params["showKota"] == "true"
    assert params["showPasar"] == "false"
    assert params["start_date"] == "2026-08-10T00:00:00.000"
    assert params["end_date"] == "2026-08-14T00:00:00.000"


def test_grid_request_rejects_invalid_range():
    with pytest.raises(ValueError, match="end_date"):
        GridRequest(
            price_type_id=1,
            comcat_id="com_3",
            province_id="13",
            start_date=date(2026, 8, 14),
            end_date=date(2026, 8, 10),
        )


def test_extract_rows_accepts_known_containers():
    assert extract_rows([{"a": 1}]) == [{"a": 1}]
    assert extract_rows({"data": [{"a": 1}]}) == [{"a": 1}]
    assert extract_rows({"rows": [{"a": 1}]}) == [{"a": 1}]
    assert extract_rows({"result": [{"a": 1}]}) == [{"a": 1}]
    assert extract_rows({"items": [{"a": 1}]}) == [{"a": 1}]


def test_extract_rows_rejects_unknown_shape():
    with pytest.raises(PihpsInterfaceError, match="recognized row container"):
        extract_rows({"unexpected": []})


def test_response_shape_exposes_keys_not_values():
    shape = response_shape([{"province_id": 13, "name": "DKI"}, {"name": "Banten"}])

    assert shape.row_count == 2
    assert shape.row_keys == ("name", "province_id")


def test_pick_reference_id_prefers_requested_value():
    rows = [{"province_id": 11}, {"province_id": 13}]

    assert pick_reference_id(rows, ("province_id", "id", "value"), preferred="13") == "13"


def test_pick_reference_id_can_require_prefix():
    rows = [{"comcat_id": "cat_1"}, {"comcat_id": "com_3"}]

    assert pick_reference_id(
        rows,
        ("comcat_id", "id", "value"),
        required_prefix="com_",
    ) == "com_3"


def test_client_uses_expected_grid_endpoint_and_headers():
    session = FakeSession(FakeResponse({"data": [{"x": 1}]}))
    client = PihpsWebsiteClient(base_url="https://example.test", session=session)
    request = GridRequest(
        price_type_id=1,
        comcat_id="com_3",
        province_id="13",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 14),
    )

    rows = client.fetch_grid(request)

    assert rows == [{"x": 1}]
    url, kwargs = session.calls[0]
    assert url.endswith("/WebSite/TabelHarga/GetGridDataKomoditas")
    assert kwargs["headers"]["X-Requested-With"] == "XMLHttpRequest"
    assert kwargs["headers"]["User-Agent"].startswith("PanganLens/")


def test_client_rejects_non_json_response():
    session = FakeSession(FakeResponse(ValueError("bad json"), content_type="text/html"))
    client = PihpsWebsiteClient(base_url="https://example.test", session=session)

    with pytest.raises(PihpsInterfaceError, match="non-JSON"):
        client.fetch_reference("provinces")
