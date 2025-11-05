from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()

SECRET_KEY = "ece461_phase2_secret_key"  # In production this would be an environment variable
ALGORITHM = "HS256"

api_key_header = APIKeyHeader(name="X-Authorization", auto_error=False)

class User(BaseModel):
    name: str
    is_admin: bool = False

class UserSecret(BaseModel):
    password: str

class AuthRequest(BaseModel):
    user: User
    secret: UserSecret

def create_access_token(user: User) -> str:
    to_encode = user.dict()
    expires = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expires.timestamp()})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return f"bearer {token}"

def verify_token(token: Optional[str] = Security(api_key_header)) -> User:
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    try:
        if token.startswith("bearer "):
            token = token[7:]  # Remove "bearer " prefix
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = User(**{k:v for k,v in payload.items() if k != "exp"})
        
        if payload.get("exp") and float(payload["exp"]) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=403, detail="Token expired")
            
        return user
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

@router.put("/authenticate")
def authenticate(auth: AuthRequest) -> dict:
    # For demo purposes - in production we would validate against a database
    if auth.user.name == "ece30861defaultadminuser" and \
       auth.secret.password == "correcthorsebatterystaple123(!__+@**(A'\"`:":
        token = create_access_token(auth.user)
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid username or password")
