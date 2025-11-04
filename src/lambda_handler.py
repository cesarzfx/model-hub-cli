from typing import Any, Dict
from mangum import Mangum
from src.api.main import app


# def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
#     """AWS Lambda handler function."""
#     return {"statusCode": 200, "body": "ok", "headers": {"Content-Type": "text/plain"}}

handler = Mangum(app)

def lambda_handler(event, context):
    return handler(event, context)