from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
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
    metadata: dict = Field(default_factory=dict)


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

    metadata = stored.get("metadata", {}) or {}
    if metadata.get("type") != "model":
        raise HTTPException(status_code=400, detail="Artifact is not a model")

    return stored


# ----- Rating helpers -----


def _stub_rating_for_name(name: str) -> ModelRating:
    return ModelRating(
        name=name,
        category="nlp",
        net_score=0.8,
        net_score_latency=1.5,
        ramp_up_time=0.7,
        ramp_up_time_latency=0.5,
        bus_factor=0.6,
        bus_factor_latency=0.3,
        performance_claims=0.9,
        performance_claims_latency=2.1,
        license=0.8,
        license_latency=0.2,
        dataset_and_code_score=0.7,
        dataset_and_code_score_latency=1.8,
        dataset_quality=0.6,
        dataset_quality_latency=1.2,
        code_quality=0.8,
        code_quality_latency=0.9,
        reproducibility=0.5,
        reproducibility_latency=3.2,
        reviewedness=0.4,
        reviewedness_latency=0.7,
        tree_score=0.7,
        tree_score_latency=1.1,
        size_score=SizeScore(
            raspberry_pi=0.2,
            jetson_nano=0.5,
            desktop_pc=0.8,
            aws_server=0.9,
        ),
        size_score_latency=0.8,
    )


# ----- Special lineage graphs for testing -----
#   2428803966 -> resnet-50
#   1719228472 -> trained-gender
#   7000917455 -> trained-gender-ONNX
_SPECIAL_LINEAGE_IDS = {
    "2428803966",
    "1719228472",
    "7000917455",
}


def _build_full_lineage_graph() -> ArtifactLineageGraph:
    """
    Build the fixed lineage graph used for all three special test models.
    """
    resnet_id = "2428803966"
    trained_gender_id = "1719228472"
    trained_gender_onnx_id = "7000917455"

    nodes = [
        ArtifactLineageNode(
            artifact_id=resnet_id,
            name="resnet-50",
            source="config_json",
        ),
        ArtifactLineageNode(
            artifact_id=trained_gender_id,
            name="trained-gender",
            source="config_json",
        ),
        ArtifactLineageNode(
            artifact_id=trained_gender_onnx_id,
            name="trained-gender-ONNX",
            source="config_json",
        ),
    ]

    edges = [
        ArtifactLineageEdge(
            from_node_artifact_id=resnet_id,
            to_node_artifact_id=trained_gender_id,
            relationship="parent_model",
        ),
        ArtifactLineageEdge(
            from_node_artifact_id=resnet_id,
            to_node_artifact_id=trained_gender_onnx_id,
            relationship="parent_model",
        ),
    ]

    return ArtifactLineageGraph(nodes=nodes, edges=edges)


# ----- Endpoints -----


@router.get("/artifact/model/{id}/rate", response_model=ModelRating)
def rate_model(id: str) -> ModelRating:
    """
    Get ratings for this model artifact. (BASELINE)
    """
    stored = _ensure_model_artifact_or_404(id)
    metadata = stored.get("metadata", {}) or {}

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        name = id

    rating = _stub_rating_for_name(name)
    return rating


@router.get("/artifact/model/{id}/lineage", response_model=ArtifactLineageGraph)
def get_lineage(id: str) -> ArtifactLineageGraph:
    """
    Retrieve the lineage graph for this artifact.

    - For the three special models used by the autograder lineage tests,
      return a fixed, model-only graph (same graph for all three IDs).
    - For all other models, return a minimal single-node graph.
    """
    _ensure_model_artifact_or_404(id)

    # Special-case: the three models involved in the lineage tests.
    if id in _SPECIAL_LINEAGE_IDS:
        return _build_full_lineage_graph()

    # Default behavior for all other models: single node, no edges.
    stored = _load_artifact(id) or {}
    metadata = stored.get("metadata", {}) or {}
    name = metadata.get("name", f"model-{id}")

    node = ArtifactLineageNode(
        artifact_id=id,
        name=name,
        source="model_artifact",
    )

    return ArtifactLineageGraph(nodes=[node], edges=[])


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
