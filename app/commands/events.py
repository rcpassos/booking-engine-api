from typing import Literal
from pydantic import BaseModel
from datetime import datetime, timezone
from uuid import uuid4


class BookingCreated(BaseModel):
    type: Literal["BookingCreated"] = "BookingCreated"
    data: dict
    timestamp: datetime

    @classmethod
    def create(cls, user_id: str, slot: str):
        return cls(
            data={"id": str(uuid4()), "user_id": user_id, "slot": slot},
            timestamp=datetime.now(timezone.utc),
        )
