from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.auth import current_user_id
from app.db import get_supabase

router = APIRouter()

@router.delete("/api/account", status_code=204)
async def delete_account(user_id: UUID = Depends(current_user_id)) -> None:
    client = get_supabase()
    client.table("conversations").delete().eq("user_id", str(user_id)).execute()
    client.table("usage_daily").delete().eq("user_id", str(user_id)).execute()
    try:
        client.auth.admin.delete_user(str(user_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "upstream", "message": "The account could not be deleted."}) from exc