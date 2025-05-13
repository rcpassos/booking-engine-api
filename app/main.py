from fastapi import FastAPI, Depends, HTTPException, Body, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import EmailStr

from app.config import settings
from app.auth.jwt import ALGORITHM, create_access_token
from app.auth.dependencies import get_current_user
from app.auth.hash import verify_password
from app.commands.user_handlers import register_user, update_user, update_password
from app.commands.booking_handlers import handle_create_booking
from app.queries.booking_handlers import handle_list_bookings
from app.models.user import UserIn, UserOut, UserUpdate, PasswordUpdate
from app.models.booking import BookingList
from app.email import send_recovery_email
from app.db import users
from app.auth.api_key import get_api_key

app = FastAPI(
    title="Booking Engine",
    dependencies=[Depends(get_api_key)],
)


# -- Register --
@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(data: UserIn):
    try:
        user = register_user(data)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {
        "id": user["_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "created_at": user["created_at"],
    }


# -- Login --
@app.post("/auth/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = users.find_one({"email": form.username})
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(subject=user["_id"])
    return {"access_token": token, "token_type": "bearer"}


# -- Recover password --
@app.post("/auth/recover-password")
def recover_password(email: EmailStr = Body(..., embed=True)):
    user = users.find_one({"email": email})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    # token valid for 60 minutes
    token = create_access_token(
        subject=user["_id"], expires_delta=timedelta(minutes=60)
    )
    send_recovery_email(email, token)
    return {"msg": "Recovery email sent"}


# -- Reset password --
@app.post("/auth/reset-password")
def reset_password(token: str, new_password: str):
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")
    update_password(user_id, new_password)
    return {"msg": "Password updated"}


# -- Get current user --
@app.get("/users/me", response_model=UserOut)
def read_profile(user_id: str = Depends(get_current_user)):
    u = users.find_one({"_id": user_id})
    return {
        "id": u["_id"],
        "email": u["email"],
        "full_name": u["full_name"],
        "created_at": u["created_at"],
    }


# -- Update profile --
@app.put("/users/me", response_model=UserOut)
def update_profile(data: UserUpdate, user_id: str = Depends(get_current_user)):
    updated = update_user(user_id, data.model_dump())
    return {
        "id": updated["_id"],
        "email": updated["email"],
        "full_name": updated["full_name"],
        "created_at": updated["created_at"],
    }


# -- Change password (authenticated) --
@app.put("/users/me/password")
def change_password(data: PasswordUpdate, user_id: str = Depends(get_current_user)):
    user = users.find_one({"_id": user_id})
    if not verify_password(data.old_password, user["hashed_password"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Old password incorrect")
    update_password(user_id, data.new_password)
    return {"msg": "Password changed successfully"}


# --- Booking(Command) ---
@app.post("/bookings", status_code=201)
def create_booking(slot: str, user_id: str = Depends(get_current_user)):
    booking = handle_create_booking(user_id, slot)
    return booking


# --- Booking(Query) ---
@app.get("/bookings", response_model=BookingList)
def list_bookings(user_id: str = Depends(get_current_user)):
    return handle_list_bookings(user_id)
