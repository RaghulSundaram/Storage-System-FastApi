from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, status, Form, UploadFile 
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from app.server import database as db
import os


SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: str | None = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str):
    user = await db.retrieve_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("sub")
        if id is None:
            raise credentials_exception
        token_data = TokenData(id=id)
    except JWTError:
        raise credentials_exception
    user = await db.retrieve_user_by_id(id)
    if user is None:
        raise credentials_exception
    return user


@app.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register", status_code=200)
async def register(username: str, password: str , fullname: str):
    if await db.retrieve_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username Already exists",
        )
    else:
        user_entry = {"username": username, "fullname": fullname, "password": get_password_hash(password)}
        inserted_user = await db.add_user(user_entry)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": inserted_user["id"]}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user


@app.post("/upload")
async def upload_file(file: UploadFile, current_user = Depends(get_current_user)):
    id = await db.upload_file(file, current_user)
    return {"id": str(id)}

@app.get("/download")
async def download_file(id: str, current_user = Depends(get_current_user)):
    file = await db.download_file(id, current_user)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    else:
        return StreamingResponse(file, media_type=file.metadata["contentType"])

@app.post("/share")
async def share_file(file_id: str, to_id: str, current_user = Depends(get_current_user)):
    if not await db.check_valid_user(to_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    elif not await db.check_file_owner(file_id, current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    elif await db.check_shared(file_id, to_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested resource is already shared with that account",
        )
    else:
        id = await db.share_file(file_id, to_id)
        return {"id": str(id)}
