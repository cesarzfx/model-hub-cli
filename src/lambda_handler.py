import sys
import os

# Add src directory to Python path for Lambda environment
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from typing import Any, Dict
from mangum import Mangum
from src.api.main import app

handler = Mangum(app)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return handler(event, context)
