from typing import Literal

from pydantic import BaseModel, field_validator

TOPICS = {
    "immigrazione",
    "cittadinanza",
    "anagrafe",
    "identita_digitale",
    "lavoro_previdenza",
    "fisco",
    "sanita",
    "giustizia",
    "famiglia",
    "impresa",
    "istruzione",
    "mobilita",
    "casa",
}


class SourceSpec(BaseModel):
    id: str
    topic: str
    name: str
    batch: Literal["a", "b", "c"]
    portal_url: str
    urls: list[str]
    keywords: list[str]
    max_pages: int = 30

    @field_validator("topic")
    @classmethod
    def known_topic(cls, value: str) -> str:
        if value not in TOPICS:
            raise ValueError(value)
        return value

    @field_validator("portal_url", "urls")
    @classmethod
    def https_only(cls, value):
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not str(item).startswith("https://"):
                raise ValueError(item)
        return value