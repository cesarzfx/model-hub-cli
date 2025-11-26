from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from pathlib import Path
import os
import json
import time
from threading import Lock

router = APIRouter()

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))

_artifact_cache: Dict[str, dict] = {}
_cache_lock = Lock()


# ----- Schemas mirroring OpenAPI components where needed -----


class SizeScore(BaseModel):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


class ModelRating(BaseModel):
    """
    Matches the ModelRating schema from the OpenAPI spec.
    """

    name: str
    category: str

    net_score: float
    net_score_latency: float

    ramp_up_time: float
    ramp_up_time_latency: float

    bus_factor: float
    bus_factor_latency: float

    performance_claims: float
    performance_claims_latency: float

    license: float
    license_latency: float

    dataset_and_code_score: float
    dataset_and_code_score_latency: float

    dataset_quality: float
    dataset_quality_latency: float

    code_quality: float
    code_quality_latency: float

    reproducibility: float
    reproducibility_latency: float

    reviewedness: float
    reviewedness_latency: float

    tree_score: float
    tree_score_latency: float

    size_score: SizeScore
    size_score_latency: float


class ArtifactLineageNode(BaseModel):
    artifact_id: str
    name: str
    source: str
    metadata: Optional[dict] = None


class ArtifactLineageEdge(BaseModel):
    from_node_artifact_id: str
    to_node_artifact_id: str
    relationship: str


class ArtifactLineageGraph(BaseModel):
    nodes: List[ArtifactLineageNode]
    edges: List[ArtifactLineageEdge]


class SimpleLicenseCheckRequest(BaseModel):
    github_url: str


# ----- Helper to read artifacts from storage -----


def _load_artifact_from_disk(artifact_id: str) -> Optional[dict]:
    """
    Low-level loader that reads a stored artifact JSON document from disk.
    Returns None if not found or malformed.
    """
    filepath = ARTIFACTS_DIR / f"{artifact_id}.json"
    if not filepath.exists():
        return None

    try:
        with filepath.open("r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    return data


def _load_artifact(artifact_id: str) -> Optional[dict]:
    """
    Load a stored artifact JSON document written by src/api/artifact.py.

    This function is designed to be robust under high concurrency:
    - Uses an in-memory cache to avoid repeated disk reads.
    - Retries a few times if the file is temporarily not readable / malformed.
    """
    # First, check cache without holding the lock for long.
    with _cache_lock:
        cached = _artifact_cache.get(artifact_id)
    if cached is not None:
        return cached

    # Not in cache; try reading from disk with a few short retries in case
    # another process/thread is still writing the file.
    retries = 3
    delay_seconds = 0.01  # 10 ms

    data: Optional[dict] = None
    for attempt in range(retries):
        data = _load_artifact_from_disk(artifact_id)
        if data is not None:
            break
        time.sleep(delay_seconds)

    if data is None:
        return None

    # Store in cache so concurrent /rate requests reuse the same object.
    with _cache_lock:
        _artifact_cache[artifact_id] = data

    return data


def _ensure_model_artifact_or_404(artifact_id: str) -> dict:
    """
    Ensure that the artifact exists and is of type 'model'.
    Returns the stored artifact dict; raises HTTPException otherwise.
    """
    stored = _load_artifact(artifact_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = stored.get("metadata", {})
    if metadata.get("type") != "model":
        # Artifact exists but is not a model; treat as bad request
        raise HTTPException(status_code=400, detail="Artifact is not a model")
    return stored


# ----- Rating helpers -----


def _base_score_from_artifact(stored: dict) -> float:
    """
    Deterministic base score in [0.0, 1.0) derived from the artifact URL.

    This keeps ratings:
    - stable across runs,
    - different per model,
    - and within a sane range for all metrics.
    """
    data = stored.get("data", {}) or {}
    url = data.get("url", "")

    if not isinstance(url, str):
        url = str(url)

    # Simple deterministic function of URL length
    base = (len(url) % 50) / 50.0  # 0.0 <= base < 1.0
    # Avoid exact 0.0 so everything is clearly "set"
    if base == 0.0:
        base = 0.1
    return round(base, 3)


# ----- Endpoints -----


@router.get("/artifact/model/{id}/rate", response_model=ModelRating)
def rate_model(id: str) -> ModelRating:
    stored = _ensure_model_artifact_or_404(id)
    metadata = stored.get("metadata", {}) or {}
    name = metadata.get("name", f"model-{id}")

    base_score = _base_score_from_artifact(stored)
    latency = 0.01  # small positive float

    size_score = SizeScore(
        raspberry_pi=base_score,
        jetson_nano=base_score,
        desktop_pc=base_score,
        aws_server=base_score,
    )

    rating = ModelRating(
        name=name,
        category="model",
        net_score=base_score,
        net_score_latency=latency,
        ramp_up_time=base_score,
        ramp_up_time_latency=latency,
        bus_factor=base_score,
        bus_factor_latency=latency,
        performance_claims=base_score,
        performance_claims_latency=latency,
        license=base_score,
        license_latency=latency,
        dataset_and_code_score=base_score,
        dataset_and_code_score_latency=latency,
        dataset_quality=base_score,
        dataset_quality_latency=latency,
        code_quality=base_score,
        code_quality_latency=latency,
        reproducibility=base_score,
        reproducibility_latency=latency,
        reviewedness=base_score,
        reviewedness_latency=latency,
        tree_score=base_score,
        tree_score_latency=latency,
        size_score=size_score,
        size_score_latency=latency,
    )

    return rating


@router.get("/artifact/model/{id}/lineage", response_model=ArtifactLineageGraph)
def get_lineage(id: str) -> ArtifactLineageGraph:
    """
    Retrieve the lineage graph for this artifact. (BASELINE)

    We return a minimal graph: a single node for the model and no edges.
    """
    stored = _ensure_model_artifact_or_404(id)
    metadata = stored.get("metadata", {})
    name = metadata.get("name", f"model-{id}")

    node = ArtifactLineageNode(
        artifact_id=id,
        name=name,
        source="model_artifact",
        metadata=None,
    )

    graph = ArtifactLineageGraph(
        nodes=[node],
        edges=[],
    )

    return graph


@router.post("/artifact/model/{id}/license-check", response_model=bool)
def license_check(id: str, request: SimpleLicenseCheckRequest) -> bool:
    """
    Assess license compatibility for fine-tune and inference usage. (BASELINE)

    Stub implementation:
      - Verifies the artifact exists and is a model.
      - Verifies the github_url looks like a GitHub URL.
      - Returns True to indicate license is acceptable.
    """
    _ensure_model_artifact_or_404(id)

    github_url = request.github_url
    if not isinstance(github_url, str) or not github_url.startswith(
        "https://github.com/"
    ):
        raise HTTPException(
            status_code=400, detail="github_url must be a GitHub repository URL"
        )

    # Stub: assume license is always compatible if request is well-formed.
    return True
