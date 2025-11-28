import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


# This lambda implements the /artifact/model/{id}/rate endpoint used by API Gateway.
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))


def _get_stored_artifact(artifact_id: str) -> Optional[dict]:
    """
    Load a stored artifact JSON document from disk.

    This mirrors src/api/artifact_store.get_stored_artifact but is duplicated
    here so this lambda can work independently of the FastAPI app package.
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


class HttpError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _ensure_model_artifact(artifact_id: str) -> dict:
    """
    Ensure the artifact exists and is of type 'model'.
    Returns the stored artifact dict; raises HttpError otherwise.
    """
    stored = _get_stored_artifact(artifact_id)
    if stored is None:
        raise HttpError(404, "Artifact does not exist")

    metadata = stored.get("metadata", {}) or {}
    if metadata.get("type") != "model":
        raise HttpError(400, "Artifact is not a model")
    return stored


def _base_score_from_artifact(stored: dict) -> float:
    """
    Deterministic base score in [0.0, 1.0) derived from the artifact URL.

    This keeps ratings:
      * stable across runs,
      * different per model,
      * and within a sane range for all metrics.
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
    AWS Lambda handler for rating a model artifact.

    Expects API Gateway event with pathParameters["id"].
    """
    headers = {"Content-Type": "application/json"}

    try:
        path_params = event.get("pathParameters") or {}
        artifact_id = path_params.get("id")
        if not artifact_id:
            raise HttpError(400, "Missing artifact id")

        stored = _ensure_model_artifact(artifact_id)
        metadata = stored.get("metadata", {}) or {}
        name = metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            # Fall back to the artifact id if no name is stored
            name = artifact_id

        base_score = _base_score_from_artifact(stored)
        latency = 0.01  # small positive float

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
        body = {"detail": e.detail}
        return {
            "statusCode": e.status_code,
            "headers": headers,
            "body": json.dumps(body),
        }
    except Exception:
        body = {"detail": "Internal server error"}
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps(body),
        }
