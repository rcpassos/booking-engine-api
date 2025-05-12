from app.db import events
from app.commands.events import BookingCreated


def handle_create_booking(user_id: str, slot: str) -> dict:
    # slot as ISO string
    event = BookingCreated.create(user_id=user_id, slot=slot)
    events.insert_one(event.model_dump())
    return event.data
