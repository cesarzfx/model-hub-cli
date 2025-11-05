from fastapi import FastAPI, Depends
import yaml
from .auth import router as auth_router, verify_token
from .artifact import router as artifact_router
from .model import router as model_router
from .reset import router as reset_router
from .health import router as health_router
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
import os

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

# Create artifacts directory if it doesn't exist
if not os.path.exists("/tmp/artifacts"):
    os.makedirs("/tmp/artifacts")

# Include routers
app.include_router(auth_router, tags=["authentication"])
app.include_router(health_router, tags=["system"], dependencies=[Depends(verify_token)])
app.include_router(artifact_router, tags=["artifacts"])
app.include_router(model_router, tags=["models"])
app.include_router(reset_router, tags=["system"])


# Add API Key security scheme to OpenAPI docs and apply globally to all endpoints
def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Authorization",
        }
    }
    # Apply security to all paths except /authenticate
    for path, path_item in openapi_schema["paths"].items():
        if not path.endswith("/authenticate"):
            for method in path_item.values():
                method["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[assignment]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
