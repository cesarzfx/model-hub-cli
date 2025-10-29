# service/app/domain/repos.py
import os, uuid
from typing import List, Callable, Pattern, Dict, Optional
from .models import ModelPackage
from ..core.config import get_settings

# NOTE: simple in-memory + JSON persistence for Delivery #1; swap to SQLModel later
_DB: Dict[str, ModelPackage] = {}
_USERS: Dict[str, Dict] = {
    # default admin will be recreated by /admin/reset
}

def get_repo():
    return PackageRepo()

class PackageRepo:
    def create(self, pkg: ModelPackage) -> ModelPackage:
        _DB[pkg.id] = pkg
        return pkg

    def create_from_hf(self, hf_id: str) -> ModelPackage:
        # stub: hydrate minimal fields from hf_id
        pid = str(uuid.uuid4())
        pkg = ModelPackage(
            id=pid, name=hf_id.split("/")[-1], version="1.0.0",
            card_text=f"Imported from {hf_id}", meta={"source":"hf"},
            parents=[], sensitive=False, pre_download_hook=None
        )
        _DB[pid] = pkg
        return pkg

    def get(self, pid: str) -> Optional[ModelPackage]:
        return _DB.get(pid)

    def update_scores(self, pid: str, scores: Dict[str, float]):
        pkg = _DB[pid]; pkg.scores.update(scores)

    def upsert_blobs(self, pid: str, full: str|None, weights: str|None, datasets: str|None, size: int):
        pkg = _DB[pid]
        if full: pkg.blob_key_full = full
        if weights: pkg.blob_key_weights = weights
        if datasets: pkg.blob_key_datasets = datasets
        pkg.size_bytes = size

    def search(self, regex: Pattern|None, version_pred: Callable[[str], bool]|None,
               page: int, limit: int):
        items = list(_DB.values())
        if regex:
            items = [p for p in items if regex.search(p.name) or (p.card_text and regex.search(p.card_text))]
        if version_pred:
            items = [p for p in items if version_pred(p.version)]
        total = len(items)
        start = max((page-1)*limit, 0); end = start + limit
        page_items = items[start:end]
        from .schemas import PackagePage, PackageSummary, Scores
        return PackagePage(
            page=page, limit=limit, total=total,
            items=[PackageSummary(
                id=p.id, name=p.name, version=p.version, size_bytes=p.size_bytes,
                scores=Scores(**p.scores)
            ) for p in page_items]
        )
    
    def user_count(self) -> int:
        return len(_USERS)


    # simple user store for login (admin-only can add users later)
    def upsert_user(self, username: str, hashed: str, role: str):
        _USERS[username] = {"hashed": hashed, "role": role, "rev": 0}

    def get_user(self, username: str):
        return _USERS.get(username)

    def reset(self):
        _DB.clear()
        _USERS.clear()
