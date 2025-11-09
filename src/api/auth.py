from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt
import os
from datetime import datetime, timedelta

router = APIRouter()

# Secret key for JWT token signing - in production, use a secure environment variable
SECRET_KEY = "your-secret-key-here"  # TODO: Move to environment variable
ALGORITHM = "HS256"


class User(BaseModel):
    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    password: str


class AuthenticationRequest(BaseModel):
    user: User
    secret: UserAuthenticationInfo


def create_jwt_token(user: User) -> str:
    """Create a JWT token for the authenticated user."""
    token_data = {
        "sub": user.name,
        "is_admin": user.is_admin,
        "exp": datetime.utcnow() + timedelta(days=1),  # Token expires in 1 day
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)


@router.put("/authenticate")
async def authenticate(auth_request: AuthenticationRequest) -> str:
    """
    Authenticate a user and return a JWT token.
    The token should be provided to other endpoints via the "X-Authorization" header.
    """
    # Check if the credentials match the default admin user
    if (
        auth_request.user.name == "ece30861defaultadminuser"
        and auth_request.secret.password
        == "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
    ):

        # Create JWT token
        token = create_jwt_token(auth_request.user)

        # Return the token with "bearer " prefix
        return f"bearer {token}"

    # If credentials don't match, return 401 Unauthorized
    raise HTTPException(status_code=401, detail="The user or password is invalid.")
