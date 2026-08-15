from datetime import date

from panganlens.ingestion.pihps_interface import PihpsWebsiteClient
from panganlens.ingestion.pihps_probe import build_probe_summary, previous_business_day


class FakeClient(PihpsWebsiteClient):
    def __init__(self):
        pass

    def fetch_reference(self, name, params=None):
        if name == "provinces":
            return [{"province_id": 13, "province_name": "DKI Jakarta"}]
        if name == "commodities":
            return [{"comcat_id": "com_3", "commodity_name": "Beras"}]
        raise KeyError(name)

    def fetch_grid(self, request):
        assert request.province_id == "13"
        assert request.comcat_id == "com_3"
        return [{"name": "DKI Jakarta", "2026-08-14": 15000}]


def test_previous_business_day_skips_weekend():
    assert previous_business_day(date(2026, 8, 15)) == date(2026, 8, 14)
    assert previous_business_day(date(2026, 8, 17)) == date(2026, 8, 14)


def test_probe_summary_contains_schema_only_evidence():
    summary = build_probe_summary(FakeClient(), date(2026, 8, 15))

    assert summary["status"] == "pass"
    assert summary["probe_window"]["end_date"] == "2026-08-14"
    assert summary["response_shapes"]["grid"]["row_count"] == 1
    assert summary["response_shapes"]["grid"]["row_keys"] == ("2026-08-14", "name")
