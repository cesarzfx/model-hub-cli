from fastapi import FastAPI
import yaml
from .artifact import router as artifact_router
from .model import router as model_router
from .reset import router as reset_router
from .health import router as health_router
from .auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
import os
from loguru import logger
from starlette.requests import Request

# Load the OpenAPI spec
with open("ece461_fall_2025_openapi_spec.yaml", "r") as f:
    openapi_spec = yaml.safe_load(f)

app = FastAPI(
    title=openapi_spec["info"]["title"],
    description=openapi_spec["info"]["description"],
    version=openapi_spec["info"]["version"],
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this would be more restrictive
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware

from starlette.responses import Response
from typing import Callable


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    logger.info(f"Endpoint called: {request.url.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    body = await request.body()
    logger.info(f"Request body: {body.decode('utf-8') if body else 'None'}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    # Log response body safely
    if hasattr(response, "body"):
        try:
            logger.info(
                f"Response body: {response.body.decode('utf-8') if response.body else 'None'}"
            )
        except Exception as e:
            logger.warning(f"Could not log response body: {e}")
    return response


# Create artifacts directory if it doesn't exist
if not os.path.exists("/tmp/artifacts"):
    os.makedirs("/tmp/artifacts")

# Include routers
app.include_router(health_router, tags=["system"])
app.include_router(auth_router, tags=["auth"])
app.include_router(artifact_router, tags=["artifacts"])
app.include_router(model_router, tags=["models"])
app.include_router(reset_router, tags=["system"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
