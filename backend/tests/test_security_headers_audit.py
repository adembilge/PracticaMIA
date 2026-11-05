"""Real TestClient response headers: check denied and successful paths."""
import pytest

HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


@pytest.mark.parametrize("path,expected_status", [
    ("/health", 200),
    ("/not-a-route", 404),
    ("/api/v1/cases", 401),
    ("/api/v1/knowledge/review/queue", 401),
])
def test_basic_security_headers_are_applied_on_all_api_responses(
    client, path, expected_status,
):
    result = client.get(path)
    assert result.status_code == expected_status
    for key, value in HEADERS.items():
        assert result.headers.get(key) == value, (path, key)
