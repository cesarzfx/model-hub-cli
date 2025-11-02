
from fastapi import FastAPI
import yaml
from src.api.auth import router as auth_router
from src.api.artifact import router as artifact_router
from src.api.model import router as model_router
from src.api.reset import router as reset_router
from fastapi.openapi.utils import get_openapi

# Load the OpenAPI spec
with open('ece461_fall_2025_openapi_spec.yaml', 'r') as f:
    openapi_spec = yaml.safe_load(f)

app = FastAPI(
    title=openapi_spec['info']['title'],
    description=openapi_spec['info']['description'],
    version=openapi_spec['info']['version']
)

app.include_router(auth_router)
app.include_router(artifact_router)
app.include_router(model_router)
app.include_router(reset_router)


# Add API Key security scheme to OpenAPI docs and apply globally to all endpoints
def custom_openapi():
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
            "name": "X-Authorization"
        }
    }
    # Apply security to all paths
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)