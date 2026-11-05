"""Read-only external smoke audit of the user's own Vercel production URLs.

This is intentionally NOT a load test or a scanner: each path is requested
once, with GET, without cookies, credentials, payloads, third-party targets,
or touching cases / administrative records.

Run: python audit/live_production_smoke.py
Produces audit/results/live_production_smoke.json and .md.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FRONTEND = "https://practicamia.vercel.app"
BACKEND = "https://practicamia-api.vercel.app"
MAX_CAPTURE = 131072
CASES_ID = "00000000-0000-0000-0000-000000000001"


class PageA11y(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = ""
        self.viewport = False
        self.main = False
        self.title = False
    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "html":
            self.lang = props.get("lang", "")
        elif tag == "meta" and props.get("name", "").lower() == "viewport":
            self.viewport = True
        elif tag == "main":
            self.main = True
        elif tag == "title":
            self.title = True


def request_once(url):
    started = monotonic()
    headers = {"User-Agent": "PracticaMIA-ReadOnly-System-Audit/1.0",
               "Accept": "text/html,application/json"}
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=10) as result:
            status = result.status
            response_headers = result.headers
            raw = result.read(MAX_CAPTURE)
    except HTTPError as exc:
        status = exc.code
        response_headers = exc.headers
        raw = exc.read(MAX_CAPTURE)
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": None, "error": type(exc).__name__,
                "elapsed_ms": round((monotonic() - started) * 1000)}
    return {
        "status": status,
        "elapsed_ms": round((monotonic() - started) * 1000),
        "sampled_bytes": len(raw),
        "content_type": response_headers.get("content-type", ""),
        "cache_control": response_headers.get("cache-control", ""),
        "x_content_type_options": response_headers.get("x-content-type-options", ""),
        "referrer_policy": response_headers.get("referrer-policy", ""),
        "content_security_policy_present": bool(response_headers.get("content-security-policy")),
        "html": raw.decode("utf-8", errors="replace")[:MAX_CAPTURE],
    }


def main():
    checks = [
        ("frontend-home", FRONTEND + "/", {200}, "public"),
        ("frontend-account", FRONTEND + "/account", {200}, "public"),
        ("frontend-review-hidden", FRONTEND + "/knowledge/review", {404}, "private"),
        ("frontend-assistant-hidden", FRONTEND + "/cases/" + CASES_ID + "/assistant", {404}, "private"),
        ("frontend-review-api-hidden", FRONTEND + "/api/knowledge/review/browser-queue", {404}, "private"),
        ("frontend-case-api-no-cookie", FRONTEND + "/api/cases", {401, 503}, "private"),
        ("backend-health", BACKEND + "/health", {200}, "health"),
        ("backend-cases-unauth", BACKEND + "/api/v1/cases", {401, 404}, "private"),
        ("backend-review-unauth", BACKEND + "/api/v1/knowledge/review/queue", {401, 404}, "private"),
        ("backend-openapi", BACKEND + "/openapi.json", {200, 404}, "openapi"),
    ]
    results = []
    for name, url, expected, kind in checks:
        response = request_once(url)
        status = response.get("status")
        if status is None or status in (403, 429):
            # A 403 could be deployment protection rather than application
            # authorization; we cannot assert auth behavior in that case.
            verdict = "inconclusive"
        else:
            verdict = "pass" if status in expected else "fail"
        public_url = url
        item = {
            "name": name, "url": public_url, "status": status,
            "verdict": verdict, "elapsed_ms": response.get("elapsed_ms"),
            "content_type": response.get("content_type", ""),
            "cache_control": response.get("cache_control", ""),
        }
        if response.get("error"):
            item["error_type"] = response["error"]
        if kind == "public" and status == 200:
            parser = PageA11y()
            parser.feed(response["html"])
            item["document_checks"] = {
                "html_language": parser.lang,
                "has_main_region": parser.main,
                "has_page_title": parser.title,
                "has_viewport": parser.viewport,
            }
            if not (parser.lang and parser.main and parser.title and parser.viewport):
                item["accessibility_warning"] = (
                    "One or more structural mobile/accessibility markers missing"
                )
        if kind == "health" and status == 200:
            try:
                health = json.loads(response["html"])
                if health.get("status") != "ok":
                    item["verdict"] = "fail"
            except (ValueError, TypeError):
                item["verdict"] = "fail"
        if kind == "openapi" and status == 200:
            try:
                schema = json.loads(response["html"])
                paths = schema.get("paths", {})
                # Diagnostics, never expose endpoint response bodies or tokens.
                item["documented_paths"] = len(paths)
                item["preview_knowledge_route_exposed"] = any(
                    "/knowledge/review" in path or
                    "/assistant/ask" in path for path in paths
                )
                if item["preview_knowledge_route_exposed"]:
                    item["verdict"] = "fail"
            except (ValueError, TypeError):
                item["verdict"] = "fail"
        if status == 200 and kind in ("public", "health"):
            item["security_headers"] = {
                "no_sniff": bool(response["x_content_type_options"]),
                "referrer_policy": bool(response["referrer_policy"]),
                "csp": response["content_security_policy_present"],
            }
        if kind == "private" and status == 200:
            # A privileged response delivered without auth is release-blocking.
            item["verdict"] = "fail"
        # Do not persist raw page text, response bodies, headers containing
        # cookies, public user data or credentials.
        results.append(item)
        print(f"{name}: {item['verdict']} HTTP {status} "
              f"({item['elapsed_ms']} ms)", flush=True)
        if "document_checks" in item:
            print("  HTML structure: " + json.dumps(item["document_checks"]),
                  flush=True)
        if "security_headers" in item:
            print("  Header presence: " + json.dumps(item["security_headers"]),
                  flush=True)
    summary = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_anonymous_get_no_rate_load",
        "passed": sum(row["verdict"] == "pass" for row in results),
        "failed": sum(row["verdict"] == "fail" for row in results),
        "inconclusive": sum(row["verdict"] == "inconclusive" for row in results),
        "checks": results,
    }
    output = Path("audit/results")
    output.mkdir(parents=True, exist_ok=True)
    (output / "live_production_smoke.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = ["# PracticaMIA — anonymous external production smoke",
             "", f"Timestamp UTC: {summary['utc']}",
             "",
             "| Check | HTTP | Verdict | Time (ms) |",
             "| --- | --- | --- | ---: |"]
    for row in results:
        lines.append(
            f"| {row['name']} | {row['status']} | {row['verdict']} | "
            f"{row['elapsed_ms']} |"
        )
    lines += [
        "",
        f"**{summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['inconclusive']} inconclusive.**",
        "",
        "All requests were anonymous GET only. No application changes, "
        "user records, writes, cookies or credentials.",
        "A passing smoke test is not an authenticated end-to-end test.",
        "A 403 may be an edge access restriction; it is inconclusive for "
        "application authorization, not proof of a functioning auth gate.",
    ]
    (output / "live_production_smoke.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )
    if summary["failed"]:
        raise SystemExit("Public endpoint or release safety smoke check failed")


if __name__ == "__main__":
    main()
