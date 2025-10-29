# service/app/api/v1/ingest.py
from fastapi import APIRouter, Depends, HTTPException
from ... import deps  # ✅ correct location for require_contributor
from ...domain import schemas, metrics, repos, storage

router = APIRouter()

@router.post("", response_model=schemas.IngestResult)
def ingest_hf(
    req: schemas.IngestRequest,
    user=Depends(deps.require_contributor),  # ✅ use deps
    repo: repos.PackageRepo = Depends(deps.get_repo),
    blobs: storage.BlobStore = Depends(deps.get_blob_store),
):
    # 1) fetch HF card/files (stub here)
    pkg = repo.create_from_hf(req.hf_id)
    # 2) score with adapter
    scores = metrics.rate_model(pkg)
    # 3) gate on non-latency metrics
    for k, v in scores.dict(exclude_none=True).items():
        if k != "latency" and v < 0.5:
            raise HTTPException(status_code=400, detail=f"Rejected: {k}={v:.2f} < 0.5")
    # 4) store blobs + metadata (stub for now)
    repo.update_scores(pkg.id, scores.dict(exclude_none=True))
    return schemas.IngestResult(id=pkg.id, name=pkg.name, version=pkg.version, scores=scores)
