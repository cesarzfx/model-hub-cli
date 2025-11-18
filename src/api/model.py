from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import json

router = APIRouter()

# Must match the directory used by artifact.py
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))


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


def _load_artifact(artifact_id: str) -> Optional[dict]:
    """
    Load a stored artifact JSON document written by src/api/artifact.py.
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


# ----- Endpoints -----


@router.get("/artifact/model/{id}/rate", response_model=ModelRating)
def rate_model(
    id: str,
    x_authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
) -> ModelRating:
    """
    Get ratings for this model artifact. (BASELINE)

    We compute a simple synthetic rating with fixed values.
    The important part is that the response matches the ModelRating schema.
    """
    stored = _ensure_model_artifact_or_404(id)
    metadata = stored.get("metadata", {})
    name = metadata.get("name", f"model-{id}")

    # Dummy but valid scores in [0, 1] range, with small non-zero latencies.
    base_score = 0.8
    latency = 0.01

    size_score = SizeScore(
        raspberry_pi=0.6,
        jetson_nano=0.7,
        desktop_pc=0.9,
        aws_server=1.0,
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
def get_lineage(
    id: str,
    x_authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
) -> ArtifactLineageGraph:
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
def license_check(
    id: str,
    request: SimpleLicenseCheckRequest,
    x_authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
) -> bool:
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
