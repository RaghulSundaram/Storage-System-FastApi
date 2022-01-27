from fastapi import UploadFile
import motor.motor_asyncio
from bson.objectid import ObjectId

MONGO_DETAILS = "mongodb://localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.Hackathon

gridfs_database = motor.motor_asyncio.AsyncIOMotorDatabase(client, "Hackathon")

user_collection = database.get_collection("users")

file_collection = database.get_collection("fs.files")

share_collection = database.get_collection("shares")

def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "fullname": user["fullname"],
        "username": user["username"],
        "password": user["password"],
    }

async def add_user(user_data: dict) -> dict:
    user = await user_collection.insert_one(user_data)
    new_user = await user_collection.find_one({"_id": user.inserted_id})
    return user_helper(new_user)

async def retrieve_user_by_id(id: str) -> dict:
    user = await user_collection.find_one({"_id": ObjectId(id)})
    if user:
        return user_helper(user)

async def retrieve_user_by_username(username: str) -> dict:
    user = await user_collection.find_one({"username": username})
    if user:
        return user_helper(user)


    
async def upload_file(file: UploadFile, user):
    fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(gridfs_database)
    file_id = await fs.upload_from_stream(
        file.filename,
        file.file,
        metadata={"contentType": file.content_type, "owner": ObjectId(user["id"])})
    return file_id


async def download_file(file_id, user):
    if await file_collection.find_one({"_id": ObjectId(file_id), "metadata.owner": ObjectId(user["id"])}):
        fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(gridfs_database)
        file = await fs.open_download_stream(ObjectId(file_id))
        return file


async def check_file_owner(file_id, user_id):
    if await file_collection.find_one({"_id": ObjectId(file_id), "metadata.owner": ObjectId(user_id)}):
        return True
    else:
        return False


async def check_valid_user(user_id):
    if await retrieve_user_by_id(user_id):
        return True
    else:
        return False
    

async def check_shared(file_id, user_id):
    if await share_collection.find_one({"file_id": ObjectId(file_id), "user_id": ObjectId(user_id)}):
        return True
    else:
        return False


async def share_file(file_id, to_id):
    share_entry = await share_collection.insert_one({"file_id": ObjectId(file_id), "user_id": ObjectId(to_id)})
    return share_entry.inserted_id
        
