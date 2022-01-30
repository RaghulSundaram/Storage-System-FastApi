from pydantic import BaseModel


class User(BaseModel):
    username: str
    fullname: str


class UserInDB(User):
    password: str
    _id: str

class UserInFrom(User):
    password: str

    


