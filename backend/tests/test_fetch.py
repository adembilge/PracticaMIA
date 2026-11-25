from urllib.robotparser import RobotFileParser

import httpx
import pytest

from ingest.fetch import (
    ALLOWED_HOST_SUFFIXES,
    MAX_REDIRECTS,
    TIMEOUT_SECONDS,
    USER_AGENT,
    FetchResult,
    fetch_url,
    host_allowed,
)


def test_host_allowed_rejects_unknown_host():
    assert host_allowed("https://evil.example/a") is False


def test_host_allowed_accepts_official_suffixes():
    assert host_allowed("https://www.poliziadistato.it/page") is True
    assert host_allowed("https://www.anagrafenazionale.interno.it/area-cittadino/") is True
    assert host_allowed("https://cittadinanza.dlci.interno.it/faq") is True


def test_allowed_host_suffixes_match_controller_resolution():
    assert ALLOWED_HOST_SUFFIXES == (
        "interno.gov.it",
        "poliziadistato.it",
        "portaleimmigrazione.it",
        "integrazionemigranti.gov.it",
        "normattiva.it",
        "gazzettaufficiale.it",
        "spid.gov.it",
        "agenziaentrate.gov.it",
        "inps.it",
        "inail.it",
        "salute.gov.it",
        "lavoro.gov.it",
        "giustizia.it",
        "registroimprese.it",
        "mur.gov.it",
        "cimea.it",
        "ilportaledellautomobilista.it",
        "anagrafenazionale.interno.it",
        "dlci.interno.it",
    )


def test_fetch_blocks_disallowed_host_without_http_call():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, content=b"ok")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    result = fetch_url(
        "https://evil.example/a",
        client,
        robots_for=lambda _host: RobotFileParser(),
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert result == FetchResult(
        url="https://evil.example/a",
        status=0,
        content_type="",
        body=b"",
        skipped_reason="host",
    )
    assert call_count == 0


def test_fetch_blocks_when_robots_parser_missing():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, content=b"ok")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    url = "https://www.poliziadistato.it/ok"
    result = fetch_url(
        url,
        client,
        robots_for=lambda _host: None,
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert result.skipped_reason == "robots"
    assert result.body == b""
    assert result.status == 0
    assert call_count == 0


def test_fetch_blocks_robots_disallow_path():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, content=b"secret")

    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /secret"].__iter__())

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    url = "https://www.poliziadistato.it/secret/page"
    result = fetch_url(
        url,
        client,
        robots_for=lambda _host: parser,
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert result.skipped_reason == "robots"
    assert result.body == b""
    assert call_count == 0


def test_fetch_waits_one_second_before_second_request_same_host():
    sleeps: list[float] = []
    times = iter([0.0, 0.0, 1.0])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html>ok</html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"].__iter__())
    host_next: dict[str, float] = {}
    url = "https://www.poliziadistato.it/a"

    fetch_url(
        url,
        client,
        robots_for=lambda _host: parser,
        now=lambda: next(times),
        host_next=host_next,
        sleep=sleeps.append,
    )
    fetch_url(
        url,
        client,
        robots_for=lambda _host: parser,
        now=lambda: next(times),
        host_next=host_next,
        sleep=sleeps.append,
    )
    assert sleeps == [1.0]


@pytest.mark.parametrize(
    "url",
    [
        "https://www.poliziadistato.it/login",
        "https://www.poliziadistato.it/area/Accedi",
    ],
)
def test_fetch_skips_login_paths(url: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html>login</html>",
            headers={"content-type": "text/html"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"].__iter__())
    result = fetch_url(
        url,
        client,
        robots_for=lambda _host: parser,
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert result.skipped_reason == "login"
    assert result.body == b""


def test_fetch_skips_unsupported_content_type():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"\x89PNG",
            headers={"content-type": "image/png"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"].__iter__())
    url = "https://www.poliziadistato.it/image"
    result = fetch_url(
        url,
        client,
        robots_for=lambda _host: parser,
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert result.skipped_reason == "type"
    assert result.body == b""


@pytest.mark.parametrize(
    "content_type,body",
    [
        ("text/html; charset=utf-8", b"<html>page</html>"),
        ("application/pdf", b"%PDF-1.4"),
    ],
)
def test_fetch_returns_body_for_html_and_pdf(content_type: str, body: bytes):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("User-Agent") == USER_AGENT
        return httpx.Response(200, content=body, headers={"content-type": content_type})

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"].__iter__())
    url = "https://www.poliziadistato.it/doc"
    result = fetch_url(
        url,
        client,
        robots_for=lambda _host: parser,
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert result.skipped_reason is None
    assert result.body == body
    assert result.status == 200


def test_fetch_uses_request_timeout_constant():
    observed: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request.extensions["timeout"]["connect"])
        return httpx.Response(
            200,
            content=b"<html/>",
            headers={"content-type": "text/html"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        max_redirects=MAX_REDIRECTS,
    )
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"].__iter__())
    fetch_url(
        "https://www.poliziadistato.it/t",
        client,
        robots_for=lambda _host: parser,
        now=lambda: 0.0,
        host_next={},
        sleep=lambda _s: None,
    )
    assert observed == [TIMEOUT_SECONDS]