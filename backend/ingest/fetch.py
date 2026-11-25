from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

ALLOWED_HOST_SUFFIXES: tuple[str, ...] = (
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

USER_AGENT = "PracticaMIA-bot/0.1 (public administration study assistant)"
TIMEOUT_SECONDS = 20
MAX_REDIRECTS = 3
FORBIDDEN_URL_SUBSTRING = "0554_initaliainregola"


class FetchResult(BaseModel):
    url: str
    status: int
    content_type: str
    body: bytes
    skipped_reason: str | None


def host_allowed(url: str) -> bool:
    if FORBIDDEN_URL_SUBSTRING in url:
        return False
    host = (urlparse(url).hostname or "").casefold()
    for suffix in ALLOWED_HOST_SUFFIXES:
        s = suffix.casefold()
        if host == s or host.endswith("." + s):
            return True
    return False


def _skip(url: str, reason: str) -> FetchResult:
    return FetchResult(
        url=url,
        status=0,
        content_type="",
        body=b"",
        skipped_reason=reason,
    )


def fetch_url(
    url: str,
    client: httpx.Client,
    robots_for: Callable[..., object | None],
    now: Callable[[], float],
    host_next: dict[str, float],
    sleep: Callable[[float], None],
) -> FetchResult:
    if not host_allowed(url):
        return _skip(url, "host")

    host = (urlparse(url).hostname or "").casefold()
    parser = robots_for(host)
    if parser is None:
        return _skip(url, "robots")
    if not parser.can_fetch(USER_AGENT, url):
        return _skip(url, "robots")

    current = now()
    wait_until = host_next.get(host, 0.0)
    if current < wait_until:
        sleep(wait_until - current)
        current = now()

    response = client.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    host_next[host] = current + 1.0

    final_url = str(response.url)
    if not host_allowed(final_url):
        return _skip(url, "host")

    final_path = urlparse(final_url).path.casefold()
    if "login" in final_path or "accedi" in final_path:
        return FetchResult(
            url=url,
            status=response.status_code,
            content_type=_media_type(response.headers.get("content-type", "")),
            body=b"",
            skipped_reason="login",
        )

    media = _media_type(response.headers.get("content-type", ""))
    if media.casefold() not in ("text/html", "application/pdf"):
        return FetchResult(
            url=url,
            status=response.status_code,
            content_type=media,
            body=b"",
            skipped_reason="type",
        )

    return FetchResult(
        url=url,
        status=response.status_code,
        content_type=media,
        body=response.content,
        skipped_reason=None,
    )


def _media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip()