import logging
import re
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from . import deps
from .api.v1 import admin, auth, health, ingest, license as license_api, lineage, packages, rate, tracks
from .core.database import init_db


class NormalizePathMiddleware(BaseHTTPMiddleware):
    """Collapse repeated slashes so //tracks maps to /tracks."""

    async def dispatch(self, request, call_next):
        scope = request.scope
        original_path = scope.get("path", "")
        normalized_path = re.sub(r"/{2,}", "/", original_path)
        if normalized_path != original_path:
            logging.getLogger(__name__).debug(
                "Normalizing path from %s to %s", original_path, normalized_path
            )
            scope["path"] = normalized_path
        return await call_next(request)

def create_app() -> FastAPI:
    app = FastAPI(title="Trustworthy Model Registry", version="1.0.0")
    
    # Add CORS middleware to allow frontend requests
    # Allow all origins when deployed (frontend served from same domain), or specific origins for local dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins - frontend is served from same domain when deployed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(NormalizePathMiddleware)
    
    # Initialize database on startup
    @app.on_event("startup")
    def startup_event():
        init_db()
        # Ensure admin user exists on startup
        try:
            from .api.v1.admin import bootstrap
            from .domain import repos
            repo = repos.get_repo()
            # Call bootstrap to ensure admin user exists
            bootstrap(repo=repo)
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Admin user bootstrap completed on startup")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to bootstrap admin user on startup: {e}")
    
    # API routes - must come before static file serving
    app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(packages.router, prefix="/v1/packages", tags=["packages"])
    app.include_router(ingest.router, prefix="/v1/ingest", tags=["ingest"])
    app.include_router(rate.router, prefix="/v1/rate", tags=["rate"])
    app.include_router(lineage.router, prefix="/v1/lineage", tags=["lineage"])
    app.include_router(license_api.router, prefix="/v1/license", tags=["license"])
    app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
    app.include_router(health.router, prefix="/v1/health", tags=["health"])
    app.include_router(tracks.router, prefix="/v1/tracks", tags=["tracks"])
    
    # Also expose tracks at root level for autograder compatibility (before frontend catch-all)
    from .api.v1.tracks import get_tracks, TracksResponse
    @app.get("/tracks", response_model=TracksResponse, tags=["tracks"])
    async def tracks_root():
        """Root-level tracks endpoint for autograder compatibility"""
        result = get_tracks()
        # Return the Pydantic model directly - FastAPI will serialize it to JSON
        return result
    
    # Also handle trailing slash for autograder compatibility
    @app.get("/tracks/", response_model=TracksResponse, tags=["tracks"])
    async def tracks_root_slash():
        """Root-level tracks endpoint with trailing slash"""
        result = get_tracks()
        return result

    @app.post("/reset", tags=["admin"])
    @app.delete("/reset", tags=["admin"])
    async def reset_root(repo=Depends(deps.get_repo), user=Depends(deps.require_admin)):
        """Root-level reset endpoint for autograder compatibility."""
        return admin.reset(repo=repo, user=user)

    @app.head("/tracks", tags=["tracks"])
    @app.head("/tracks/", tags=["tracks"])
    async def tracks_head():
        """Allow head requests so health checks/autograders do not see 405 responses."""
        return Response(status_code=200)
    
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
            normalized = full_path.lstrip("/")
            # Don't serve frontend for API routes or static assets
            if (
                normalized.startswith("v1/")
                or normalized.startswith("api/")
                or normalized.startswith("assets/")
                or normalized == "tracks"
                or normalized.startswith("tracks/")
            ):
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
