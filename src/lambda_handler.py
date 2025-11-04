from typing import Any, Dict


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function."""
    return {"statusCode": 200, "body": "ok", "headers": {"Content-Type": "text/plain"}}
