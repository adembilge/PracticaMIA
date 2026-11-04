"""Environment settings: case endpoints are disabled unless explicitly enabled."""
from dataclasses import dataclass
from os import environ


@dataclass(frozen=True)
class Settings:
    database_url: str = ""
    enable_demo_case_api: bool = False
    auth_issuer: str = ""
    auth_audience: str = ""
    auth_jwks_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=environ.get("DATABASE_URL", ""),
            enable_demo_case_api=environ.get("ENABLE_DEMO_CASE_API", "").lower()
            in {"1", "true", "yes"},
            auth_issuer=environ.get("AUTH_ISSUER", ""),
            auth_audience=environ.get("AUTH_AUDIENCE", ""),
            auth_jwks_url=environ.get("AUTH_JWKS_URL", ""),
        )
