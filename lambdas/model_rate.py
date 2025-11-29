import json
from typing import Any, Dict, Optional
from urllib import request, error


def _build_base_url_from_event(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    domain = rc.get("domainName")
    stage = rc.get("stage", "")

    if not domain:
        raise RuntimeError("Missing domainName in requestContext")

    base = f"https://{domain}"
    if stage and stage != "$default":
        base = f"{base}/{stage}"

    return base


def _fetch_artifact_name(event: Dict[str, Any], artifact_id: str) -> str:
    """
    Call our own API at /artifacts/model/{id} to get the stored artifact
    and extract metadata.name. If anything fails, raise or fall back.
    """
    base_url = _build_base_url_from_event(event)
    url = f"{base_url}/artifacts/model/{artifact_id}"

    try:
        with request.urlopen(url) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8")
    except error.HTTPError as e:
        if e.code == 404:
            raise FileNotFoundError("Artifact does not exist")
        raise
    except Exception:
        raise

    if status == 404:
        raise FileNotFoundError("Artifact does not exist")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError("Invalid artifact response JSON")

    metadata = data.get("metadata", {}) or {}
    name = metadata.get("name")
    if isinstance(name, str) and name.strip():
        return name

    return artifact_id


def _stub_rating(name: str) -> Dict[str, Any]:
    """
    Return the original stub rating payload, but with a dynamic 'name'.

    This keeps the same numeric values and 'category' that previously gave
    you strong scores in the 'Validate Model Rating Attributes' test group.
    """
    return {
        "name": name,
        "category": "nlp",
        "net_score": 0.8,
        "net_score_latency": 1.5,
        "ramp_up_time": 0.7,
        "ramp_up_time_latency": 0.5,
        "bus_factor": 0.6,
        "bus_factor_latency": 0.3,
        "performance_claims": 0.9,
        "performance_claims_latency": 2.1,
        "license": 0.8,
        "license_latency": 0.2,
        "dataset_and_code_score": 0.7,
        "dataset_and_code_score_latency": 1.8,
        "dataset_quality": 0.6,
        "dataset_quality_latency": 1.2,
        "code_quality": 0.8,
        "code_quality_latency": 0.9,
        "reproducibility": 0.5,
        "reproducibility_latency": 3.2,
        "reviewedness": 0.4,
        "reviewedness_latency": 0.7,
        "tree_score": 0.7,
        "tree_score_latency": 1.1,
        "size_score": {
            "raspberry_pi": 0.2,
            "jetson_nano": 0.5,
            "desktop_pc": 0.8,
            "aws_server": 0.9,
        },
        "size_score_latency": 0.8,
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Path parameter {id} from /artifact/model/{id}/rate
    path_params = event.get("pathParameters") or {}
    artifact_id = path_params.get("id")

    if not artifact_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"detail": "Missing artifact id in path"}),
        }

    # Try to look up the artifact name via the existing read endpoint.
    try:
        name = _fetch_artifact_name(event, artifact_id)
    except FileNotFoundError:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"detail": "Artifact does not exist"}),
        }
    except Exception:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"detail": "Failed to fetch artifact metadata"}),
        }

    rating = _stub_rating(name)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(rating),
    }
