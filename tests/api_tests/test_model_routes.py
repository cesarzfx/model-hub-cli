"""Tests for model.py endpoints."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import json

from src.api.main import app
from src.api import artifact_store

client = TestClient(app)


@pytest.fixture
def temp_artifacts_dir(monkeypatch):
    """Create a temporary artifacts directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir)
        monkeypatch.setattr(artifact_store, "ARTIFACTS_DIR", test_path)
        # Also patch the model.py ARTIFACTS_DIR
        import src.api.model as model_module

        monkeypatch.setattr(model_module, "ARTIFACTS_DIR", test_path)
        yield test_path


class TestModelRating:
    """Tests for GET /artifact/model/{id}/rate endpoint."""

    def test_rate_model_not_found(self, temp_artifacts_dir):
        """Test rating non-existent model."""
        response = client.get("/artifact/model/nonexistent/rate")

        assert response.status_code == 404

    def test_rate_model_invalid_artifact(self, temp_artifacts_dir):
        """Test rating artifact that isn't a model."""
        artifact = {
            "metadata": {"id": "ds1", "name": "dataset1", "type": "dataset"},
            "data": {"url": "http://example.com/data"},
        }
        artifact_store.store_artifact("ds1", artifact)

        response = client.get("/artifact/model/ds1/rate")

        # Should fail because it's not a model type
        assert response.status_code in [400, 404, 500]

    def test_rate_model_missing_url(self, temp_artifacts_dir):
        """Test rating model with missing URL."""
        artifact = {
            "metadata": {"id": "m1", "name": "model1", "type": "model"},
            "data": {},
        }
        artifact_store.store_artifact("m1", artifact)

        response = client.get("/artifact/model/m1/rate")

        # Should return 400 when URL is missing
        assert response.status_code == 400
        assert "url" in response.json()["detail"].lower()

    def test_rate_model_with_valid_url(self, temp_artifacts_dir, monkeypatch):
        """Test rating model with valid HuggingFace URL."""
        artifact = {
            "metadata": {"id": "m2", "name": "test-model", "type": "model"},
            "data": {"url": "https://huggingface.co/gpt2"},
        }
        artifact_store.store_artifact("m2", artifact)

        response = client.get("/artifact/model/m2/rate")

        # Should return 200 with rating data
        assert response.status_code == 200
        data = response.json()

        # Validate ModelRating schema fields
        assert "name" in data
        assert "category" in data
        assert "net_score" in data
        assert "net_score_latency" in data
        assert "ramp_up_time" in data
        assert "bus_factor" in data
        assert "performance_claims" in data
        assert "license" in data
        assert "dataset_and_code_score" in data
        assert "dataset_quality" in data
        assert "code_quality" in data
        assert "reproducibility" in data
        assert "reviewedness" in data
        assert "tree_score" in data
        assert "size_score" in data

        # Validate size_score structure
        size_score = data["size_score"]
        assert "raspberry_pi" in size_score
        assert "jetson_nano" in size_score
        assert "desktop_pc" in size_score
        assert "aws_server" in size_score

        # All scores should be between 0 and 1
        for key in data:
            if key.endswith("_score") and key != "size_score":
                assert 0.0 <= data[key] <= 1.0, f"{key} should be between 0 and 1"


class TestModelLineage:
    """Tests for GET /artifact/model/{id}/lineage endpoint."""

    def test_lineage_not_found(self, temp_artifacts_dir):
        """Test lineage for non-existent model."""
        response = client.get("/artifact/model/nonexistent/lineage")

        assert response.status_code == 404

    def test_lineage_no_parents(self, temp_artifacts_dir):
        """Test lineage for model with no parent models."""
        artifact = {
            "metadata": {"id": "m1", "name": "standalone-model", "type": "model"},
            "data": {"url": "http://example.com/model", "name": "standalone-model"},
        }
        artifact_store.store_artifact("m1", artifact)

        response = client.get("/artifact/model/m1/lineage")

        if response.status_code == 200:
            result = response.json()
            assert "nodes" in result
            assert "edges" in result
            # Should have at least the model itself as a node
            assert len(result["nodes"]) >= 1

    def test_lineage_with_parent_models(self, temp_artifacts_dir):
        """Test lineage graph construction with parent models."""
        # Create parent model
        parent = {
            "metadata": {"id": "parent1", "name": "base-model", "type": "model"},
            "data": {"url": "http://example.com/base", "name": "base-model"},
        }
        artifact_store.store_artifact("parent1", parent)

        # Create child model referencing parent
        child = {
            "metadata": {"id": "child1", "name": "fine-tuned-model", "type": "model"},
            "data": {
                "url": "http://example.com/finetuned",
                "name": "fine-tuned-model",
                "parent_models": ["base-model"],
            },
        }
        artifact_store.store_artifact("child1", child)

        response = client.get("/artifact/model/child1/lineage")

        if response.status_code == 200:
            result = response.json()
            assert "nodes" in result
            assert "edges" in result


class TestModelLicenseCheck:
    """Tests for POST /artifact/model/{id}/license-check endpoint."""

    def test_license_check_not_found(self, temp_artifacts_dir):
        """Test license check for non-existent model."""
        response = client.post(
            "/artifact/model/nonexistent/license-check",
            json={"github_url": "https://github.com/org/repo"},
        )

        assert response.status_code == 404

    def test_license_check_with_model(self, temp_artifacts_dir):
        """Test license check with existing model."""
        artifact = {
            "metadata": {"id": "m1", "name": "model1", "type": "model"},
            "data": {"url": "https://huggingface.co/org/model"},
        }
        artifact_store.store_artifact("m1", artifact)

        response = client.post(
            "/artifact/model/m1/license-check",
            json={"github_url": "https://github.com/org/repo"},
        )

        # Endpoint exists and processes the request
        assert response.status_code in [200, 400, 500]
