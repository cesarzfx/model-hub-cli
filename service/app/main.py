from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from .api.v1 import packages, ingest, rate, lineage, license as license_api, admin, health, auth
from .core.database import init_db

def create_app() -> FastAPI:
    app = FastAPI(title="Trustworthy Model Registry", version="1.0.0")
    
    # Add CORS middleware to allow frontend requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8080"],  # Frontend dev server and backend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize database on startup
    @app.on_event("startup")
    def startup_event():
        init_db()
    
    # API routes - must come before static file serving
    app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(packages.router, prefix="/v1/packages", tags=["packages"])
    app.include_router(ingest.router, prefix="/v1/ingest", tags=["ingest"])
    app.include_router(rate.router, prefix="/v1/rate", tags=["rate"])
    app.include_router(lineage.router, prefix="/v1/lineage", tags=["lineage"])
    app.include_router(license_api.router, prefix="/v1/license", tags=["license"])
    app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
    app.include_router(health.router, prefix="/v1/health", tags=["health"])
    
    # Serve frontend static files
    # In container: /app/frontend/dist, locally: service/frontend/dist
    frontend_build_path = Path("/app/frontend/dist")
    if not frontend_build_path.exists():
        # Fallback for local development
        frontend_build_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Frontend build path: {frontend_build_path}, exists: {frontend_build_path.exists()}")
    
    if frontend_build_path.exists():
        # Mount static assets directory
        static_assets_path = frontend_build_path / "assets"
        if static_assets_path.exists():
            app.mount("/assets", StaticFiles(directory=str(static_assets_path)), name="assets")
        
        # Serve index.html for all non-API routes (for client-side routing)
        # This must be last to catch all routes not handled above
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            # Don't serve frontend for API routes or static assets
            if full_path.startswith("v1/") or full_path.startswith("api/") or full_path.startswith("assets/"):
                raise HTTPException(status_code=404, detail="Not found")
            
            # Try to serve the file if it exists (for direct file access)
            file_path = frontend_build_path / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            
            # Otherwise serve index.html for client-side routing
            index_path = frontend_build_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            
            raise HTTPException(status_code=404, detail="Frontend not built")
    
    return app

app = create_app()
