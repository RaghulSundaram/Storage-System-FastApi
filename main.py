from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from server import database as db


SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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


@app.post("/token", response_model=Token)
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
async def register(username: str = Form(...), password: str = Form(...)):
    if await db.retrieve_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username Already exists",
        )
    else:
        user_entry = {"username": username, "password": get_password_hash(password)}
        inserted_user = await db.add_user(user_entry)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": inserted_user["id"]}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}


