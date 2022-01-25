import motor.motor_asyncio

MONGO_DETAILS = "mongodb://localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.Hackathon

user_collection = database.get_collection("users")

def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "password": user["password"],
    }

async def add_user(user_data: dict) -> dict:
    user = await user_collection.insert_one(user_data)
    new_user = await user_collection.find_one({"_id": user.inserted_id})
    return user_helper(new_user)

async def retrieve_user(id: str) -> dict:
    user = await user_collection.find_one({"_id": ObjectId(id)})
    if user:
        return user_helper(user)

async def retrieve_user_by_username(username: str) -> dict:
    user = await user_collection.find_one({"username": username})
    if user:
        print(user)
        return user_helper(user)