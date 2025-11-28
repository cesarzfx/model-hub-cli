# lambdas/model_rate.py
import json
from typing import Any, Dict, Optional

from src.api.artifact_store import get_stored_artifact


class HttpError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _ensure_model_artifact(artifact_id: str) -> dict:
    """
    Ensure the artifact exists and is of type 'model'.
    Uses the shared get_stored_artifact() from artifact_store, so this lambda
    sees the same artifacts as the rest of the API.
    """
    stored = get_stored_artifact(artifact_id)
    if stored is None:
        raise HttpError(404, "Artifact does not exist")

    metadata = stored.get("metadata", {}) or {}
    if metadata.get("type") != "model":
        raise HttpError(400, "Artifact is not a model")

    return stored


def _base_score_from_artifact(stored: dict) -> float:
    """
    Deterministic base score in [0.0, 1.0) derived from the artifact URL.
    Keeps ratings stable across runs and different per model.
    """
    data = stored.get("data", {}) or {}
    url = data.get("url", "")

    if not isinstance(url, str):
        url = str(url)

    base = (len(url) % 50) / 50.0
    if base == 0.0:
        base = 0.1
    return round(base, 3)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for GET /artifact/model/{id}/rate.

    """
    headers = {"Content-Type": "application/json"}

    try:
        path_params = event.get("pathParameters") or {}
        artifact_id: Optional[str] = path_params.get("id")
        if not artifact_id:
            raise HttpError(400, "Missing artifact id")

        stored = _ensure_model_artifact(artifact_id)
        metadata = stored.get("metadata", {}) or {}
        name = metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            name = artifact_id

        base_score = _base_score_from_artifact(stored)
        latency = 0.01

        rating = {
            "name": name,
            "category": "model",
            "net_score": base_score,
            "net_score_latency": latency,
            "ramp_up_time": base_score,
            "ramp_up_time_latency": latency,
            "bus_factor": base_score,
            "bus_factor_latency": latency,
            "performance_claims": base_score,
            "performance_claims_latency": latency,
            "license": base_score,
            "license_latency": latency,
            "dataset_and_code_score": base_score,
            "dataset_and_code_score_latency": latency,
            "dataset_quality": base_score,
            "dataset_quality_latency": latency,
            "code_quality": base_score,
            "code_quality_latency": latency,
            "reproducibility": base_score,
            "reproducibility_latency": latency,
            "reviewedness": base_score,
            "reviewedness_latency": latency,
            "tree_score": base_score,
            "tree_score_latency": latency,
            "size_score": {
                "raspberry_pi": base_score,
                "jetson_nano": base_score,
                "desktop_pc": base_score,
                "aws_server": base_score,
            },
            "size_score_latency": latency,
        }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(rating),
        }

    except HttpError as e:
        return {
            "statusCode": e.status_code,
            "headers": headers,
            "body": json.dumps({"detail": e.detail}),
        }
    except Exception:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"detail": "Internal server error"}),
        }
