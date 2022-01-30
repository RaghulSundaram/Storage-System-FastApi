from fastapi import UploadFile
import motor.motor_asyncio
from bson.objectid import ObjectId
import pymongo
from app.models.user import UserInDB, User, UserInFrom, UserToReturn

MONGO_DETAILS = "mongodb://localhost:27017"

client = pymongo.MongoClient("mongodb+srv://raghulsundaram:Raghul9248$@hackathon-db.vlnns.mongodb.net/Hackathon?retryWrites=true&w=majority")
# db = client.test

gridfs_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://raghulsundaram:Raghul9248$@hackathon-db.vlnns.mongodb.net/Hackathon?retryWrites=true&w=majority")

database = client.Hackathon

#gridfs_database = motor.motor_asyncio.AsyncIOMotorDatabase(client, "Hackathon")

user_collection = database.get_collection("users")

file_collection = database.get_collection("fs.files")

share_collection = database.get_collection("shares")

def stringify_id(obj: dict):
    obj["_id"] = str(obj["_id"])
    return obj

def change_key_owner(obj: dict):
    value = str(obj["metadata"]["owner"])
    del obj["metadata"]
    obj["owner"] = value
    return obj

async def add_user(user_data: UserInFrom):
    user = user_collection.insert_one(user_data.dict())
    new_user = user_collection.find_one({"_id": user.inserted_id})
    new_user = stringify_id(new_user)
    return new_user

async def retrieve_user_by_id(user_id: str):
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        user = stringify_id(user)
        return user

async def retrieve_user_by_username(username: str):
    user = user_collection.find_one({"username": username})
    if user:
        user = stringify_id(user)
        return user
     
async def upload_file(file: UploadFile, user_id: str):
    fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(gridfs_client.Hackathon)
    file_id = await fs.upload_from_stream(
        file.filename,
        file.file,
        metadata={"contentType": file.content_type, "owner": ObjectId(user_id)})
    return file_id


async def download_file(file_id):
    fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(gridfs_client.Hackathon)
    file = await fs.open_download_stream(ObjectId(file_id))
    return file


async def check_file_owner(file_id, user_id):
    if file_collection.find_one({"_id": ObjectId(file_id), "metadata.owner": ObjectId(user_id)}):
        return True
    else:
        return False


async def check_valid_user(user_id):
    if retrieve_user_by_id(user_id):
        return True
    else:
        return False
    

async def check_shared(file_id, user_id):
    if share_collection.find_one({"file_id": ObjectId(file_id), "user_id": ObjectId(user_id)}):
        return True
    else:
        return False


async def share_file(file_id, to_id):
    share_entry = share_collection.insert_one({"file_id": ObjectId(file_id), "user_id": ObjectId(to_id)})
    return share_entry.inserted_id
        

async def revoke_share_file(file_id, to_id):
    result = share_collection.delete_one({"file_id": ObjectId(file_id), "user_id": ObjectId(to_id)})
    return result


async def get_all_users(user_id: str):
    result = user_collection.find({},{"password": 0})
    result = [stringify_id({**item}) for item in result]
    return result


async def get_owned_files(user_id: str):
    result = file_collection.find({"metadata.owner": ObjectId(user_id)}, {"_id": 1, "filename": 1, "metadata.owner": 1})
    result = [change_key_owner(stringify_id({**item})) for item in result]
    return result


async def get_shared_files(user_id: str):
    file_ids = share_collection.find({"user_id": ObjectId(user_id)}, {"file_id": 1})
    files = []
    for file_id in file_ids:
        files.append(file_collection.find_one({"_id": file_id["file_id"]}, {"_id": 1, "metadata.owner": 1, "filename": 1}))
    
    files = [change_key_owner(stringify_id({**file})) for file in files]
    return files


async def get_shared_users(file_id: str):
    user_ids = share_collection.find({"file_id": ObjectId(file_id)}, {"user_id": 1})
    users = []
    for user_id in user_ids:
        users.append(user_collection.find_one({"_id": user_id["user_id"]}, {"password": 0}))

    users = [stringify_id(user) for user in users]
    return users


async def rename_file(file_id: str, filename: str):
    result = file_collection.update_one({"_id": ObjectId(file_id)}, {"$set": {"filename": filename}})
    return result


async def delete_file(file_id: str):
    result1 = file_collection.delete_one({"_id": ObjectId(file_id)})
    result2 = share_collection.delete_many({"file_id": ObjectId(file_id)})
    if result1 and result2:
        return True


async def get_file_details(file_id: str):
    result = file_collection.find_one({"_id": ObjectId(file_id)}, {"_id": 1, "metadata.owner": 1, "filename": 1})
    return change_key_owner(stringify_id({**result}))
