from pymongo import MongoClient
from app.config import settings

_client = MongoClient(settings.mongodb_uri)
events = _client.booking.events
read_models = _client.booking.read_models
users = _client.booking.users
