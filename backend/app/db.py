from supabase import Client, create_client

from app.config import get_settings


def get_supabase() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("supabase is not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)