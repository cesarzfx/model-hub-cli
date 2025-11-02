from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ModelRating(BaseModel):
    name: str
    bus_factor_score: float
    correctness_score: float
    ramp_up_score: float
    responsive_maintainer_score: float
    license_score: float
    good_pinning_practice_score: float
    pull_request_score: float
    net_score: float


@router.get("/artifact/model/{id}/rate")
def rate_model(id: str) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/artifact/model/{id}/lineage")
def get_lineage(id: str) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/artifact/model/{id}/license-check")
def license_check(id: str) -> None:
    raise HTTPException(status_code=501, detail="Not implemented")
