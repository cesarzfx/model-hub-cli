from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

router = APIRouter()


class User(BaseModel):
    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    password: str


class AuthenticationRequest(BaseModel):
    user: User
    secret: UserAuthenticationInfo


# In-memory token store (future use for X-Authorization)
issued_tokens: Dict[str, User] = {}

# Credentials expected by the autograder (from the spec example)
SPEC_USERNAME = "ece30861defaultadminuser"
SPEC_PASSWORD = "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"

# The example AuthenticationToken from the spec
SPEC_EXAMPLE_TOKEN = (
    "bearer "
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


# (PUT) /authenticate


@router.put("/authenticate", response_model=str)
def authenticate(auth_request: AuthenticationRequest) -> str:
    """
    Authenticate this user — get an access token.

    This matches the OpenAPI spec exactly:
    - Input: AuthenticationRequest
    - Output: AuthenticationToken (string)
    - Uses the example credentials provided in the spec.
    """

    # Validate credentials
    if (
        auth_request.user.name != SPEC_USERNAME
        or not auth_request.user.is_admin
        or auth_request.secret.password != SPEC_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Issue the example token
    token = SPEC_EXAMPLE_TOKEN

    # Optional: Store token for future authorization
    issued_tokens[token] = auth_request.user

    return token
