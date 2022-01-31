from fastapi import Depends, APIRouter, HTTPException, status, UploadFile
from fastapi.responses import StreamingResponse
from app import database as db
from app.services.token import get_current_user

router = APIRouter()

@router.post("/file/upload", status_code=200)
async def upload_file(file: UploadFile, current_user = Depends(get_current_user)):
    id = await db.upload_file(file, current_user["_id"])
    if not id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )        
    else:
        return {"details": "Uploaded successfully"}


@router.get("/file/download", status_code=200)
async def download_file(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]) and not await db.check_shared(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource cannot be accessed by the user",
        )    
    else:
        file = await db.download_file(file_id)
        return StreamingResponse(file, media_type=file.metadata["contentType"])


@router.post("/file/share", status_code=200)
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


@router.put("/file/revoke", status_code=200)
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

@router.get("/files", status_code=200)
async def get_owned_files(current_user = Depends(get_current_user)):
    return { "files": await db.get_owned_files(current_user["_id"]) }


@router.get("/file/shared-users", status_code=200)
async def get_shared_users(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource is not owned by the user",
        )
    else:
        return { "users": await db.get_shared_users(file_id) }


@router.put("/file/rename", status_code=200)
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


@router.delete("/file/delete", status_code=200)
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


@router.get("/file/details", status_code=200)
async def get_file_details(file_id: str, current_user = Depends(get_current_user)):
    if not await db.check_file_owner(file_id, current_user["_id"]) and not await db.check_shared(file_id, current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested resource cannot be accessed by the user",
        )    
    else:
        return { "details": await db.get_file_details(file_id) } 
