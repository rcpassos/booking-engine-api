from app.db import events
from app.models.booking import BookingView, BookingList


def handle_list_bookings(user_id: str) -> BookingList:
    # only fetch bookings for this user
    cursor = events.find({"type": "BookingCreated", "data.user_id": user_id})
    items = [
        BookingView(
            id=doc["data"]["id"],
            user_id=doc["data"]["user_id"],
            slot=doc["data"]["slot"],
        )
        for doc in cursor
    ]
    return BookingList(bookings=items)
