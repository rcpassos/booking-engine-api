from pymongo import MongoClient
from app.config import settings

# Connect once
_client = MongoClient(settings.mongodb_uri)

# Select database by name
_db = _client[settings.mongodb_db]

# Collections
events = _db.events
read_models = _db.read_models
users = _db.users
