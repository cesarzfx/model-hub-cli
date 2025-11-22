from fastapi import APIRouter, HTTPException, Response
from typing import List, Optional, Dict, Set
import hashlib
import re
from urllib.parse import urlparse

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


# ------------------ /artifacts POST (query) ------------------ #


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
              - exact name match (metadata.name == q.name)
              - optional type filter
              - if no match for any query, return 404
    """
    # Validation: ensure all types in all queries are valid
    for q in query:
        if q.types:
            for t in q.types:
                if t not in VALID_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid artifact type in query: {t}",
                    )

    # If there are no artifacts at all, short-circuit behavior:
    if not ARTIFACTS_DIR.exists():
        # If any query is not wildcard, treat as "no such artifact"
        if query:
            for q in query:
                if q.name != "*":
                    raise HTTPException(status_code=404, detail="No such artifact")
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []
    seen_ids: Set[str] = set()

    for q in query:
        if q.name == "*":
            # Wildcard: collect all artifacts filtered by type
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
            # Name-specific query: exact match
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

                # If multiple artifacts share the same name, pick the one with
                # lexicographically smallest id (deterministic but arbitrary).
                if best is None or md.id < best.id:
                    best = md

            if best is None:
                # According to Piazza clarification: if any name-query fails, 404
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


# ------------------ /artifact/readRegEx POST ------------------ #


@router.post("/artifact/readRegEx", response_model=List[ArtifactMetadata])
def get_artifacts_by_regex(regex: ArtifactRegEx) -> List[ArtifactMetadata]:
    """
    Returns all ArtifactMetadata whose name matches the given regular expression.

    If regex is invalid, return 400.
    If no artifacts match, return 404.
    """
    pattern = regex.regex
    try:
        compiled = re.compile(pattern)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regular expression")

    if not ARTIFACTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No artifact found")

    stored = iter_all_artifacts()
    results: List[ArtifactMetadata] = []

    for a in stored:
        md_raw = a.get("metadata", {})
        try:
            md = ArtifactMetadata(**md_raw)
        except Exception:
            continue

        if compiled.search(md.name):
            results.append(md)

    if not results:
        raise HTTPException(status_code=404, detail="No artifact found")

    return results


# ------------------ /artifact/{artifact_type} POST (ingest) ------------------ #


def derive_artifact_name(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc
    path_parts = [p for p in parsed.path.split("/") if p]

    # GitHub: https://github.com/{owner}/{repo}[...]
    if host.endswith("github.com") and len(path_parts) >= 2:
        owner, repo = path_parts[0], path_parts[1]
        return f"{owner}-{repo}"

    # Hugging Face: https://huggingface.co/{org}/{model}[...]
    if host.endswith("huggingface.co"):
        if len(path_parts) >= 2:
            # Typically /org/model/...; we want the model name
            return path_parts[1]
        elif path_parts:
            return path_parts[-1]

    # Default: last non-empty path segment, or the whole URL as a fallback
    if path_parts:
        return path_parts[-1]
    return url


@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Artifact:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    url_str = artifact.url

    # Deterministic id based on type + url
    raw_id = f"{artifact_type}:{url_str}"
    artifact_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:10]

    # Derive a canonical name from the source URL
    name = derive_artifact_name(url_str)

    # Prevent duplicate artifacts with same type + url
    for existing in iter_all_artifacts():
        md = existing.get("metadata", {})
        data = existing.get("data", {})
        if md.get("type") == artifact_type and data.get("url") == url_str:
            raise HTTPException(status_code=409, detail="Artifact exists already")

    # Data section: url and an internal download_url (for now equal to source url)
    data_obj = ArtifactData(url=url_str, download_url=url_str)

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
        # Type mismatch for this id
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    try:
        return Artifact(**stored)
    except Exception:
        raise HTTPException(status_code=500, detail="Stored artifact is invalid")


# ------------------ DELETE /artifacts/{type}/{id} ------------------ #


@router.delete("/artifacts/{artifact_type}/{id}")
def delete_artifact(artifact_type: str, id: str) -> Response:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ARTIFACT_ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    filepath = ARTIFACTS_DIR / f"{id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    stored = get_stored_artifact(id)
    if stored:
        md = stored.get("metadata", {})
        if md.get("type") != artifact_type:
            raise HTTPException(status_code=400, detail="Artifact type mismatch")

    filepath.unlink()
    return Response(status_code=200)


# ------------------ /artifact/{artifact_type}/{id}/cost ------------------ #


@router.get(
    "/artifact/{artifact_type}/{id}/cost", response_model=Dict[str, ArtifactCostEntry]
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
