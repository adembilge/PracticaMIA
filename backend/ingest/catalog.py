from pathlib import Path
from typing import Literal

import yaml

from ingest.models import SourceSpec


def load_sources(
    batch: Literal["a", "b", "c", "all"],
    path: Path | None = None,
) -> list[SourceSpec]:
    if path is None:
        path = Path(__file__).with_name("sources.yaml")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    specs = [SourceSpec.model_validate(item) for item in data["sources"]]
    if batch == "all":
        return specs
    return [s for s in specs if s.batch == batch]