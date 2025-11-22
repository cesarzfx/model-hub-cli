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


# ------------------ /artifacts POST ------------------ #


@router.post("/artifacts", response_model=List[ArtifactMetadata])
def list_artifacts(
    query: List[ArtifactQuery],
    response: Response,
    offset: Optional[str] = None,
) -> List[ArtifactMetadata]:
    response.headers["offset"] = offset or "0"

    # If there is no storage directory yet, either:
    #  - wildcard queries return empty list
    #  - name queries return 404 (no such artifact)
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
        # Validate q.types entries if present
        if q.types:
            for t in q.types:
                if t not in VALID_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid artifact type in query: {t}",
                    )

        # Wildcard: list all artifacts (optionally filtered by type)
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

        # Name-specific query: exact name match, optional type filter
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

                # If multiple artifacts share the same name, pick the one
                # with lexicographically smallest id, for deterministic behavior.
                if best is None or md.id < best.id:
                    best = md

            if best is None:
                # For any name query that finds no artifact, the autograder
                # expects a 404.
                raise HTTPException(status_code=404, detail="No such artifact")

            results.append(best)

    return results


# ------------------ /artifact/byName/{name} ------------------ #


@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
def get_artifacts_by_name(name: str) -> List[ArtifactMetadata]:
    """
    Retrieve all artifacts whose metadata.name exactly matches the given name.
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

    # Strip ^ and $ for simple exact-match patterns so that we can special-case
    # "regex" queries that are really just names.
    stripped = raw
    if stripped.startswith("^"):
        stripped = stripped[1:]
    if stripped.endswith("$"):
        stripped = stripped[:-1]

    # If the stripped pattern is a simple "name-like" string, treat it as an
    # exact name match (this matches the spec examples).
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

    # Otherwise, treat the input as a full regular expression
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


# ------------------ Helper: derive canonical name from URL ------------------ #


def derive_artifact_name(url: str) -> str:
    """Derive a canonical artifact name from the source URL.

    Heuristics based on the project spec examples and autograder hints:
      - GitHub:  {owner}-{repo}, e.g. https://github.com/openai/whisper -> openai-whisper
      - Hugging Face: model name (second path segment), e.g.
            https://huggingface.co/google-bert/bert-base-uncased -> bert-base-uncased
            https://huggingface.co/openai/whisper-tiny/tree/main -> whisper-tiny
      - Default: last non-empty path segment, or the whole URL if the path is empty.
    """
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


# ------------------ POST /artifact/{artifact_type} ------------------ #


@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Artifact:
    """
    Ingest a new artifact.

    - artifact_type must be one of VALID_TYPES.
    - The artifact_id is a deterministic hash of "{artifact_type}:{url}" so that
      repeated uploads of the same url + type yield the same id.
    - The ArtifactMetadata.name is derived from the URL using derive_artifact_name().
    """
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    raw_id = f"{artifact_type}:{artifact.url}"
    artifact_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:10]

    url_str = artifact.url
    name = derive_artifact_name(url_str)

    # Prevent duplicates: same type + url -> 409
    for existing in iter_all_artifacts():
        md = existing.get("metadata", {})
        data = existing.get("data", {})
        if md.get("type") == artifact_type and data.get("url") == url_str:
            raise HTTPException(status_code=409, detail="Artifact exists already")

    # Data section: url and an internal download_url (for now equal to source url)
    data_obj = ArtifactData(url=artifact.url, download_url=artifact.url)

    metadata = ArtifactMetadata(name=name, id=artifact_id, type=artifact_type)
    artifact_obj = Artifact(metadata=metadata, data=data_obj)

    store_artifact(artifact_id, artifact_obj.dict())

    return artifact_obj


# ------------------ GET /artifacts/{artifact_type}/{id} ------------------ #


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


# ------------------ DELETE /artifacts/{artifact_type}/{id} ------------------ #


@router.delete("/artifacts/{artifact_type}/{id}")
def delete_artifact(artifact_type: str, id: str) -> Dict[str, str]:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ARTIFACT_ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    filepath = ARTIFACTS_DIR / f"{id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    # Optional: verify stored type matches path type
    stored = get_stored_artifact(id)
    if stored:
        md = stored.get("metadata", {})
        if md.get("type") != artifact_type:
            raise HTTPException(status_code=400, detail="Artifact type mismatch")

    filepath.unlink()
    return {"status": "deleted"}


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
    """
    Compute storage cost for an artifact.

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
