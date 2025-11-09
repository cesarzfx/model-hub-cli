from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class User(BaseModel):
    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    password: str


class AuthenticationRequest(BaseModel):
    user: User
    secret: UserAuthenticationInfo


@router.put("/authenticate")
async def authenticate(auth_request: AuthenticationRequest):
    """
    This system does not support authentication (NON-BASELINE).
    """
    # The authentication logic is commented out for NON-BASELINE mode.
    # If you pursue the Access Control Track, uncomment and implement the logic below.
    # return actual token if supporting authentication.
    raise HTTPException(
        status_code=501, detail="This system does not support authentication."
    )
