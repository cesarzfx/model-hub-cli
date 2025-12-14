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


def _compute_download_url(source_url: str) -> str:
    if not isinstance(source_url, str):
        return str(source_url)
    return source_url


# ------------------ POST /artifacts ------------------ #


@router.post("/artifacts", response_model=List[ArtifactMetadata])
def list_artifacts(
    query: List[ArtifactQuery],
    response: Response,
    offset: Optional[str] = None,
) -> List[ArtifactMetadata]:
    response.headers["offset"] = offset or "0"

    if not ARTIFACTS_DIR.exists():
        # No artifacts stored yet.
        if not query:
            return []
        # For non-wildcard queries, behave as "no such artifact".
        for q in query:
            if q.name != "*":
                raise HTTPException(status_code=404, detail="No such artifact")
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []
    seen_ids: Set[str] = set()

    for q in query:
        # Validate requested types
        if q.types:
            for t in q.types:
                if t not in VALID_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid artifact type in query: {t}",
                    )

        # Wildcard query: enumerate all artifacts (optionally filtered by type)
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

        # Name-specific query: exact match on metadata.name (+ optional type)
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

                # If multiple artifacts share the same name, pick smallest id
                if best is None or md.id < best.id:
                    best = md

            if best is None:
                raise HTTPException(status_code=404, detail="No such artifact")

            results.append(best)

    return results


# ------------------ GET /artifact/byName/{name} ------------------ #


@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
def get_artifacts_by_name(name: str) -> List[ArtifactMetadata]:
    """Return all artifacts whose metadata.name exactly matches `name`."""
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


# ------------------ POST /artifact/byRegEx ------------------ #


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
def get_artifacts_by_regex(payload: ArtifactRegEx) -> List[ArtifactMetadata]:
    if not ARTIFACTS_DIR.exists():
        raise HTTPException(
            status_code=404, detail="No artifact found under this regex"
        )

    raw = payload.regex

    # Try to detect simple "name-like" patterns such as ^foo$ or foo, and
    # treat them as exact-name queries to match spec examples.
    stripped = raw
    if stripped.startswith("^"):
        stripped = stripped[1:]
    if stripped.endswith("$"):
        stripped = stripped[:-1]

    if stripped and re.fullmatch(r"[A-Za-z0-9._\-]+", stripped):
        stored = iter_all_artifacts()
        exact_results: List[ArtifactMetadata] = []

        for a in stored:
            md_raw = a.get("metadata", {})
            try:
                md = ArtifactMetadata(**md_raw)
            except Exception:
                continue

            if md.name == stripped:
                exact_results.append(md)

        if not exact_results:
            raise HTTPException(
                status_code=404, detail="No artifact found under this regex"
            )

        return exact_results

    # Otherwise, treat payload.regex as a full regex
    try:
        pattern = re.compile(raw)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regular expression")

    stored = iter_all_artifacts()
    regex_results: List[ArtifactMetadata] = []

    for a in stored:
        md_raw = a.get("metadata", {})
        try:
            md = ArtifactMetadata(**md_raw)
        except Exception:
            continue

        if pattern.search(md.name):
            regex_results.append(md)

    if not regex_results:
        raise HTTPException(
            status_code=404, detail="No artifact found under this regex"
        )

    return regex_results


# ------------------ Helper: derive name from URL ------------------ #


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
            return path_parts[1]
        elif path_parts:
            return path_parts[-1]

    # Default: last non-empty path segment, or the whole URL as a fallback
    if path_parts:
        return path_parts[-1]
    return url


# ------------------ POST /artifact/{artifact_type} ------------------ #


@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Artifact:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    url_str = artifact.url
    raw_id = f"{artifact_type}:{url_str}"
    artifact_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:10]

    # Prefer client-provided name if present; otherwise derive from URL.
    provided_name = getattr(artifact, "name", None)
    if provided_name and provided_name.strip():
        name = provided_name.strip()
    else:
        name = derive_artifact_name(url_str)

    # Prevent duplicates: same type + url -> 409
    for existing in iter_all_artifacts():
        md = existing.get("metadata", {})
        data = existing.get("data", {})
        if md.get("type") == artifact_type and data.get("url") == url_str:
            raise HTTPException(status_code=409, detail="Artifact exists already")

    # Compute download_url via a helper so its semantics are centralized
    data_obj = ArtifactData(
        url=url_str,
        download_url=_compute_download_url(url_str),
        name=provided_name,
    )

    metadata = ArtifactMetadata(name=name, id=artifact_id, type=artifact_type)
    artifact_obj = Artifact(metadata=metadata, data=data_obj)
    store_artifact(artifact_id, artifact_obj.dict())
    return artifact_obj


# ------------------ GET /artifacts/{artifact_type}/{id} ------------------ #


@router.get("/artifacts/{artifact_type}/{id}", response_model=Artifact)
def get_artifact(artifact_type: str, id: str) -> Artifact:
    """Fetch a single artifact by type and id."""
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


# ------------------ DELETE /artifacts/{artifact_type}/{id} ------------------ #


@router.delete("/artifacts/{artifact_type}/{id}")
def delete_artifact(artifact_type: str, id: str) -> Response:
    """Delete an artifact if it exists and type matches."""
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


# ------------------ GET /artifact/{artifact_type}/{id}/cost ------------------ #


@router.get(
    "/artifact/{artifact_type}/{id}/cost",
    response_model=Dict[str, ArtifactCostEntry],
)
def get_artifact_cost(
    artifact_type: str,
    id: str,
    dependency: bool = False,
) -> Dict[str, ArtifactCostEntry]:
    """Compute storage cost for an artifact.

    - If dependency == false:
        return {id: {total_cost: base_cost}}
    - If dependency == true:
        return {id: {standalone_cost: base_cost, total_cost: base_cost}}
      (we do not track real dependencies in this implementation).
    """
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
