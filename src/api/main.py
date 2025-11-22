from fastapi import FastAPI
import yaml
from .artifact_routes import router as artifact_router
from .model import router as model_router
from .reset import router as reset_router
from .health import router as health_router
from .auth import router as auth_router
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
app.include_router(health_router, tags=["system"])
app.include_router(auth_router, tags=["auth"])
app.include_router(artifact_router, tags=["artifacts"])
app.include_router(model_router, tags=["models"])
app.include_router(reset_router, tags=["system"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
