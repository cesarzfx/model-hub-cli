from fastapi import APIRouter, HTTPException, Response, Header
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import json
import hashlib
import re

router = APIRouter()

# Use /tmp on Lambda; can override with ARTIFACTS_DIR env var for local dev
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))

# Import issued_tokens for authentication
try:
    from .auth import issued_tokens
except ImportError:
    issued_tokens = {}


# ---------- Models ----------


class ArtifactData(BaseModel):
    """
    ArtifactData as per spec:
      - url: required, uri string (we store as plain str for JSON safety)
      - download_url: optional, set in responses
    """

    url: str
    download_url: Optional[str] = None


class ArtifactMetadata(BaseModel):
    """
    ArtifactMetadata as per spec:
      - name: string
      - id: string
      - type: "model" | "dataset" | "code"
    """

    name: str
    id: str
    type: str


class ArtifactQuery(BaseModel):
    """
    Query used for /artifacts POST.
    Spec: name (required), types (optional list of ArtifactType).
    """

    name: str
    types: Optional[List[str]] = None


class ArtifactRegEx(BaseModel):
    """
    Request body for /artifact/byRegEx POST.
    Spec: regex (required string containing a regular expression pattern)
    """

    regex: str


class Artifact(BaseModel):
    """
    Full Artifact envelope: metadata + data.
    """

    metadata: ArtifactMetadata
    data: ArtifactData


# ---------- Storage helpers ----------


def ensure_artifact_dir() -> None:
    """Ensure the artifacts directory exists."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def store_artifact(artifact_id: str, data: dict) -> None:
    """Store artifact data as JSON on disk."""
    ensure_artifact_dir()
    filepath = ARTIFACTS_DIR / f"{artifact_id}.json"
    with filepath.open("w") as f:
        # data must contain only JSON-serializable types (str, int, list, dict, etc.)
        json.dump(data, f)


def get_stored_artifact(artifact_id: str) -> Optional[dict]:
    """Retrieve artifact JSON by ID."""
    filepath = ARTIFACTS_DIR / f"{artifact_id}.json"
    if filepath.exists():
        with filepath.open("r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return None
            if isinstance(data, dict):
                return data
    return None


def iter_all_artifacts() -> List[dict]:
    """Return all stored artifact dicts."""
    if not ARTIFACTS_DIR.exists():
        return []
    results: List[dict] = []
    for filename in os.listdir(ARTIFACTS_DIR):
        if not filename.endswith(".json"):
            continue
        artifact_id = filename[:-5]
        stored = get_stored_artifact(artifact_id)
        if stored and isinstance(stored.get("metadata"), dict):
            results.append(stored)
    return results


# ---------- /artifacts (list) ----------


@router.post("/artifacts", response_model=List[ArtifactMetadata])
def list_artifacts(
    query: List[ArtifactQuery],
    response: Response,
    offset: Optional[str] = None,
) -> List[ArtifactMetadata]:
    """
    List artifacts matching the query.

    Spec:
      - Request: array of ArtifactQuery.
      - Response: array of ArtifactMetadata (no wrapper object).
      - Header 'offset' is used for pagination; we always return "0" or the given one.

    Behavior:
      - For each query q:
          - name == "*"  => wildcard name (matches all names)
          - otherwise    => exact name match
          - types is None or [] => all types allowed
          - otherwise           => metadata.type must be in q.types
      - Results are the union of all queries (deduped by metadata.id).
    """
    # Simple pagination stub: always echo provided offset or "0"
    response.headers["offset"] = offset or "0"

    # No artifacts directory or no queries -> no results
    if not ARTIFACTS_DIR.exists():
        return []

    if not query:
        return []

    stored_artifacts = iter_all_artifacts()

    # Use dict keyed by id to dedupe across multiple queries
    results_by_id: dict[str, ArtifactMetadata] = {}

    for q in query:
        for a in stored_artifacts:
            md_raw = a.get("metadata", {})
            try:
                md = ArtifactMetadata(**md_raw)
            except Exception:
                # Skip malformed entries instead of crashing
                continue

            # Name matching
            if q.name != "*" and md.name != q.name:
                continue

            # Type matching
            if q.types is not None and len(q.types) > 0:
                if md.type not in q.types:
                    continue

            # Passed filters -> include
            results_by_id[md.id] = md

    return list(results_by_id.values())


# ---------- /artifact/byName/{name} (lookup by name) ----------


@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
def get_artifacts_by_name(name: str) -> List[ArtifactMetadata]:
    """
    Retrieve artifacts whose metadata.name matches the given name exactly.

    Behavior:
      - Returns a JSON array of ArtifactMetadata.
      - If multiple artifacts share the same name, all are returned.
      - If none match, returns an empty list (200).
    """
    if not ARTIFACTS_DIR.exists():
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []

    for a in stored_artifacts:
        md_raw = a.get("metadata", {})
        try:
            md = ArtifactMetadata(**md_raw)
        except Exception:
            continue

        if md.name == name:
            results.append(md)

    return results


# ---------- /artifact/{artifact_type} (create) ----------

VALID_TYPES = {"model", "dataset", "code"}


@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Artifact:
    """
    Register a new artifact of the given type.

    Spec:
      - Path: /artifact/{artifact_type}
      - Body: ArtifactData (must include 'url')
      - Responses:
          201: Artifact (metadata + data)
          400: malformed request
          409: Artifact exists already
    """
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    # Deterministic ID from type + URL
    raw_id = f"{artifact_type}:{artifact.url}"
    artifact_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:10]

    # Derive a human-readable name from the URL (last path segment)
    url_str = artifact.url
    if "/" in url_str:
        name = url_str.rstrip("/").split("/")[-1] or url_str
    else:
        name = url_str

    # Check for duplicates (same type + URL)
    for existing in iter_all_artifacts():
        md = existing.get("metadata", {})
        data = existing.get("data", {})
        if md.get("type") == artifact_type and data.get("url") == url_str:
            # Artifact exists already
            raise HTTPException(status_code=409, detail="Artifact exists already")

    # Set download_url equal to the source url (simple but valid URI)
    data_obj = ArtifactData(url=artifact.url, download_url=artifact.url)

    metadata = ArtifactMetadata(
        name=name,
        id=artifact_id,
        type=artifact_type,
    )

    artifact_obj = Artifact(
        metadata=metadata,
        data=data_obj,
    )

    # Persist to disk (now fully JSON-serializable)
    store_artifact(artifact_id, artifact_obj.dict())

    return artifact_obj


# ---------- /artifacts/{artifact_type}/{id} (get/delete/update) ----------


@router.get("/artifacts/{artifact_type}/{id}", response_model=Artifact)
def get_artifact(artifact_type: str, id: str) -> Artifact:
    """
    Retrieve an artifact by type and id.

    Spec path: /artifacts/{artifact_type}/{id}
    """
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


@router.delete("/artifacts/{artifact_type}/{id}")
def delete_artifact(artifact_type: str, id: str) -> dict:
    """
    Delete an artifact by type and id.
    """
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


@router.put("/artifacts/{artifact_type}/{id}", response_model=Artifact)
def update_artifact(artifact_type: str, id: str, artifact: Artifact) -> Artifact:
    """
    Update an existing artifact.

    Spec:
      - Path: /artifacts/{artifact_type}/{id}
      - Body: full Artifact envelope.
      - The name and id must match; artifact_type must match path.
    """
    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    md = stored.get("metadata", {})
    if md.get("type") != artifact_type:
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    # Validate that the incoming metadata matches the path
    if artifact.metadata.id != id or artifact.metadata.type != artifact_type:
        raise HTTPException(status_code=400, detail="Metadata id/type mismatch")

    # Overwrite stored artifact
    store_artifact(id, artifact.dict())

    try:
        return Artifact(**artifact.dict())
    except Exception:
        raise HTTPException(
            status_code=500, detail="Stored artifact is invalid after update"
        )


def verify_token(x_authorization: Optional[str] = Header(None)) -> bool:
    """
    Verify authentication token from X-Authorization header.
    Returns True if token is valid, raises HTTPException with 403 if not.
    """
    if not x_authorization:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    # Check if token is in issued_tokens
    if x_authorization not in issued_tokens:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    return True


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
def artifacts_by_regex(
    body: ArtifactRegEx,
    x_authorization: Optional[str] = Header(None),
) -> List[ArtifactMetadata]:
    """
    Search for artifacts using a regular expression pattern.

    The regex is applied to artifact names and README content.
    Returns an array of ArtifactMetadata objects for matches.

    Spec:
      - Request: ArtifactRegEx with required 'regex' field
      - Response: array of ArtifactMetadata
      - Responses:
          200: Success with matching artifacts (empty array if no matches)
          400: Missing/invalid regex field or malformed regex pattern
          403: Authentication failed
          404: No artifacts found matching the regex
    """
    # Verify authentication
    verify_token(x_authorization)

    # Validate regex field
    if not body.regex or not isinstance(body.regex, str) or body.regex.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid",
        )

    # Try to compile the regex pattern
    try:
        pattern = re.compile(body.regex)
    except re.error as e:
        raise HTTPException(
            status_code=400,
            detail=f"There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid: {str(e)}",
        )

    # Get all artifacts
    if not ARTIFACTS_DIR.exists():
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []
    results_by_id: dict[str, ArtifactMetadata] = {}

    # Search through all artifacts
    for artifact in stored_artifacts:
        md_raw = artifact.get("metadata", {})
        data_raw = artifact.get("data", {})

        try:
            md = ArtifactMetadata(**md_raw)
        except Exception:
            # Skip malformed entries
            continue

        # Check if regex matches the artifact name
        name_match = bool(pattern.search(md.name or ""))

        # Check if regex matches README content if present
        readme_match = False
        if data_raw and isinstance(data_raw, dict):
            readme = data_raw.get("readme") or data_raw.get("README")
            if readme and isinstance(readme, str):
                readme_match = bool(pattern.search(readme))

        # Add to results if either name or README matches
        if name_match or readme_match:
            results_by_id[md.id] = md

    results = list(results_by_id.values())

    # Per spec: return 404 if no artifacts match
    if not results:
        raise HTTPException(
            status_code=404, detail="No artifact found under this regex."
        )

    return results
