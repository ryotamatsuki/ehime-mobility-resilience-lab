from scripts.build_network import build_a1_1


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload


def test_fetch_reuses_only_identical_requests(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.data, timeout))
        return FakeResponse(f"response-{len(calls)}".encode())

    build_a1_1.fetch.cache_clear()
    monkeypatch.setattr(build_a1_1.urllib.request, "urlopen", fake_urlopen)

    first = build_a1_1.fetch("https://example.invalid/data", timeout=10)
    second = build_a1_1.fetch("https://example.invalid/data", timeout=10)
    different_timeout = build_a1_1.fetch("https://example.invalid/data", timeout=11)
    different_body = build_a1_1.fetch("https://example.invalid/data", data=b"q=1", timeout=10)

    assert first == second == b"response-1"
    assert different_timeout == b"response-2"
    assert different_body == b"response-3"
    assert len(calls) == 3
    build_a1_1.fetch.cache_clear()
