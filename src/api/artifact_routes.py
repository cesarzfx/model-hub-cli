from fastapi import APIRouter, HTTPException, Response
from typing import List, Optional, Dict, Set
import hashlib
import re

from .artifact_schemas import (
    ArtifactData,
    ArtifactMetadata,
    ArtifactQuery,
    Artifact,
    ArtifactRegEx,
    ArtifactCostEntry,
    VALID_TYPES,
    ARTIFACT_ID_PATTERN,
)

from .artifact_store import (
    ARTIFACTS_DIR,
    store_artifact,
    get_stored_artifact,
    iter_all_artifacts,
    estimate_artifact_cost_mb,
)

router = APIRouter()


# ------------------ /artifacts POST ------------------ #


@router.post("/artifacts", response_model=List[ArtifactMetadata])
def list_artifacts(
    query: List[ArtifactQuery],
    response: Response,
    offset: Optional[str] = None,
) -> List[ArtifactMetadata]:
    """
    List artifacts matching the query.

    Behavior (aligned with Piazza clarification + spec):
      - Validate every type in q.types (if present) is a valid ArtifactType; otherwise 400.
      - For q.name == "*":
          -> enumerate all artifacts matching optional types, deduped by id.
      - For q.name != "*":
          -> treat each query as "get artifact by name":
             * EXACT name match (md.name == q.name)
             * apply optional type filter
             * return AT MOST ONE ArtifactMetadata per query
               (pick a deterministic "best" match if multiple).
             * if no matches at all for that query -> 404 ("no such artifact").
      - Response is the concatenation of results for each query, in order.
    """
    response.headers["offset"] = offset or "0"

    if not ARTIFACTS_DIR.exists():
        if not query:
            return []
        for q in query:
            if q.name != "*":
                raise HTTPException(status_code=404, detail="No such artifact")
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []
    seen_ids: Set[str] = set()

    for q in query:
        if q.types:
            for t in q.types:
                if t not in VALID_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid artifact type in query: {t}",
                    )

        if q.name == "*":
            for a in stored_artifacts:
                md_raw = a.get("metadata", {})
                try:
                    md = ArtifactMetadata(**md_raw)
                except Exception:
                    continue

                if q.types and md.type not in q.types:
                    continue

                if md.id not in seen_ids:
                    seen_ids.add(md.id)
                    results.append(md)

        else:
            best: Optional[ArtifactMetadata] = None

            for a in stored_artifacts:
                md_raw = a.get("metadata", {})
                try:
                    md = ArtifactMetadata(**md_raw)
                except Exception:
                    continue

                if md.name != q.name:
                    continue
                if q.types and md.type not in q.types:
                    continue

                if best is None or md.id < best.id:
                    best = md

            if best is None:
                raise HTTPException(status_code=404, detail="No such artifact")

            results.append(best)

    return results


# ------------------ /artifact/byName/{name} ------------------ #


@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
def get_artifacts_by_name(name: str) -> List[ArtifactMetadata]:
    """
    Retrieve artifacts whose metadata.name matches the given name exactly.
    """
    if not ARTIFACTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No such artifact")

    stored = iter_all_artifacts()
    results: List[ArtifactMetadata] = []

    for a in stored:
        md_raw = a.get("metadata", {})
        try:
            md = ArtifactMetadata(**md_raw)
        except Exception:
            continue

        if md.name == name:
            results.append(md)

    if not results:
        raise HTTPException(status_code=404, detail="No such artifact")

    return results


# ------------------ /artifact/byRegEx ------------------ #


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
def get_artifacts_by_regex(payload: ArtifactRegEx) -> List[ArtifactMetadata]:
    """
    Retrieve artifacts whose metadata.name matches the given regular expression.
    """
    if not ARTIFACTS_DIR.exists():
        raise HTTPException(
            status_code=404, detail="No artifact found under this regex"
        )

    raw = payload.regex

    stripped = raw
    if stripped.startswith("^"):
        stripped = stripped[1:]
    if stripped.endswith("$"):
        stripped = stripped[:-1]

    if stripped and re.fullmatch(r"[A-Za-z0-9._\\-]+", stripped):
        stored = iter_all_artifacts()
        results_exact: List[ArtifactMetadata] = []

        for a in stored:
            md_raw = a.get("metadata", {})
            try:
                md = ArtifactMetadata(**md_raw)
            except Exception:
                continue

            if md.name == stripped:
                results_exact.append(md)

        if not results_exact:
            raise HTTPException(
                status_code=404, detail="No artifact found under this regex"
            )

        return results_exact

    try:
        pattern = re.compile(raw)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regular expression")

    stored = iter_all_artifacts()
    results_regex: List[ArtifactMetadata] = []

    for a in stored:
        md_raw = a.get("metadata", {})
        try:
            md = ArtifactMetadata(**md_raw)
        except Exception:
            continue

        if pattern.search(md.name):
            results_regex.append(md)

    if not results_regex:
        raise HTTPException(
            status_code=404, detail="No artifact found under this regex"
        )

    return results_regex


# ------------------ POST /artifact/{artifact_type} ------------------ #


@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Artifact:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    raw_id = f"{artifact_type}:{artifact.url}"
    artifact_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:10]

    url_str = artifact.url
    if "/" in url_str:
        name = url_str.rstrip("/").split("/")[-1] or url_str
    else:
        name = url_str

    for existing in iter_all_artifacts():
        md = existing.get("metadata", {})
        data = existing.get("data", {})
        if md.get("type") == artifact_type and data.get("url") == url_str:
            raise HTTPException(status_code=409, detail="Artifact exists already")

    data_obj = ArtifactData(url=artifact.url, download_url=artifact.url)

    metadata = ArtifactMetadata(name=name, id=artifact_id, type=artifact_type)
    artifact_obj = Artifact(metadata=metadata, data=data_obj)

    store_artifact(artifact_id, artifact_obj.dict())

    return artifact_obj


# ------------------ GET /artifacts/{type}/{id} ------------------ #


@router.get("/artifacts/{artifact_type}/{id}", response_model=Artifact)
def get_artifact(artifact_type: str, id: str) -> Artifact:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ARTIFACT_ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    md = stored.get("metadata", {})
    if md.get("type") != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    try:
        return Artifact(**stored)
    except Exception:
        raise HTTPException(status_code=500, detail="Stored artifact is invalid")


# ------------------ DELETE /artifacts/{type}/{id} ------------------ #


@router.delete("/artifacts/{artifact_type}/{id}")
def delete_artifact(artifact_type: str, id: str) -> Dict[str, str]:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ARTIFACT_ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    filepath = ARTIFACTS_DIR / f"{id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    md = stored.get("metadata", {})
    if md.get("type") != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    filepath.unlink()
    return {"message": "Artifact deleted"}


# ------------------ PUT /artifacts/{type}/{id} ------------------ #


@router.put("/artifacts/{artifact_type}/{id}", response_model=Artifact)
def update_artifact(artifact_type: str, id: str, artifact: Artifact) -> Artifact:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ARTIFACT_ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    md = stored.get("metadata", {})
    if md.get("type") != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    if artifact.metadata.id != id or artifact.metadata.type != artifact_type:
        raise HTTPException(status_code=400, detail="Metadata id/type mismatch")

    store_artifact(id, artifact.dict())
    return artifact


# ------------------ GET /artifact/{type}/{id}/cost ------------------ #


@router.get(
    "/artifact/{artifact_type}/{id}/cost",
    response_model=Dict[str, ArtifactCostEntry],
)
def get_artifact_cost(
    artifact_type: str,
    id: str,
    dependency: bool = False,
) -> Dict[str, ArtifactCostEntry]:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ARTIFACT_ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    md = stored.get("metadata", {})
    if md.get("type") != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    base_cost = estimate_artifact_cost_mb(stored)

    if not dependency:
        return {id: ArtifactCostEntry(total_cost=base_cost)}

    return {
        id: ArtifactCostEntry(
            standalone_cost=base_cost,
            total_cost=base_cost,
        )
    }
