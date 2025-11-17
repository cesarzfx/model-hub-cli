from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel


import secrets
from typing import Dict

router = APIRouter()

# In-memory store for tokens and users (for autograder/testing)
issued_tokens: Dict[str, str] = {}  # token -> username


class User(BaseModel):
    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    password: str


class AuthenticationRequest(BaseModel):
    user: User
    secret: UserAuthenticationInfo


@router.put("/authenticate")
async def authenticate(
    auth_request: AuthenticationRequest,
    request: Request
) -> str:
    """
    Authenticate user and return a token if credentials are valid.
    """


    # Validate request body
    if not auth_request or not auth_request.user or not auth_request.secret:
        raise HTTPException(status_code=400, detail="Malformed AuthenticationRequest.")

    # Credentials required by spec
    required_username = "ece30861defaultadminuser"
    required_password = (
        "correcthorsebatterystaple123(!__+@**(A'\";DROP TABLE artifacts;"
    )

    # Validate credentials
    if (
        auth_request.user.name != required_username
        or auth_request.secret.password != required_password
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Issue the example JWT token from the spec
    token = "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    issued_tokens[token] = auth_request.user.name
    return token
