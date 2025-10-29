# service/app/api/v1/rate.py
from fastapi import APIRouter, Depends, HTTPException
from ...domain import repos, metrics, schemas
from ... import deps

router = APIRouter()

@router.post("/{id}", response_model=schemas.Scores)
def rate(id: str, repo: repos.PackageRepo = Depends(deps.get_repo),
         user=Depends(deps.require_contributor)):
    pkg = repo.get(id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    sc = metrics.rate_model(pkg)
    repo.update_scores(id, sc.dict(exclude_none=True))
    return sc
