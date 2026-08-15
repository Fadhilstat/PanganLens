import json
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
    validate_schema_contract,
    verify_payload_text,
)


class FakeResponse:
    def __init__(
        self,
        payload,
        status_code=200,
        content_type="application/json",
        extra_headers=None,
    ):
        self.payload = payload
        self.status_code = status_code
        rendered = json.dumps(payload).encode("utf-8")
        self.content = rendered
        self.headers = {"content-type": content_type, "content-length": str(len(rendered))}
        if extra_headers:
            self.headers.update(extra_headers)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def iter_content(self, chunk_size):
        del chunk_size
        yield self.content


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def make_client(response, max_payload_bytes=2_000_000):
    return PihpsWebsiteClient(
        base_url="https://example.test",
        session=FakeSession(response),
        allowed_hosts=frozenset({"example.test"}),
        max_payload_bytes=max_payload_bytes,
    )


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


def test_response_shape_normalizes_dynamic_date_keys():
    shape = response_shape(
        [
            {"name": "A", "14/08/2026": 1},
            {"name": "B", "13/08/2026": 2},
        ]
    )
    assert shape.row_count == 2
    assert shape.normalized_keys == ("<date>", "name")
    assert len(shape.schema_fingerprint) == 64


def test_schema_contract_fails_closed_on_new_field():
    rows = [{"id": "13", "name": "A", "unexpected": True}]
    with pytest.raises(PihpsInterfaceError, match="schema changed"):
        validate_schema_contract(rows, frozenset({"id", "name"}))


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


def test_client_records_hashes_and_disables_redirects():
    response = FakeResponse({"data": [{"x": 1}]})
    client = make_client(response)
    request = GridRequest(
        price_type_id=1,
        comcat_id="com_3",
        province_id="13",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 14),
    )
    capture = client.fetch_grid_capture(request)
    assert capture.rows == ({"x": 1},)
    assert len(capture.evidence.payload_sha256) == 64
    assert len(capture.evidence.request_fingerprint) == 64
    assert verify_payload_text(capture.payload_text, capture.evidence.payload_sha256)
    _, kwargs = client.session.calls[0]
    assert kwargs["allow_redirects"] is False
    assert kwargs["stream"] is True


def test_client_rejects_non_json_response():
    client = make_client(FakeResponse({"x": 1}, content_type="text/html"))
    with pytest.raises(PihpsInterfaceError, match="content-type"):
        client.fetch_reference("provinces")


def test_client_rejects_redirect():
    client = make_client(FakeResponse({"x": 1}, status_code=302))
    with pytest.raises(PihpsInterfaceError, match="redirect"):
        client.fetch_reference("provinces")


def test_client_rejects_oversized_payload_from_header():
    response = FakeResponse(
        {"data": [{"x": 1}]},
        extra_headers={"content-length": "999"},
    )
    client = make_client(response, max_payload_bytes=100)
    with pytest.raises(PihpsInterfaceError, match="size limit"):
        client.fetch_reference("provinces")


def test_client_rejects_non_https_source():
    with pytest.raises(ValueError, match="HTTPS"):
        PihpsWebsiteClient(
            base_url="http://example.test",
            allowed_hosts=frozenset({"example.test"}),
        )


def test_client_rejects_unapproved_host():
    with pytest.raises(ValueError, match="allowlisted"):
        PihpsWebsiteClient(base_url="https://example.test")
