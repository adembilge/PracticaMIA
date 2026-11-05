"""Environment settings: case endpoints are disabled unless explicitly enabled."""
from dataclasses import dataclass
from os import environ


@dataclass(frozen=True)
class Settings:
    database_url: str = ""
    enable_demo_case_api: bool = False
    enable_knowledge_catalog_api: bool = False
    enable_knowledge_review_api: bool = False
    enable_knowledge_search_api: bool = False
    enable_assistant_api: bool = False
    deployment_environment: str = ""
    assistant_chat_model: str = ""
    assistant_openai_api_key: str = ""
    knowledge_reviewer_subjects: frozenset[str] = frozenset()
    auth_issuer: str = ""
    auth_audience: str = ""
    auth_jwks_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=environ.get("DATABASE_URL", ""),
            enable_demo_case_api=environ.get("ENABLE_DEMO_CASE_API", "").lower()
            in {"1", "true", "yes"},
            enable_knowledge_catalog_api=environ.get("ENABLE_KNOWLEDGE_CATALOG_API", "").lower()
            in {"1", "true", "yes"},
            enable_knowledge_review_api=environ.get("ENABLE_KNOWLEDGE_REVIEW_API", "").lower()
            in {"1", "true", "yes"},
            enable_knowledge_search_api=environ.get("ENABLE_KNOWLEDGE_SEARCH_API", "").lower()
            in {"1", "true", "yes"},
            enable_assistant_api=environ.get("ENABLE_ASSISTANT_API", "").lower()
            in {"1", "true", "yes"},
            deployment_environment=environ.get("VERCEL_ENV", ""),
            assistant_chat_model=environ.get("ASSISTANT_CHAT_MODEL", "").strip(),
            assistant_openai_api_key=environ.get("OPENAI_API_KEY", ""),
            knowledge_reviewer_subjects=frozenset(
                value.strip()
                for value in environ.get("KNOWLEDGE_REVIEWER_SUBJECTS", "").split(",")
                if value.strip()
            ),
            auth_issuer=environ.get("AUTH_ISSUER", ""),
            auth_audience=environ.get("AUTH_AUDIENCE", ""),
            auth_jwks_url=environ.get("AUTH_JWKS_URL", ""),
        )
