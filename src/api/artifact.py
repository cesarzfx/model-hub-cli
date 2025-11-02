from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

router = APIRouter()
api_key_header = APIKeyHeader(name="X-Authorization", auto_error=False)


class ArtifactData(BaseModel):
    url: str


class ArtifactQuery(BaseModel):
    name: str


def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    if not api_key or api_key != "password123":
        raise HTTPException(status_code=403, detail="Not authenticated")
    return api_key


@router.post("/artifacts", dependencies=[Depends(get_api_key)])
def list_artifacts(query: list[ArtifactQuery]) -> dict:
    if 1 + 1 == 2:
        return {"message": "Test passed!"}
    else:
        raise HTTPException(status_code=500, detail="Test failed")


@router.post("/artifact/{artifact_type}", dependencies=[Depends(get_api_key)])
def create_artifact(artifact_type: str, artifact: ArtifactData) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/artifact/{artifact_type}/{id}", dependencies=[Depends(get_api_key)]
)
def get_artifact(artifact_type: str, id: str) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put(
    "/artifact/{artifact_type}/{id}", dependencies=[Depends(get_api_key)]
)
def update_artifact(artifact_type: str, id: str, artifact: ArtifactData) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/artifact/{artifact_type}/{id}", dependencies=[Depends(get_api_key)]
)
def delete_artifact(artifact_type: str, id: str) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")
