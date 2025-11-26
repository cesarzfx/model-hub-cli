from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

router = APIRouter()

# ---------------- Schemas ---------------- #


class User(BaseModel):
    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    password: str


class AuthenticationRequest(BaseModel):
    user: User
    secret: UserAuthenticationInfo


# ------------- Token / credential config ------------- #

issued_tokens: Dict[str, User] = {}

SPEC_USERNAME = "ece30861defaultadminuser"
SPEC_PASSWORD = "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
SPEC_EXAMPLE_TOKEN = (
    "bearer "
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


# ---------------- Route ---------------- #


@router.put("/authenticate", response_model=str)
def authenticate(auth_request: AuthenticationRequest) -> str:
    """
    Authenticate this user -- get an access token.

    - 200: returns AuthenticationToken (string) on valid creds
    - 401: invalid username or password
    """

    if (
        auth_request.user.name != SPEC_USERNAME
        or not auth_request.user.is_admin
        or auth_request.secret.password != SPEC_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = SPEC_EXAMPLE_TOKEN
    issued_tokens[token] = auth_request.user
    return token
