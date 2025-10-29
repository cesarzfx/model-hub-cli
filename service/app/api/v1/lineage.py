# service/app/api/v1/lineage.py
from fastapi import APIRouter, Depends, HTTPException
from ...domain import repos
from ... import deps

router = APIRouter()

@router.get("/{id}")
def lineage(id: str, repo: repos.PackageRepo = Depends(deps.get_repo),
            user=Depends(deps.require_viewer)):
    pkg = repo.get(id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    def summarize(pid: str):
        p = repo.get(pid)
        if not p: return None
        return {"id": p.id, "name": p.name, "version": p.version, "score": sum((p.scores or {}).values())/max(len(p.scores or {}),1)}
    parents = [summarize(pid) for pid in pkg.parents if summarize(pid)]
    return {"id": pkg.id, "name": pkg.name, "version": pkg.version, "parents": parents}
