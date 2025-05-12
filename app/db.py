from pymongo import MongoClient
from app.config import settings

_client = MongoClient(settings.mongodb_uri)
events = _client.get_database("booking").get_collection("events")
read_models = _client.get_database("booking").get_collection("read_models")
