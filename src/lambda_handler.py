import os
import sys
from typing import Any, Dict
from mangum import Mangum

# Try local import first, then fall back to Lambda import path
try:
    from src.api.main import app  # Local development
except ImportError:
    from api.main import app  # type: ignore  # Lambda deployment

handler = Mangum(app)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return handler(event, context)
