from fastapi import APIRouter
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

router = APIRouter()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"


class AuthRequest(BaseModel):
    user: str
    secret: str


@router.put("/authenticate")
def authenticate(auth: AuthRequest) -> dict:
    # Dummy authentication: accept any user/secret
    to_encode = {"sub": auth.user}
    expires = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expires})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token}
