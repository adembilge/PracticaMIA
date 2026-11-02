"""One checked reply. The model does not set the stop."""
import os

LOCAL = {"reply": "The model is not configured."}
FIELDS = ("reply", "name", "address")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _checked(payload):
    if not isinstance(payload, dict) or not set(payload) <= set(FIELDS) or "reply" not in payload:
        raise ValueError("rejected")
    if not _text(payload["reply"]):
        raise ValueError("rejected")
    result = {"reply": payload["reply"]}
    for key in ("name", "address"):
        if key not in payload:
            continue
        if not _text(payload[key]):
            raise ValueError("rejected")
        result[key] = payload[key]
    return result


def complete(prompt, transport=None):
    if not _text(prompt):
        raise ValueError("rejected")
    provider = os.environ.get("PAPERPILOT_MODEL", "local")
    if provider == "local":
        return dict(LOCAL)
    if provider != "configured":
        raise ValueError("unknown model provider: %s" % provider)
    if transport is None:
        raise RuntimeError("provider failed")
    return _checked(transport(prompt))
