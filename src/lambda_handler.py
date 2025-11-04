from typing import Any, Dict
from mangum import Mangum
from api.main import app


handler = Mangum(app)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return handler(event, context)
