from fastapi import Depends, APIRouter
from app import database as db
from app.services.token import get_current_user

router = APIRouter()

@router.get("/users", status_code=200)
async def get_all_users(current_user = Depends(get_current_user)):
    return { "users": await db.get_all_users(current_user["_id"]) }

@router.get("/user/shared-files", status_code=200)
async def get_shared_files(current_user = Depends(get_current_user)):
    return { "files": await db.get_shared_files(current_user["_id"]) } 