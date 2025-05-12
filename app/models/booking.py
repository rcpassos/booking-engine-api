from pydantic import BaseModel
from typing import List


class BookingView(BaseModel):
    id: str
    user_id: str
    slot: str


class BookingList(BaseModel):
    bookings: List[BookingView]
