from fastapi import FastAPI
from .api.v1 import packages, ingest, rate, lineage, license as license_api, admin, health, auth

def create_app() -> FastAPI:
    app = FastAPI(title="Trustworthy Model Registry", version="1.0.0")
    app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(packages.router, prefix="/v1/packages", tags=["packages"])
    app.include_router(ingest.router, prefix="/v1/ingest", tags=["ingest"])
    app.include_router(rate.router, prefix="/v1/rate", tags=["rate"])
    app.include_router(lineage.router, prefix="/v1/lineage", tags=["lineage"])
    app.include_router(license_api.router, prefix="/v1/license", tags=["license"])
    app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
    app.include_router(health.router, prefix="/v1/health", tags=["health"])
    return app

app = create_app()
