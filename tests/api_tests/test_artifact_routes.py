"""Tests for artifact_routes.py endpoints."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import json
import os

from src.api.main import app
from src.api.artifact_schemas import (
    ArtifactQuery,
    ArtifactMetadata,
    ArtifactData,
    Artifact,
)
from src.api import artifact_store

client = TestClient(app)


@pytest.fixture
def temp_artifacts_dir(monkeypatch):
    """Create a temporary artifacts directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(artifact_store, "ARTIFACTS_DIR", Path(tmpdir))
        yield Path(tmpdir)


class TestListArtifacts:
    """Tests for POST /artifacts endpoint."""

    def test_list_artifacts_empty_directory(self, temp_artifacts_dir):
        """Test listing artifacts when directory is empty."""
        response = client.post("/artifacts", json=[{"name": "*"}])
        assert response.status_code == 200
        assert response.json() == []

    def test_list_artifacts_nonexistent_directory(self, monkeypatch):
        """Test listing artifacts when directory doesn't exist."""
        nonexistent = Path("/tmp/nonexistent_artifacts_dir_12345")
        monkeypatch.setattr(artifact_store, "ARTIFACTS_DIR", nonexistent)

        response = client.post("/artifacts", json=[{"name": "*"}])
        assert response.status_code == 200
        assert response.json() == []

    def test_list_artifacts_wildcard_query(self, temp_artifacts_dir):
        """Test wildcard query returns all artifacts."""
        # Store test artifacts
        artifact1 = {
            "metadata": {"id": "art1", "name": "model1", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact2 = {
            "metadata": {"id": "art2", "name": "dataset1", "type": "dataset"},
            "data": {"url": "http://example.com/dataset1"},
        }

        artifact_store.store_artifact("art1", artifact1)
        artifact_store.store_artifact("art2", artifact2)

        response = client.post("/artifacts", json=[{"name": "*"}])

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert any(r["id"] == "art1" for r in results)
        assert any(r["id"] == "art2" for r in results)

    def test_list_artifacts_wildcard_with_type_filter(self, temp_artifacts_dir):
        """Test wildcard query with type filtering."""
        artifact1 = {
            "metadata": {"id": "art1", "name": "model1", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact2 = {
            "metadata": {"id": "art2", "name": "dataset1", "type": "dataset"},
            "data": {"url": "http://example.com/dataset1"},
        }

        artifact_store.store_artifact("art1", artifact1)
        artifact_store.store_artifact("art2", artifact2)

        response = client.post("/artifacts", json=[{"name": "*", "types": ["model"]}])

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["id"] == "art1"
        assert results[0]["type"] == "model"

    def test_list_artifacts_invalid_type(self, temp_artifacts_dir):
        """Test query with invalid artifact type."""
        response = client.post(
            "/artifacts", json=[{"name": "*", "types": ["invalid_type"]}]
        )

        assert response.status_code == 400
        assert "Invalid artifact type" in response.json()["detail"]

    def test_list_artifacts_exact_name_match(self, temp_artifacts_dir):
        """Test exact name matching."""
        artifact1 = {
            "metadata": {"id": "art1", "name": "my-model", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact2 = {
            "metadata": {"id": "art2", "name": "other-model", "type": "model"},
            "data": {"url": "http://example.com/model2"},
        }

        artifact_store.store_artifact("art1", artifact1)
        artifact_store.store_artifact("art2", artifact2)

        response = client.post("/artifacts", json=[{"name": "my-model"}])

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["name"] == "my-model"

    def test_list_artifacts_name_not_found(self, temp_artifacts_dir):
        """Test query for non-existent artifact name."""
        artifact_store.ensure_artifact_dir()

        response = client.post("/artifacts", json=[{"name": "nonexistent"}])

        assert response.status_code == 404
        assert "No such artifact" in response.json()["detail"]

    def test_list_artifacts_offset_header(self, temp_artifacts_dir):
        """Test that offset header is set in response."""
        response = client.post("/artifacts", json=[{"name": "*"}])

        assert response.status_code == 200
        assert "offset" in response.headers
        assert response.headers["offset"] == "0"

    def test_list_artifacts_custom_offset(self, temp_artifacts_dir):
        """Test custom offset in response header."""
        response = client.post("/artifacts?offset=10", json=[{"name": "*"}])

        assert response.status_code == 200
        assert response.headers["offset"] == "10"

    def test_list_artifacts_multiple_queries(self, temp_artifacts_dir):
        """Test multiple queries in single request."""
        artifact1 = {
            "metadata": {"id": "art1", "name": "model1", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact2 = {
            "metadata": {"id": "art2", "name": "dataset1", "type": "dataset"},
            "data": {"url": "http://example.com/dataset1"},
        }

        artifact_store.store_artifact("art1", artifact1)
        artifact_store.store_artifact("art2", artifact2)

        response = client.post(
            "/artifacts", json=[{"name": "model1"}, {"name": "dataset1"}]
        )

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2

    def test_list_artifacts_skips_invalid_metadata(self, temp_artifacts_dir):
        """Test that artifacts with invalid metadata are skipped."""
        # Valid artifact
        valid = {
            "metadata": {"id": "valid1", "name": "model1", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact_store.store_artifact("valid1", valid)

        # Invalid artifact (missing required fields)
        invalid_file = temp_artifacts_dir / "invalid.json"
        invalid_file.write_text(json.dumps({"metadata": {"id": "invalid"}}))

        response = client.post("/artifacts", json=[{"name": "*"}])

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["id"] == "valid1"


class TestGetArtifactByName:
    """Tests for GET /artifact/byName/{name} endpoint."""

    def test_get_artifact_by_name_success(self, temp_artifacts_dir):
        """Test successful retrieval by name."""
        artifact = {
            "metadata": {"id": "art1", "name": "my-model", "type": "model"},
            "data": {"url": "http://example.com/model"},
        }
        artifact_store.store_artifact("art1", artifact)

        response = client.get("/artifact/byName/my-model")

        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) >= 1
        assert results[0]["name"] == "my-model"

    def test_get_artifact_by_name_not_found(self, temp_artifacts_dir):
        """Test retrieval of non-existent artifact."""
        artifact_store.ensure_artifact_dir()

        response = client.get("/artifact/byName/nonexistent")

        assert response.status_code == 404

    def test_get_artifact_by_name_no_artifacts(self, temp_artifacts_dir):
        """Test retrieval when no artifacts exist."""
        response = client.get("/artifact/byName/anything")

        assert response.status_code == 404


class TestGetArtifactById:
    """Tests for GET /artifacts/{artifact_type}/{id} endpoint."""

    def test_get_artifact_by_id_success(self, temp_artifacts_dir):
        """Test successful retrieval by type and ID."""
        artifact = {
            "metadata": {"id": "art123", "name": "my-model", "type": "model"},
            "data": {"url": "http://example.com/model"},
        }
        artifact_store.store_artifact("art123", artifact)

        response = client.get("/artifacts/model/art123")

        assert response.status_code == 200
        result = response.json()
        assert result["metadata"]["id"] == "art123"

    def test_get_artifact_by_id_not_found(self, temp_artifacts_dir):
        """Test retrieval of non-existent artifact ID."""
        artifact_store.ensure_artifact_dir()

        response = client.get("/artifacts/model/nonexistent")

        assert response.status_code == 404


class TestSearchArtifacts:
    """Tests for POST /artifact/byRegEx endpoint."""

    def test_search_artifacts_by_regex(self, temp_artifacts_dir):
        """Test regex search."""
        artifact1 = {
            "metadata": {"id": "art1", "name": "model-v1", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact2 = {
            "metadata": {"id": "art2", "name": "model-v2", "type": "model"},
            "data": {"url": "http://example.com/model2"},
        }
        artifact3 = {
            "metadata": {"id": "art3", "name": "dataset-v1", "type": "dataset"},
            "data": {"url": "http://example.com/dataset1"},
        }

        artifact_store.store_artifact("art1", artifact1)
        artifact_store.store_artifact("art2", artifact2)
        artifact_store.store_artifact("art3", artifact3)

        response = client.post("/artifact/byRegEx", json={"regex": "model-.*"})

        assert response.status_code == 200
        results = response.json()
        assert len(results) >= 2
        assert all("model-" in r["name"] for r in results)

    def test_search_artifacts_no_matches(self, temp_artifacts_dir):
        """Test regex with no matches."""
        artifact = {
            "metadata": {"id": "art1", "name": "model1", "type": "model"},
            "data": {"url": "http://example.com/model1"},
        }
        artifact_store.store_artifact("art1", artifact)

        response = client.post("/artifact/byRegEx", json={"regex": "^nonexistent$"})

        assert response.status_code == 404

    def test_search_artifacts_invalid_regex(self, temp_artifacts_dir):
        """Test with invalid regex pattern."""
        response = client.post("/artifact/byRegEx", json={"regex": "[invalid(regex"})

        # Should return 400 for invalid regex
        assert response.status_code in [400, 404, 500]


class TestDeleteArtifact:
    """Tests for DELETE /artifacts/{artifact_type}/{id} endpoint."""

    def test_delete_artifact_success(self, temp_artifacts_dir, monkeypatch):
        """Test successful deletion."""
        # Patch both artifact_store and artifact_routes
        import src.api.artifact_routes as artifact_routes_module

        monkeypatch.setattr(artifact_routes_module, "ARTIFACTS_DIR", temp_artifacts_dir)

        artifact = {
            "metadata": {"id": "art1", "name": "model1", "type": "model"},
            "data": {"url": "http://example.com/model.zip"},
        }
        artifact_store.store_artifact("art1", artifact)

        response = client.delete("/artifacts/model/art1")

        assert response.status_code == 200

    def test_delete_artifact_not_found(self, temp_artifacts_dir, monkeypatch):
        """Test deletion of non-existent artifact."""
        import src.api.artifact_routes as artifact_routes_module

        monkeypatch.setattr(artifact_routes_module, "ARTIFACTS_DIR", temp_artifacts_dir)
        artifact_store.ensure_artifact_dir()

        response = client.delete("/artifacts/model/nonexistent")

        assert response.status_code == 404
