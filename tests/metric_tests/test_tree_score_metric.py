"""
Tests for TreeScoreMetric.

This module tests the TreeScoreMetric's ability to:
1. Extract parent model information from HuggingFace metadata
2. Search the artifact store for parent models
3. Calculate average NetScores from parent models
4. Handle edge cases (no parents, missing scores, etc.)
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from loguru import logger

from src.metrics.TreeScoreMetric import TreeScoreMetric
from tests.conftest import StubModelData


@pytest.fixture
def temp_artifacts_dir(monkeypatch):
    """Create a temporary artifacts directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ARTIFACTS_DIR", tmpdir)
        yield Path(tmpdir)


@pytest.fixture
def metric(temp_artifacts_dir):
    """Create a TreeScoreMetric instance with temporary artifacts directory."""
    return TreeScoreMetric()


def create_artifact_file(
    artifacts_dir: Path,
    artifact_id: str,
    name: str,
    net_score: float,
    artifact_type: str = "model",
) -> None:
    """
    Helper function to create a mock artifact file in the artifacts directory.

    Args:
        artifacts_dir: Path to the artifacts directory
        artifact_id: Unique identifier for the artifact
        name: Name of the model/artifact
        net_score: NetScore value for the artifact
        artifact_type: Type of artifact (default: "model")
    """
    artifact_data = {
        "metadata": {
            "id": artifact_id,
            "name": name,
            "type": artifact_type,
        },
        "metadata_json": {
            "net_score": net_score,
        },
    }

    filepath = artifacts_dir / f"{artifact_id}.json"
    with filepath.open("w") as f:
        json.dump(artifact_data, f)


class TestTreeScoreMetricBasic:
    """Basic functionality tests for TreeScoreMetric."""

    def test_metric_instantiation(self, metric):
        """Test that the metric can be instantiated."""
        assert metric is not None
        assert isinstance(metric.artifacts_dir, Path)

    def test_no_parent_models_returns_zero(self, metric):
        """Test that models without parent information return 0.0."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {}

        score = metric.evaluate(model)
        assert score == 0.0

    def test_no_hf_metadata_returns_zero(self, metric):
        """Test that models without HF metadata return 0.0."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = None

        score = metric.evaluate(model)
        assert score == 0.0


class TestParentModelExtraction:
    """Tests for extracting parent model information from metadata."""

    def test_extract_from_carddata_base_model_string(self, metric):
        """Test extraction of base_model from cardData (string format)."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"cardData": {"base_model": "parent-org/parent-model"}}

        parent_names = metric._extract_parent_models(model)
        assert "parent-org/parent-model" in parent_names

    def test_extract_from_carddata_base_model_list(self, metric):
        """Test extraction of base_model from cardData (list format)."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {
            "cardData": {"base_model": ["parent1/model1", "parent2/model2"]}
        }

        parent_names = metric._extract_parent_models(model)
        assert "parent1/model1" in parent_names
        assert "parent2/model2" in parent_names

    def test_extract_from_top_level_base_model(self, metric):
        """Test extraction of base_model from top-level metadata."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"base_model": "parent-org/parent-model"}

        parent_names = metric._extract_parent_models(model)
        assert "parent-org/parent-model" in parent_names

    def test_extract_from_model_index(self, metric):
        """Test extraction of parent from model_index JSON."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model_index_data = {
            "base_model": "parent-org/parent-model",
            "parent_model": "another-parent/model",
        }
        model.hf_metadata = {"model_index": json.dumps(model_index_data)}

        parent_names = metric._extract_parent_models(model)
        assert "parent-org/parent-model" in parent_names
        assert "another-parent/model" in parent_names

    def test_extract_handles_invalid_model_index(self, metric):
        """Test that invalid model_index JSON is handled gracefully."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {
            "model_index": "invalid json {{{",
            "cardData": {"base_model": "valid-parent/model"},
        }

        parent_names = metric._extract_parent_models(model)
        # Should still get the valid parent from cardData
        assert "valid-parent/model" in parent_names

    def test_extract_deduplicates_parents(self, metric):
        """Test that duplicate parent names are deduplicated."""
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {
            "cardData": {"base_model": "parent-org/parent-model"},
            "base_model": "parent-org/parent-model",
        }

        parent_names = metric._extract_parent_models(model)
        assert parent_names.count("parent-org/parent-model") == 1


class TestParentScoreRetrieval:
    """Tests for retrieving parent scores from artifact store."""

    def test_retrieve_single_parent_score(self, metric, temp_artifacts_dir):
        """Test retrieving score for a single parent model."""
        create_artifact_file(temp_artifacts_dir, "parent1", "parent-model", 0.85)

        parent_scores = metric._get_parent_scores(["parent-model"])
        assert len(parent_scores) == 1
        assert parent_scores[0] == 0.85

    def test_retrieve_multiple_parent_scores(self, metric, temp_artifacts_dir):
        """Test retrieving scores for multiple parent models."""
        create_artifact_file(temp_artifacts_dir, "parent1", "parent-model-1", 0.85)
        create_artifact_file(temp_artifacts_dir, "parent2", "parent-model-2", 0.75)

        parent_scores = metric._get_parent_scores(["parent-model-1", "parent-model-2"])
        assert len(parent_scores) == 2
        assert 0.85 in parent_scores
        assert 0.75 in parent_scores

    def test_ignore_zero_scores(self, metric, temp_artifacts_dir):
        """Test that zero scores are ignored."""
        create_artifact_file(temp_artifacts_dir, "parent1", "parent-model-1", 0.0)
        create_artifact_file(temp_artifacts_dir, "parent2", "parent-model-2", 0.75)

        parent_scores = metric._get_parent_scores(["parent-model-1", "parent-model-2"])
        assert len(parent_scores) == 1
        assert parent_scores[0] == 0.75

    def test_ignore_non_model_artifacts(self, metric, temp_artifacts_dir):
        """Test that non-model artifacts are ignored."""
        create_artifact_file(
            temp_artifacts_dir,
            "dataset1",
            "parent-model",
            0.85,
            artifact_type="dataset",
        )

        parent_scores = metric._get_parent_scores(["parent-model"])
        assert len(parent_scores) == 0

    def test_handle_string_metadata_json(self, metric, temp_artifacts_dir):
        """Test handling metadata_json as a JSON string."""
        artifact_data = {
            "metadata": {
                "id": "parent1",
                "name": "parent-model",
                "type": "model",
            },
            "metadata_json": json.dumps({"net_score": 0.90}),
        }

        filepath = temp_artifacts_dir / "parent1.json"
        with filepath.open("w") as f:
            json.dump(artifact_data, f)

        parent_scores = metric._get_parent_scores(["parent-model"])
        assert len(parent_scores) == 1
        assert parent_scores[0] == 0.90

    def test_handle_malformed_artifact_files(self, metric, temp_artifacts_dir):
        """Test that malformed artifact files are skipped gracefully."""
        # Create a malformed JSON file
        filepath = temp_artifacts_dir / "malformed.json"
        with filepath.open("w") as f:
            f.write("{ invalid json")

        # Create a valid artifact
        create_artifact_file(temp_artifacts_dir, "valid", "parent-model", 0.80)

        parent_scores = metric._get_parent_scores(["parent-model"])
        assert len(parent_scores) == 1
        assert parent_scores[0] == 0.80

    def test_nonexistent_artifacts_dir(self, monkeypatch):
        """Test handling of nonexistent artifacts directory."""
        monkeypatch.setenv("ARTIFACTS_DIR", "/nonexistent/directory")
        metric = TreeScoreMetric()

        parent_scores = metric._get_parent_scores(["parent-model"])
        assert len(parent_scores) == 0


class TestParentNameMatching:
    """Tests for parent name matching logic."""

    def test_exact_match(self, metric):
        """Test exact name matching."""
        assert metric._is_parent_match("parent-model", ["parent-model"])

    def test_case_insensitive_match(self, metric):
        """Test case-insensitive matching."""
        assert metric._is_parent_match("Parent-Model", ["parent-model"])
        assert metric._is_parent_match("parent-model", ["Parent-Model"])

    def test_partial_match_parent_in_artifact(self, metric):
        """Test matching when parent name is contained in artifact name."""
        assert metric._is_parent_match("org/parent-model-finetuned", ["parent-model"])

    def test_partial_match_artifact_in_parent(self, metric):
        """Test matching when artifact name is contained in parent name."""
        assert metric._is_parent_match("model", ["org/model"])

    def test_org_model_format_matching(self, metric):
        """Test matching with organization/model format."""
        assert metric._is_parent_match("my-model", ["org/my-model"])
        assert metric._is_parent_match("org/my-model", ["my-model"])
        assert metric._is_parent_match("org1/my-model", ["org2/my-model"])

    def test_no_match(self, metric):
        """Test when names don't match."""
        assert not metric._is_parent_match("model-a", ["model-b"])
        assert not metric._is_parent_match("completely-different", ["parent-model"])


class TestEndToEndEvaluation:
    """End-to-end tests for the complete evaluation workflow."""

    def test_single_parent_evaluation(self, metric, temp_artifacts_dir):
        """Test evaluation with a single parent model."""
        create_artifact_file(temp_artifacts_dir, "parent1", "bert-base", 0.80)

        model = StubModelData(
            modelLink="https://huggingface.co/org/bert-finetuned",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"cardData": {"base_model": "bert-base"}}

        score = metric.evaluate(model)
        assert score == 0.80

    def test_multiple_parents_average(self, metric, temp_artifacts_dir):
        """Test evaluation with multiple parent models returns average."""
        create_artifact_file(temp_artifacts_dir, "parent1", "model-a", 0.80)
        create_artifact_file(temp_artifacts_dir, "parent2", "model-b", 0.60)

        model = StubModelData(
            modelLink="https://huggingface.co/org/combined-model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"cardData": {"base_model": ["model-a", "model-b"]}}

        score = metric.evaluate(model)
        assert score == 0.70  # (0.80 + 0.60) / 2

    def test_parent_not_in_store_returns_zero(self, metric, temp_artifacts_dir):
        """Test that missing parent models result in 0.0 score."""
        # Artifacts dir exists but doesn't contain the parent
        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"cardData": {"base_model": "nonexistent-parent"}}

        score = metric.evaluate(model)
        assert score == 0.0

    def test_score_rounding(self, metric, temp_artifacts_dir):
        """Test that scores are properly rounded to 2 decimal places."""
        create_artifact_file(temp_artifacts_dir, "parent1", "model-a", 0.333333)
        create_artifact_file(temp_artifacts_dir, "parent2", "model-b", 0.666666)

        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"cardData": {"base_model": ["model-a", "model-b"]}}

        score = metric.evaluate(model)
        # Average is 0.499999, should round to 0.50
        assert score == 0.50

    def test_complex_parent_hierarchy(self, metric, temp_artifacts_dir):
        """Test with complex parent model naming (org/model format)."""
        create_artifact_file(temp_artifacts_dir, "parent1", "facebook/bart-base", 0.85)
        create_artifact_file(temp_artifacts_dir, "parent2", "google/t5-small", 0.75)

        model = StubModelData(
            modelLink="https://huggingface.co/org/my-model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {
            "cardData": {"base_model": "facebook/bart-base"},
            "base_model": "google/t5-small",
        }

        score = metric.evaluate(model)
        assert score == 0.80  # (0.85 + 0.75) / 2

    def test_evaluation_with_perfect_parent(self, metric, temp_artifacts_dir):
        """Test evaluation when parent has perfect score."""
        create_artifact_file(temp_artifacts_dir, "parent1", "perfect-model", 1.0)

        model = StubModelData(
            modelLink="https://huggingface.co/org/derived-model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"base_model": "perfect-model"}

        score = metric.evaluate(model)
        assert score == 1.0

    def test_evaluation_with_negative_score_ignored(self, metric, temp_artifacts_dir):
        """Test that negative scores are ignored (treated as invalid)."""
        create_artifact_file(temp_artifacts_dir, "parent1", "bad-model", -0.5)
        create_artifact_file(temp_artifacts_dir, "parent2", "good-model", 0.8)

        model = StubModelData(
            modelLink="https://huggingface.co/org/model",
            codeLink=None,
            datasetLink=None,
        )
        model.hf_metadata = {"cardData": {"base_model": ["bad-model", "good-model"]}}

        score = metric.evaluate(model)
        # Only good-model score should be used
        assert score == 0.80
