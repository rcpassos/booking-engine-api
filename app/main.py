from fastapi import FastAPI, Depends, HTTPException, Body, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import EmailStr

# Rate limiter imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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


# Helper function to check if we're running in a test environment
def is_test_environment():
    import sys

    return "pytest" in sys.modules


# Initialize rate limiter with appropriate configuration
if is_test_environment():
    # In test environment, create a no-op rate limiter
    # This creates a limiter that doesn't actually limit anything
    class NoOpLimiter:
        def limit(self, *args, **kwargs):
            def inner(func):
                return func

            return inner

    limiter = NoOpLimiter()
else:
    # In production, use the real rate limiter
    limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Booking Engine",
    dependencies=[Depends(get_api_key)],
)

# Add rate limit handler (only needed in production)
if not is_test_environment():
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# -- Register --
@app.post("/auth/register", response_model=UserOut, status_code=201)
@limiter.limit("5/hour")  # Limit to 5 registrations per hour per IP
def register(request: Request, data: UserIn):
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
@limiter.limit("10/minute")  # Limit to 10 login attempts per minute per IP
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    user = users.find_one({"email": form.username})
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(subject=user["_id"])
    return {"access_token": token, "token_type": "bearer"}


# -- Recover password --
@app.post("/auth/recover-password")
@limiter.limit("3/hour")  # Limit to 3 recovery emails per hour per IP
def recover_password(request: Request, email: EmailStr = Body(..., embed=True)):
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
@limiter.limit("5/hour")  # Limit to 5 password resets per hour per IP
def reset_password(request: Request, token: str, new_password: str):
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
@limiter.limit("60/minute")  # Limit to 60 requests per minute per IP
def read_profile(request: Request, user_id: str = Depends(get_current_user)):
    u = users.find_one({"_id": user_id})
    return {
        "id": u["_id"],
        "email": u["email"],
        "full_name": u["full_name"],
        "created_at": u["created_at"],
    }


# -- Update profile --
@app.put("/users/me", response_model=UserOut)
@limiter.limit("30/hour")  # Limit to 30 profile updates per hour per IP
def update_profile(
    request: Request, data: UserUpdate, user_id: str = Depends(get_current_user)
):
    updated = update_user(user_id, data.model_dump())
    return {
        "id": updated["_id"],
        "email": updated["email"],
        "full_name": updated["full_name"],
        "created_at": updated["created_at"],
    }


# -- Change password (authenticated) --
@app.put("/users/me/password")
@limiter.limit("5/hour")  # Limit to 5 password changes per hour per IP
def change_password(
    request: Request, data: PasswordUpdate, user_id: str = Depends(get_current_user)
):
    user = users.find_one({"_id": user_id})
    if not verify_password(data.old_password, user["hashed_password"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Old password incorrect")
    update_password(user_id, data.new_password)
    return {"msg": "Password changed successfully"}


# --- Booking(Command) ---
@app.post("/bookings", status_code=201)
@limiter.limit("20/hour")  # Limit to 20 bookings per hour per IP
def create_booking(
    request: Request, slot: str, user_id: str = Depends(get_current_user)
):
    booking = handle_create_booking(user_id, slot)
    return booking


# --- Booking(Query) ---
@app.get("/bookings", response_model=BookingList)
@limiter.limit("60/minute")  # Limit to 60 requests per minute per IP
def list_bookings(request: Request, user_id: str = Depends(get_current_user)):
    return handle_list_bookings(user_id)
