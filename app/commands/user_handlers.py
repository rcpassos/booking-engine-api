from app.db import users
from app.models.user import UserIn
from app.auth.hash import hash_password
from uuid import uuid4
from datetime import datetime, timezone


def register_user(data: UserIn) -> dict:
    if users.find_one({"email": data.email}):
        raise ValueError("Email already registered")
    user = {
        "_id": str(uuid4()),
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "full_name": data.full_name,
        "created_at": datetime.now(timezone.utc),
    }
    users.insert_one(user)
    return user


def update_user(user_id: str, update_data: dict) -> dict:
    users.update_one({"_id": user_id}, {"$set": update_data})
    return users.find_one({"_id": user_id})


def update_password(user_id: str, new_password: str) -> None:
    users.update_one(
        {"_id": user_id}, {"$set": {"hashed_password": hash_password(new_password)}}
    )
