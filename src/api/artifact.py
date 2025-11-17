from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from pathlib import Path
import os
import json
import hashlib

router = APIRouter()

# Use /tmp on Lambda; can override with ARTIFACTS_DIR env var for local dev
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))


# ---------- Models ----------


class ArtifactData(BaseModel):
    """
    ArtifactData as per spec:
      - url: required, uri string
      - download_url: optional, read-only in spec (we set it in responses)
    """

    url: HttpUrl
    download_url: Optional[HttpUrl] = None


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
    """
    # Simple pagination stub: always echo provided offset or "0"
    response.headers["offset"] = offset or "0"

    if not ARTIFACTS_DIR.exists():
        return []

    if not query:
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []

    # Wildcard query: return all artifacts
    if query[0].name == "*":
        for a in stored_artifacts:
            md = a.get("metadata", {})
            try:
                results.append(ArtifactMetadata(**md))
            except Exception:
                # Skip malformed entries instead of crashing
                continue
        return results

    # Otherwise, match by name (ignore types for now)
    wanted_names = {q.name for q in query}
    for a in stored_artifacts:
        md = a.get("metadata", {})
        if md.get("name") in wanted_names:
            try:
                results.append(ArtifactMetadata(**md))
            except Exception:
                continue

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
    url_str = str(artifact.url)
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

    # Persist to disk
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
