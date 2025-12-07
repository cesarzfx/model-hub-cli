"""
Tests for artifact storage functions.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.api.artifact_store import (
    ensure_artifact_dir,
    store_artifact,
    get_stored_artifact,
    iter_all_artifacts,
    estimate_artifact_cost_mb,
)


class TestArtifactStore:
    """Tests for artifact storage functions."""

    def test_ensure_artifact_dir_creates_directory(self):
        """Test that ensure_artifact_dir creates the directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                ensure_artifact_dir()
                assert test_dir.exists()
                assert test_dir.is_dir()

    def test_ensure_artifact_dir_idempotent(self):
        """Test that ensure_artifact_dir can be called multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                ensure_artifact_dir()
                ensure_artifact_dir()
                assert test_dir.exists()

    def test_store_artifact_creates_file(self):
        """Test that store_artifact creates a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifact_id = "test123"
                data = {"key": "value", "number": 42}

                store_artifact(artifact_id, data)

                artifact_file = test_dir / f"{artifact_id}.json"
                assert artifact_file.exists()

                with artifact_file.open() as f:
                    stored_data = json.load(f)

                assert stored_data == data

    def test_get_stored_artifact_returns_data(self):
        """Test that get_stored_artifact returns the stored data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifact_id = "test123"
                data = {"metadata": {"id": "123", "type": "model"}}

                store_artifact(artifact_id, data)
                retrieved = get_stored_artifact(artifact_id)

                assert retrieved == data

    def test_get_stored_artifact_nonexistent(self):
        """Test that get_stored_artifact returns None for nonexistent artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                retrieved = get_stored_artifact("nonexistent")
                assert retrieved is None

    def test_get_stored_artifact_invalid_json(self):
        """Test that get_stored_artifact handles invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()

            # Create invalid JSON file
            artifact_file = test_dir / "invalid.json"
            artifact_file.write_text("{ invalid json")

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                retrieved = get_stored_artifact("invalid")
                assert retrieved is None

    def test_get_stored_artifact_non_dict(self):
        """Test that get_stored_artifact returns None for non-dict data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()

            # Create file with non-dict data
            artifact_file = test_dir / "array.json"
            artifact_file.write_text("[1, 2, 3]")

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                retrieved = get_stored_artifact("array")
                assert retrieved is None

    def test_iter_all_artifacts_empty_directory(self):
        """Test that iter_all_artifacts returns empty list for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifacts = iter_all_artifacts()
                assert artifacts == []

    def test_iter_all_artifacts_nonexistent_directory(self):
        """Test that iter_all_artifacts returns empty list for nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "nonexistent"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifacts = iter_all_artifacts()
                assert artifacts == []

    def test_iter_all_artifacts_returns_all(self):
        """Test that iter_all_artifacts returns all stored artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                # Store multiple artifacts
                data1 = {"metadata": {"id": "1", "type": "model"}}
                data2 = {"metadata": {"id": "2", "type": "dataset"}}
                data3 = {"metadata": {"id": "3", "type": "model"}}

                store_artifact("artifact1", data1)
                store_artifact("artifact2", data2)
                store_artifact("artifact3", data3)

                artifacts = iter_all_artifacts()

                assert len(artifacts) == 3
                assert data1 in artifacts
                assert data2 in artifacts
                assert data3 in artifacts

    def test_iter_all_artifacts_ignores_non_json(self):
        """Test that iter_all_artifacts ignores non-JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()

            # Create JSON and non-JSON files
            (test_dir / "valid.json").write_text('{"metadata": {"id": "1"}}')
            (test_dir / "readme.txt").write_text("This is a readme")
            (test_dir / "script.py").write_text("print('hello')")

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifacts = iter_all_artifacts()
                assert len(artifacts) == 1

    def test_iter_all_artifacts_skips_invalid_metadata(self):
        """Test that iter_all_artifacts skips artifacts with invalid metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"
            test_dir.mkdir()

            # Valid artifact
            (test_dir / "valid.json").write_text('{"metadata": {"id": "1"}}')

            # Invalid: metadata is not a dict
            (test_dir / "invalid1.json").write_text('{"metadata": "string"}')

            # Invalid: no metadata field
            (test_dir / "invalid2.json").write_text('{"data": {}}')

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifacts = iter_all_artifacts()
                assert len(artifacts) == 1

    def test_estimate_artifact_cost_mb_basic(self):
        """Test artifact cost estimation."""
        artifact = {"data": {"url": "https://example.com/model.bin"}}

        cost = estimate_artifact_cost_mb(artifact)
        assert isinstance(cost, float)
        assert cost > 0

    def test_estimate_artifact_cost_mb_longer_url(self):
        """Test that longer URLs result in higher cost."""
        artifact1 = {"data": {"url": "short"}}
        artifact2 = {"data": {"url": "a" * 100}}

        cost1 = estimate_artifact_cost_mb(artifact1)
        cost2 = estimate_artifact_cost_mb(artifact2)

        assert cost2 > cost1

    def test_estimate_artifact_cost_mb_non_string_url(self):
        """Test cost estimation with non-string URL."""
        artifact = {"data": {"url": 12345}}

        # Should convert to string and calculate
        cost = estimate_artifact_cost_mb(artifact)
        assert isinstance(cost, float)
        assert cost > 0

    def test_estimate_artifact_cost_mb_missing_url(self):
        """Test cost estimation with missing URL."""
        artifact = {"data": {}}

        cost = estimate_artifact_cost_mb(artifact)
        assert isinstance(cost, float)
        # Empty string length is 0, but we take max with 1
        assert cost == 0.1  # max(0, 1) / 10.0

    def test_store_and_retrieve_complex_data(self):
        """Test storing and retrieving complex nested data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "artifacts"

            with patch("src.api.artifact_store.ARTIFACTS_DIR", test_dir):
                artifact_id = "complex"
                data = {
                    "metadata": {
                        "id": "123",
                        "type": "model",
                        "nested": {"key": "value", "list": [1, 2, 3]},
                    },
                    "data": {"url": "https://example.com", "size": 1024},
                }

                store_artifact(artifact_id, data)
                retrieved = get_stored_artifact(artifact_id)

                assert retrieved == data
                assert retrieved["metadata"]["nested"]["key"] == "value"
                assert retrieved["data"]["size"] == 1024
