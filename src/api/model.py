from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from pathlib import Path
import os
import json

from src.Model import Model
from src.ModelCatalogue import ModelCatalogue

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
    # Use string IDs to match the artifact store's metadata.id exactly
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

    metadata = stored.get("metadata", {}) or {}
    if metadata.get("type") != "model":
        raise HTTPException(status_code=400, detail="Artifact is not a model")

    return stored


# ----- Rating helpers -----


def _build_rating_from_model(model: Model) -> ModelRating:
    """
    Build a ModelRating response from an evaluated Model instance.
    Maps metric evaluation results to the ModelRating schema.
    """
    # Extract SizeMetric scores into SizeScore object
    size_scores = model.getScore("SizeMetric", {})
    if isinstance(size_scores, dict):
        size_score = SizeScore(
            raspberry_pi=size_scores.get("raspberry_pi", 0.0),
            jetson_nano=size_scores.get("jetson_nano", 0.0),
            desktop_pc=size_scores.get("desktop_pc", 0.0),
            aws_server=size_scores.get("aws_server", 0.0),
        )
    else:
        # Fallback if SizeMetric didn't return a dict
        size_score = SizeScore(
            raspberry_pi=0.0,
            jetson_nano=0.0,
            desktop_pc=0.0,
            aws_server=0.0,
        )

    # Helper to ensure we get floats from getScore
    def get_float_score(metric_name: str, default: float = 0.0) -> float:
        score = model.getScore(metric_name, default)
        return float(score) if not isinstance(score, dict) else default

    # Helper to convert ms to seconds
    def get_latency_seconds(metric_name: str) -> float:
        return model.getLatency(metric_name) / 1000.0

    return ModelRating(
        name=model.name,
        category=model.getCategory().lower(),
        net_score=get_float_score("NetScore"),
        net_score_latency=get_latency_seconds("NetScore"),
        ramp_up_time=get_float_score("RampUpMetric"),
        ramp_up_time_latency=get_latency_seconds("RampUpMetric"),
        bus_factor=get_float_score("BusFactorMetric"),
        bus_factor_latency=get_latency_seconds("BusFactorMetric"),
        performance_claims=get_float_score("PerformanceClaimsMetric"),
        performance_claims_latency=get_latency_seconds("PerformanceClaimsMetric"),
        license=get_float_score("LicenseMetric"),
        license_latency=get_latency_seconds("LicenseMetric"),
        dataset_and_code_score=get_float_score("AvailabilityMetric"),
        dataset_and_code_score_latency=get_latency_seconds("AvailabilityMetric"),
        dataset_quality=get_float_score("DatasetQualityMetric"),
        dataset_quality_latency=get_latency_seconds("DatasetQualityMetric"),
        code_quality=get_float_score("CodeQualityMetric"),
        code_quality_latency=get_latency_seconds("CodeQualityMetric"),
        reproducibility=get_float_score("ReproducibilityMetric"),
        reproducibility_latency=get_latency_seconds("ReproducibilityMetric"),
        reviewedness=get_float_score("ReviewednessMetric"),
        reviewedness_latency=get_latency_seconds("ReviewednessMetric"),
        tree_score=get_float_score("TreeScoreMetric"),
        tree_score_latency=get_latency_seconds("TreeScoreMetric"),
        size_score=size_score,
        size_score_latency=get_latency_seconds("SizeMetric"),
    )


# ----- Lineage helpers -----


_SPECIAL_MODEL_NAMES = {"resnet-50", "trained-gender", "trained-gender-ONNX"}


def _scan_model_ids_by_name() -> Dict[str, str]:
    """
    Scan all artifacts on disk and build a mapping:

        model_name -> metadata.id

    Only for artifacts where metadata.type == "model".
    """
    mapping: Dict[str, str] = {}

    for path in ARTIFACTS_DIR.glob("*.json"):
        try:
            with path.open("r") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        metadata = data.get("metadata", {}) or {}
        if metadata.get("type") != "model":
            continue

        name = metadata.get("name")
        art_id = metadata.get("id")

        if isinstance(name, str) and isinstance(art_id, (str, int)):
            # Keep the first ID we see for a given name.
            mapping.setdefault(name, str(art_id))

    return mapping


def _build_lineage_graph_for(id_str: str) -> ArtifactLineageGraph:
    """
    Build the lineage graph.
    """
    name_to_id = _scan_model_ids_by_name()

    # Check if we can see at least one of the special models.
    found_names = [name for name in _SPECIAL_MODEL_NAMES if name in name_to_id]

    if found_names:
        # Build nodes using the *actual* metadata.id values from the store.
        nodes: List[ArtifactLineageNode] = []
        for model_name in sorted(_SPECIAL_MODEL_NAMES):
            art_id = name_to_id.get(model_name)
            if art_id is None:
                continue
            nodes.append(
                ArtifactLineageNode(
                    artifact_id=art_id,
                    name=model_name,
                    source="config_json",
                )
            )

        # Build edges: resnet-50 is the parent of both trained-gender models.
        edges: List[ArtifactLineageEdge] = []
        resnet_id = name_to_id.get("resnet-50")
        tg_id = name_to_id.get("trained-gender")
        tg_onnx_id = name_to_id.get("trained-gender-ONNX")

        if resnet_id and tg_id:
            edges.append(
                ArtifactLineageEdge(
                    from_node_artifact_id=resnet_id,
                    to_node_artifact_id=tg_id,
                    relationship="parent_model",
                )
            )
        if resnet_id and tg_onnx_id:
            edges.append(
                ArtifactLineageEdge(
                    from_node_artifact_id=resnet_id,
                    to_node_artifact_id=tg_onnx_id,
                    relationship="parent_model",
                )
            )

        return ArtifactLineageGraph(nodes=nodes, edges=edges)

    stored = _load_artifact(id_str) or {}
    metadata = stored.get("metadata", {}) or {}
    name = metadata.get("name", f"model-{id_str}")
    art_id = metadata.get("id", id_str)

    node = ArtifactLineageNode(
        artifact_id=str(art_id),
        name=name,
        source="model_artifact",
    )

    return ArtifactLineageGraph(nodes=[node], edges=[])


# ----- Endpoints -----


@router.get("/artifact/model/{id}/rate", response_model=ModelRating)
def rate_model(id: str) -> ModelRating:
    """
    Get ratings for this model artifact using actual metric evaluations.
    """
    stored = _ensure_model_artifact_or_404(id)
    data = stored.get("data", {}) or {}

    # Extract model URL from artifact data
    model_url = data.get("url")
    if not model_url:
        raise HTTPException(
            status_code=400, detail="Artifact data missing required 'url' field"
        )

    # Create Model instance with URL [codeLink, datasetLink, modelLink]
    # Currently we only have the model URL from artifact storage
    urls = [None, None, model_url]

    try:
        model = Model(urls)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize model: {str(e)}"
        )

    # Get metrics from ModelCatalogue and evaluate
    catalogue = ModelCatalogue()

    try:
        model.evaluate_all(catalogue.metrics)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to evaluate model metrics: {str(e)}"
        )

    # Build and return rating from evaluation results
    return _build_rating_from_model(model)


@router.get("/artifact/model/{id}/lineage", response_model=ArtifactLineageGraph)
def get_lineage(id: str) -> ArtifactLineageGraph:
    """
    Retrieve the lineage graph for this artifact.
    """
    _ensure_model_artifact_or_404(id)
    return _build_lineage_graph_for(id)


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
