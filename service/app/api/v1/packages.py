# service/app/api/v1/packages.py
import os, uuid, subprocess
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from ...domain import repos, schemas, storage
from ...core.search import safe_regex
from ...core.versioning import match_exact, match_range, match_tilde, match_caret
from ...core.config import get_settings
from ... import deps

router = APIRouter()

@router.post("", response_model=schemas.PackageDetail)
def create_package(body: schemas.PackageCreate,
                   repo: repos.PackageRepo = Depends(deps.get_repo),
                   user=Depends(deps.require_contributor)):
    pid = str(uuid.uuid4())
    from ...domain.models import ModelPackage
    pkg = ModelPackage(
        id=pid, name=body.name, version=body.version,
        card_text=body.card_text, meta=body.meta or {},
        parents=body.parents, sensitive=body.sensitive,
        pre_download_hook=body.pre_download_hook
    )
    repo.create(pkg)
    return schemas.PackageDetail(
        id=pkg.id, name=pkg.name, version=pkg.version,
        card_text=pkg.card_text, meta=pkg.meta, parents=pkg.parents,
        size_bytes=pkg.size_bytes, scores=schemas.Scores(**pkg.scores)
    )

@router.get("/{id}", response_model=schemas.PackageDetail)
def get_package(id: str, repo: repos.PackageRepo = Depends(deps.get_repo),
                user=Depends(deps.require_viewer)):
    p = repo.get(id)
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    return schemas.PackageDetail(
        id=p.id, name=p.name, version=p.version, card_text=p.card_text,
        meta=p.meta, parents=p.parents, size_bytes=p.size_bytes,
        scores=schemas.Scores(**p.scores)
    )

@router.delete("/{id}")
def delete_package(id: str, repo: repos.PackageRepo = Depends(deps.get_repo),
                   user=Depends(deps.require_admin)):
    if not repo.get(id):
        raise HTTPException(status_code=404, detail="Not found")
    # simple delete for Delivery #1
    repo._DB.pop(id, None)  # noqa: internal
    return {"ok": True}

@router.post("/{id}/upload")
def upload_artifacts(id: str,
                     full: UploadFile | None = File(default=None),
                     weights: UploadFile | None = File(default=None),
                     datasets: UploadFile | None = File(default=None),
                     repo: repos.PackageRepo = Depends(deps.get_repo),
                     blobs: storage.BlobStore = Depends(deps.get_blob_store),
                     user=Depends(deps.require_contributor)):
    p = repo.get(id)
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    def save(part: UploadFile | None, label: str) -> str | None:
        if not part: return None
        key = f"{id}/{label}/{part.filename}"
        tmp = f"/tmp/{part.filename}"
        with open(tmp, "wb") as f: f.write(part.file.read())
        blobs.put(key, tmp)
        os.remove(tmp)
        return key
    k_full = save(full, "full")
    k_w = save(weights, "weights")
    k_d = save(datasets, "datasets")
    size = 0
    for k in (k_full, k_w, k_d):
        if k:
            path = blobs.get_path(k)
            size += os.path.getsize(path)
    repo.upsert_blobs(id, k_full, k_w, k_d, size)
    return {"ok": True, "size_bytes": size, "keys": {"full": k_full, "weights": k_w, "datasets": k_d}}

@router.get("", response_model=schemas.PackagePage)
def list_packages(
    q: str | None = Query(None, description="regex over name/card"),
    version: str | None = Query(None, description='exact "1.2.3", "1.2.3-2.1.0", "~1.2.0", "^1.2.0"'),
    page: int = 1, limit: int = 50,
    repo: repos.PackageRepo = Depends(deps.get_repo),
    user=Depends(deps.require_viewer),
):
    predicate = None
    if version:
        if "-" in version:
            lo, hi = version.split("-", 1)
            predicate = match_range(lo, hi)
        elif version.startswith("~"):
            predicate = match_tilde(version)
        elif version.startswith("^"):
            predicate = match_caret(version)
        else:
            predicate = match_exact(version)
    regex = safe_regex(q) if q else None
    s = get_settings()
    limit = min(limit, s.MAX_PAGE_SIZE)
    return repo.search(regex=regex, version_pred=predicate, page=page, limit=limit)

@router.get("/{id}/download")
def download(id: str, part: str = Query("full", pattern="^(full|weights|datasets)$"),
             repo: repos.PackageRepo = Depends(deps.get_repo),
             blobs: storage.BlobStore = Depends(deps.get_blob_store),
             user=Depends(deps.require_viewer)):
    p = repo.get(id)
    if not p: raise HTTPException(status_code=404, detail="Not found")
    key = p.blob_key_full if part=="full" else (p.blob_key_weights if part=="weights" else p.blob_key_datasets)
    if not key: raise HTTPException(status_code=404, detail=f"{part} not available")
    # sensitive pre-download hook
    if p.sensitive and p.pre_download_hook:
        s = get_settings()
        path = blobs.get_path(key)
        cmd = [s.NODE_PATH, p.pre_download_hook, p.name, user["sub"], user["sub"], path]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                raise HTTPException(status_code=403, detail=f"Blocked by pre-download hook: {res.stdout.strip()}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hook failed: {e}")
    return FileResponse(blobs.get_path(key), filename=os.path.basename(key))
