from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    groq_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    user_daily_limit: int = 15
    global_daily_limit: int = 40


def get_settings() -> Settings:
    return Settings()
