"""Summarize the checks that already exist. No threshold is approved."""


def summarize(rows):
    lines = []
    for name, ok, seconds in rows:
        lines.append("%s %s %.3f" % (name, "ok" if ok else "fail", seconds))
    lines.append("thresholds: none approved")
    failed = [name for name, ok, _seconds in rows if not ok]
    if rows and not failed:
        lines.append("failures: none")
        lines.append("knowledge ok")
    else:
        lines.append("failures: " + ", ".join(failed))
    return lines
