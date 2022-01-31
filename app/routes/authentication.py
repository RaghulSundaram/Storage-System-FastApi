from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from app import database as db
from app.models.user import UserInDB, UserInFrom, UserLogin
from app.services.token import create_access_token
from app.services.security import verify_password, get_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"])

async def authenticate_user(username: str, password: str):
    user = await db.retrieve_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user


@router.post("/login", status_code=200)
#async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
async def login_for_access_token(user: UserLogin):
    user = await authenticate_user(user.username, user.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "username": user["username"], "fullname": user["fullname"]}


@router.post("/register", status_code=200)
async def register(user: UserInFrom):
    if user.username == "" or user.password == "" or user.fullname == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please fill all the fields",
        )
    elif await db.retrieve_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username Already exists",
        )
    else:
        user.password = get_password_hash(user.password)
        inserted_user: UserInDB = await db.add_user(user)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(inserted_user["_id"])}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}