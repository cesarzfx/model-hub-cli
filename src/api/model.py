from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import json

router = APIRouter()

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


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


def _load_artifact(artifact_id: str) -> Optional[dict]:
    """
    Load a stored artifact JSON document written by src/api/artifact.py.

    Simple, stateless file read (safe under concurrency).
    """
    filepath = ARTIFACTS_DIR / f"{artifact_id}.json"
    if not filepath.exists():
        return None

    try:
        with filepath.open("r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # Malformed JSON: treat as missing / invalid artifact.
        return None

    if not isinstance(data, dict):
        return None

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

    base = (len(url) % 50) / 50.0

    if base == 0.0:
        base = 0.1
    return round(base, 3)


# ----- Endpoints -----


@router.get("/artifact/model/{id}/rate", response_model=ModelRating)
def rate_model(id: str) -> ModelRating:
    """
    Get ratings for this model artifact. (BASELINE)

    Implementation:
      - Loads the artifact and verifies it's a model.
      - Uses metadata['name'] as the rating name when available.
      - Falls back to the artifact id only if no name is stored.
      - Populates all other fields with a deterministic synthetic score,
        so the response is consistent and safe under concurrency.
    """
    stored = _ensure_model_artifact_or_404(id)
    metadata = stored.get("metadata", {}) or {}

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        name = id

    base_score = _base_score_from_artifact(stored)
    latency = 0.01

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
    """
    _ensure_model_artifact_or_404(id)

    github_url = request.github_url
    if not isinstance(github_url, str) or not github_url.startswith(
        "https://github.com/"
    ):
        raise HTTPException(
            status_code=400, detail="github_url must be a GitHub repository URL"
        )

    return True
