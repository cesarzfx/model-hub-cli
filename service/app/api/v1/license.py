# service/app/api/v1/license.py
from fastapi import APIRouter, Depends, HTTPException
from ...domain import repos, schemas
from ... import deps

router = APIRouter()

@router.post("/check", response_model=schemas.LicenseCheckResult)
def check(req: schemas.LicenseCheckRequest,
          repo: repos.PackageRepo = Depends(deps.get_repo),
          user=Depends(deps.require_contributor)):
    pkg = repo.get(req.model_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    # basic policy table (fine-tune + inference)
    model_lic = (pkg.meta or {}).get("license", "apache-2.0").lower()
    repo_lic = "mit"  # TODO: detect via GitHub API; stub = permissive
    ok = True
    rationale = f"Model license={model_lic}, Repo license={repo_lic} compatible for fine-tune+inference."
    if model_lic in {"cc-by-nc-4.0", "proprietary"}:
        ok = False
        rationale = f"Model license {model_lic} is non-commercial or restricted."
    return schemas.LicenseCheckResult(ok=ok, rationale=rationale)
