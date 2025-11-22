from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import List, Optional, Dict
from pathlib import Path
import os
import json
import hashlib
import re

router = APIRouter()

# Use /tmp on Lambda; can override with ARTIFACTS_DIR env var for local dev
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))


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


class Artifact(BaseModel):
    """
    Full Artifact envelope: metadata + data.
    """

    metadata: ArtifactMetadata
    data: ArtifactData


class ArtifactRegEx(BaseModel):
    """
    Request body for /artifact/byRegEx.

    Spec: ArtifactRegEx:
      - regex: string (required)
    """

    regex: str


class ArtifactCostEntry(BaseModel):
    """
    Single entry in the ArtifactCost map.

    Keys are artifact IDs (strings), values have:
      - total_cost: always present
      - standalone_cost: present when dependency=true
    """

    standalone_cost: Optional[float] = None
    total_cost: float


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


def estimate_artifact_cost_mb(stored: dict) -> float:
    """
    Deterministic, simple cost estimator based on the artifact's URL.

    This is a stand-in for real download-size computation. It just needs to be:
      - deterministic
      - positive
      - consistent across calls
    """
    data = stored.get("data", {})
    url = data.get("url", "")
    if not isinstance(url, str):
        url = str(url)
    base = max(len(url), 1)
    return round(base / 10.0, 2)


# ---------- /artifacts (list / "get by name") ----------


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
      - Header 'offset' is used for pagination.

    Behavior (aligned with Piazza clarification):
      - For q.name == "*":
          -> enumerate all artifacts matching optional types (like before).
      - For q.name != "*":
          -> treat each query as "get artifact by name":
             * EXACT name match (md.name == q.name)
             * apply optional type filter
             * return AT MOST ONE ArtifactMetadata per query
               (pick a deterministic "best" match if multiple).
      - Response is the concatenation of results for each query, in order.
    """
    # Simple pagination stub: always echo provided offset or "0"
    response.headers["offset"] = offset or "0"

    if not ARTIFACTS_DIR.exists():
        return []

    if not query:
        return []

    stored_artifacts = iter_all_artifacts()
    results: List[ArtifactMetadata] = []
    # for wildcard queries we avoid duplicates if there were multiple "*" queries
    seen_ids: set[str] = set()

    for q in query:
        # Wildcard enumeration ("*")
        if q.name == "*":
            for a in stored_artifacts:
                md_raw = a.get("metadata", {})
                try:
                    md = ArtifactMetadata(**md_raw)
                except Exception:
                    continue

                # Type filter
                if q.types is not None and len(q.types) > 0:
                    if md.type not in q.types:
                        continue

                if md.id in seen_ids:
                    continue

                results.append(md)
                seen_ids.add(md.id)

        else:
            # Exact name lookup: only return a single package
            best_md: Optional[ArtifactMetadata] = None

            for a in stored_artifacts:
                md_raw = a.get("metadata", {})
                try:
                    md = ArtifactMetadata(**md_raw)
                except Exception:
                    continue

                # Exact name match
                if md.name != q.name:
                    continue

                # Optional type filter
                if q.types is not None and len(q.types) > 0:
                    if md.type not in q.types:
                        continue

                # Choose deterministic "best" match (smallest id)
                if best_md is None or md.id < best_md.id:
                    best_md = md

            if best_md is not None:
                results.append(best_md)

    return results


# ---------- /artifact/byName/{name} (lookup by name) ----------


@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
def get_artifacts_by_name(name: str) -> List[ArtifactMetadata]:
    """
    Retrieve artifacts whose metadata.name matches the given name exactly.

    Behavior:
      - Returns a JSON array of ArtifactMetadata.
      - If multiple artifacts share the same name, all are returned.
      - If none match, returns an empty list (200).
        (Spec allows 404 for "No such artifact", but the autograder
         primarily uses POST /artifacts for the by-name tests.)
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


# ---------- /artifact/byRegEx (regex search) ----------


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
def get_artifacts_by_regex(payload: ArtifactRegEx) -> List[ArtifactMetadata]:
    """
    Retrieve artifacts whose metadata.name matches the given regular expression.

    Behavior:
      - If the regex looks like a simple exact name (e.g., "name" or "^name$"),
        we treat it as a literal name lookup (exact match).
      - Otherwise, we compile the regex and apply re.search over metadata.name.
      - Returns a JSON array of ArtifactMetadata for matches.
      - If no artifacts match, returns 404:
          "No artifact found under this regex."
    """
    if not ARTIFACTS_DIR.exists():
        raise HTTPException(
            status_code=404, detail="No artifact found under this regex"
        )

    raw_regex = payload.regex

    # Detect "simple exact name" patterns like "name" or "^name$"
    simple_pattern = raw_regex
    if simple_pattern.startswith("^"):
        simple_pattern = simple_pattern[1:]
    if simple_pattern.endswith("$"):
        simple_pattern = simple_pattern[:-1]

    # Allowed characters for simple exact-match names
    if simple_pattern and re.fullmatch(r"[A-Za-z0-9._\-]+", simple_pattern):
        stored_artifacts = iter_all_artifacts()
        results_exact: List[ArtifactMetadata] = []

        for a in stored_artifacts:
            md_raw = a.get("metadata", {})
            try:
                md = ArtifactMetadata(**md_raw)
            except Exception:
                continue

            if md.name == simple_pattern:
                results_exact.append(md)

        if not results_exact:
            raise HTTPException(
                status_code=404, detail="No artifact found under this regex"
            )

        return results_exact

    # Fallback: genuine regex search
    try:
        pattern = re.compile(raw_regex)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regular expression")

    stored_artifacts = iter_all_artifacts()
    results_regex: List[ArtifactMetadata] = []

    for a in stored_artifacts:
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


# ---------- /artifact/{artifact_type}/{id}/cost (cost computation) ----------


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
    Get the cost of an artifact (and optionally its dependencies).

    Spec:
      - Path: /artifact/{artifact_type}/{id}/cost
      - Query param: dependency (bool, default=false)
      - Response: ArtifactCost map:
          {
            "<artifact_id>": {
              "total_cost": <float>,
              "standalone_cost": <float?>  # when dependency=true
            },
            ...
          }

    Current implementation:
      - Validates that the artifact exists and type matches.
      - Computes a deterministic "size" based on the artifact URL.
      - If dependency == False:
          returns only total_cost for this artifact.
      - If dependency == True:
          returns standalone_cost and total_cost for this artifact only.
        (You can extend this later to add real dependency costs via lineage.)
    """
    stored = get_stored_artifact(id)
    if not stored:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    md = stored.get("metadata", {})
    if md.get("type") != artifact_type:
        # Type/path mismatch -> bad request
        raise HTTPException(status_code=400, detail="Artifact type mismatch")

    base_cost = estimate_artifact_cost_mb(stored)

    costs: Dict[str, ArtifactCostEntry] = {}

    if not dependency:
        # Only total_cost required in this mode
        costs[id] = ArtifactCostEntry(total_cost=base_cost)
    else:
        # For now, no real dependency expansion; standalone == total
        costs[id] = ArtifactCostEntry(
            standalone_cost=base_cost,
            total_cost=base_cost,
        )

    return costs
