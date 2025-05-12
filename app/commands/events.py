from typing import Literal
from pydantic import BaseModel
from datetime import datetime
from uuid import uuid4


class BookingCreated(BaseModel):
    type: Literal["BookingCreated"] = "BookingCreated"
    data: dict
    timestamp: datetime

    @classmethod
    def create(cls, user_id: str, slot: datetime):
        return cls(
            data={"id": str(uuid4()), "user_id": user_id, "slot": slot.isoformat()},
            timestamp=datetime.utcnow(),
        )
