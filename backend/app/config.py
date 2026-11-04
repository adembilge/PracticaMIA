"""Explicit runtime configuration. The demo API is disabled by default."""
from dataclasses import dataclass
from os import environ


@dataclass(frozen=True)
class Settings:
    database_url: str = ""
    enable_demo_case_api: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=environ.get("DATABASE_URL", ""),
            enable_demo_case_api=environ.get("ENABLE_DEMO_CASE_API", "").lower()
            in {"1", "true", "yes"},
        )
