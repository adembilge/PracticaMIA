from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import current_user_id
from app.db import get_supabase

router = APIRouter()

SOURCE_COLUMNS = "id,name,topic,batch,portal_url,last_crawled_at,status"


class SourceRow(BaseModel):
    id: str
    name: str
    topic: str
    batch: str
    portal_url: str
    last_crawled_at: str | None
    status: str


@router.get("/api/sources")
async def list_sources(_user_id: UUID = Depends(current_user_id)) -> list[SourceRow]:
    client = get_supabase()
    result = client.table("sources").select(SOURCE_COLUMNS).execute()
    rows = result.data or []
    return [SourceRow.model_validate(row) for row in rows]