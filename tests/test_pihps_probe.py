from panganlens.ingestion.pihps_candidates import PihpsCandidateProbe


class FakeResponse:
    status_code = 200
    headers = {"content-type": "application/json"}

    def json(self):
        return {"data": [{"id": 1}, {"id": 2}]}


class FakeSession:
    def get(self, url, headers, timeout):
        assert url.startswith("https://example.test")
        assert headers["X-Requested-With"] == "XMLHttpRequest"
        assert timeout == 10
        return FakeResponse()


def test_probe_accepts_json_list_inside_data_key():
    probe = PihpsCandidateProbe(
        base_url="https://example.test",
        timeout_seconds=10,
        session=FakeSession(),
    )

    result = probe.probe_reference("provinces")

    assert result.status_code == 200
    assert result.is_json
    assert result.item_count == 2
    assert result.error is None
