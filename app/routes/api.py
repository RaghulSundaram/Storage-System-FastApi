from fastapi import APIRouter

from app.routes import authentication, file, user

router = APIRouter()

router.include_router(authentication.router, tags=["authentication"])
router.include_router(user.router, tags=["users"])
router.include_router(file.router, tags=["files"])
