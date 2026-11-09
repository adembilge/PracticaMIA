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
    enable_preparation_api: bool = False
    enable_agent_history_api: bool = False
    enable_private_document_api: bool = False
    private_document_key: str = ""
    private_document_scan_url: str = ""
    private_document_scan_host: str = ""
    private_document_scan_token: str = ""
    private_document_cron_secret: str = ""
    private_document_privacy_approved: bool = False
    private_document_controller: str = ""
    private_document_contact: str = ""
    preparation_document_key: str = ""
    preparation_target: str = ""
    preparation_database_fingerprint: str = ""
    deployment_environment: str = ""
    assistant_chat_model: str = ""
    assistant_llm_provider: str = "openai"
    assistant_openai_api_key: str = ""
    assistant_openrouter_api_key: str = ""
    assistant_usage_hash_key: str = ""
    assistant_daily_limit: int = 10
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
            enable_preparation_api=environ.get("ENABLE_PREPARATION_API", "").lower()
            in {"1", "true", "yes"},
            enable_agent_history_api=environ.get("ENABLE_AGENT_HISTORY_API", "").lower()
            in {"1", "true", "yes"},
            enable_private_document_api=environ.get("ENABLE_PRIVATE_DOCUMENT_API", "").lower()
            in {"1", "true", "yes"},
            private_document_key=environ.get("PRIVATE_DOCUMENT_KEY", ""),
            private_document_scan_url=environ.get("PRIVATE_DOCUMENT_SCAN_URL", ""),
            private_document_scan_host=environ.get("PRIVATE_DOCUMENT_SCAN_HOST", ""),
            private_document_scan_token=environ.get("PRIVATE_DOCUMENT_SCAN_TOKEN", ""),
            private_document_cron_secret=environ.get("CRON_SECRET", ""),
            private_document_privacy_approved=environ.get("PRIVATE_DOCUMENT_PRIVACY_APPROVED", "").lower()
            in {"1", "true", "yes"},
            private_document_controller=environ.get("PRIVATE_DOCUMENT_CONTROLLER", ""),
            private_document_contact=environ.get("PRIVATE_DOCUMENT_CONTACT", ""),
            preparation_document_key=environ.get("PREPARATION_DOCUMENT_KEY", ""),
            preparation_target=environ.get("PREPARATION_TARGET", ""),
            preparation_database_fingerprint=environ.get("PREPARATION_DATABASE_FINGERPRINT", ""),
            deployment_environment=environ.get("VERCEL_ENV", ""),
            assistant_chat_model=environ.get("ASSISTANT_CHAT_MODEL", "").strip(),
            assistant_llm_provider=environ.get("ASSISTANT_LLM_PROVIDER", "openai").strip().lower(),
            assistant_openai_api_key=environ.get("OPENAI_API_KEY", ""),
            assistant_openrouter_api_key=environ.get("OPENROUTER_API_KEY", ""),
            assistant_usage_hash_key=environ.get("ASSISTANT_USAGE_HASH_KEY", ""),
            assistant_daily_limit=int(environ.get("ASSISTANT_DAILY_LIMIT", "10")),
            knowledge_reviewer_subjects=frozenset(
                value.strip()
                for value in environ.get("KNOWLEDGE_REVIEWER_SUBJECTS", "").split(",")
                if value.strip()
            ),
            auth_issuer=environ.get("AUTH_ISSUER", ""),
            auth_audience=environ.get("AUTH_AUDIENCE", ""),
            auth_jwks_url=environ.get("AUTH_JWKS_URL", ""),
        )
