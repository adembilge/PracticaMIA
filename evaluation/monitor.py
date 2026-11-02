"""Event names only. A body, a path, or a password is refused."""

NAMES = ("retrieval", "citation", "index", "tool", "model")


def record(name):
    if name not in NAMES:
        raise ValueError("refused")
    return name


def alert(name):
    return ["alert: " + record(name)]
