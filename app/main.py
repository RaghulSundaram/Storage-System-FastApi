from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from app.server import database as db
from app.models.user import User, UserInDB, UserInFrom, UserToReturn



SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str

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


def create_access_token(data: dict, expires_delta: timedelta):
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
    except JWTError:
        raise credentials_exception
    user = await db.retrieve_user_by_id(id)
    if user is None:
        raise credentials_exception
    return user


@app.post("/login", status_code=200)
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
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "username": user["username"], "fullname": user["fullname"]}


@app.post("/register", status_code=200)
async def register(user: UserInFrom):
    if await db.retrieve_user_by_username(user.username):
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


@app.post("/file/upload", status_code=200)
async def upload_file(file: UploadFile, current_user = Depends(get_current_user)):
    id = await db.upload_file(file, current_user["_id"])
    if not id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )        
    else:
        return {"details": "Uploaded successfully"}


@app.get("/file/download", status_code=200)
async def download_file(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]) and not await db.check_shared(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource cannot be accessed by the user",
        )    
    else:
        file = await db.download_file(file_id)
        return StreamingResponse(file, media_type=file.metadata["contentType"])


@app.post("/file/share", status_code=200)
async def share_file(file_id: str, to_id: str, current_user = Depends(get_current_user)):
    if to_id == current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested resource is already owned by the user",
        )
    elif not await db.check_valid_user(to_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    elif not await db.check_file_owner(file_id, current_user["_id"]):
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
        if not id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )        
        else:
            return {"details": "Shared successfully"}


@app.put("/file/revoke", status_code=200)
async def revoke_file(file_id: str, to_id: str, current_user = Depends(get_current_user)):
    if to_id == current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested resource is already owned by the user",
        )
    elif not await db.check_valid_user(to_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    elif not await db.check_file_owner(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    elif not await db.check_shared(file_id, to_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested resource is already not shared with that account",
        )
    else:
        result = await db.revoke_share_file(file_id, to_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )        
        else:
            return {"details": "Revoked successfully"}



@app.get("/users", status_code=200)
async def get_all_users(current_user = Depends(get_current_user)):
    return { "users": await db.get_all_users(current_user["_id"]) }


@app.get("/files", status_code=200)
async def get_owned_files(current_user = Depends(get_current_user)):
    return { "files": await db.get_owned_files(current_user["_id"]) }


@app.get("/user/shared-files", status_code=200)
async def get_shared_files(current_user = Depends(get_current_user)):
    return { "files": await db.get_shared_files(current_user["_id"]) } 


@app.get("/file/shared-users", status_code=200)
async def get_shared_users(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    else:
        return { "users": await db.get_shared_users(file_id) }


@app.put("/file/rename", status_code=200)
async def rename_file(file_id: str, filename: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    else:
        result = await db.rename_file(file_id, filename)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )        
        else:
            return {"details": "Renamed successfully"}


@app.delete("/file/delete", status_code=200)
async def delete_file(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    else:
        result = await db.delete_file(file_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )        
        else:
            return {"details": "Deleted successfully"}


@app.get("/file/details", status_code=200)
async def get_file_details(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]) and not await db.check_shared(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource cannot be accessed by the user",
        )    
    else:
        return { "details": await db.get_file_details(file_id) } 
