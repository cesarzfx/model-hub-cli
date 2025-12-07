"""
Tests for health check endpoint.
"""

from fastapi.testclient import TestClient
from src.api.health import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self):
        """Test that health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        """Test that health endpoint returns description."""
        response = client.get("/health")
        data = response.json()

        assert "description" in data
        assert data["description"] == "Service reachable."

    def test_health_returns_dict(self):
        """Test that health endpoint returns a dictionary."""
        response = client.get("/health")
        data = response.json()
        
        assert isinstance(data, dict)


class TestTracksEndpoint:
    """Tests for /tracks endpoint."""

    def test_tracks_returns_200(self):
        """Test that tracks endpoint returns 200."""
        response = client.get("/tracks")
        
        assert response.status_code == 200

    def test_tracks_returns_planned_tracks(self):
        """Test that tracks endpoint returns plannedTracks."""
        response = client.get("/tracks")
        data = response.json()
        
        assert "plannedTracks" in data
        assert isinstance(data["plannedTracks"], list)

    def test_tracks_contains_access_control(self):
        """Test that tracks includes Access control track."""
        response = client.get("/tracks")
        data = response.json()
        
        assert "Access control track" in data["plannedTracks"]
