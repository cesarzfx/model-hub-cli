"""
Tests for artifact schema models.
"""

import pytest
from pydantic import ValidationError

from src.api.artifact_schemas import (
    ArtifactMetadata,
    ArtifactData,
    Artifact,
    ArtifactQuery,
    ArtifactRegEx,
    ArtifactCostEntry,
    VALID_TYPES,
    ARTIFACT_ID_PATTERN,
)


class TestArtifactMetadata:
    """Tests for ArtifactMetadata model."""

    def test_artifact_metadata_valid(self):
        """Test creating valid ArtifactMetadata."""
        metadata = ArtifactMetadata(id="test123", name="test-artifact", type="model")

        assert metadata.id == "test123"
        assert metadata.name == "test-artifact"
        assert metadata.type == "model"

    def test_artifact_metadata_requires_id(self):
        """Test that id is required."""
        with pytest.raises(ValidationError):
            ArtifactMetadata(name="test", type="model")

    def test_artifact_metadata_requires_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            ArtifactMetadata(id="123", type="model")

    def test_artifact_metadata_requires_type(self):
        """Test that type is required."""
        with pytest.raises(ValidationError):
            ArtifactMetadata(id="123", name="test")


class TestArtifactData:
    """Tests for ArtifactData model."""

    def test_artifact_data_valid(self):
        """Test creating valid ArtifactData."""
        data = ArtifactData(url="https://example.com/model.bin")
        assert data.url == "https://example.com/model.bin"

    def test_artifact_data_requires_url(self):
        """Test that url is required."""
        with pytest.raises(ValidationError):
            ArtifactData()


class TestArtifact:
    """Tests for Artifact model."""

    def test_artifact_valid(self):
        """Test creating valid Artifact."""
        metadata = ArtifactMetadata(id="123", name="test", type="model")
        data = ArtifactData(url="https://example.com/model.bin")

        artifact = Artifact(metadata=metadata, data=data)

        assert artifact.metadata.id == "123"
        assert artifact.data.url == "https://example.com/model.bin"

    def test_artifact_requires_metadata(self):
        """Test that metadata is required."""
        data = ArtifactData(url="https://example.com/model.bin")

        with pytest.raises(ValidationError):
            Artifact(data=data)

    def test_artifact_requires_data(self):
        """Test that data is required."""
        metadata = ArtifactMetadata(id="123", name="test", type="model")

        with pytest.raises(ValidationError):
            Artifact(metadata=metadata)


class TestArtifactQuery:
    """Tests for ArtifactQuery model."""

    def test_artifact_query_valid(self):
        """Test creating valid ArtifactQuery."""
        query = ArtifactQuery(name="test-model", types=["model"])

        assert query.name == "test-model"
        assert query.types == ["model"]

    def test_artifact_query_requires_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            ArtifactQuery(types=["model"])

    def test_artifact_query_optional_types(self):
        """Test that types is optional."""
        query = ArtifactQuery(name="test")
        assert query.name == "test"
        assert query.types is None

    def test_artifact_query_wildcard_name(self):
        """Test query with wildcard name."""
        query = ArtifactQuery(name="*")
        assert query.name == "*"


class TestArtifactRegEx:
    """Tests for ArtifactRegEx model."""

    def test_artifact_regex_valid(self):
        """Test creating valid ArtifactRegEx."""
        regex = ArtifactRegEx(regex="test.*")
        assert regex.regex == "test.*"

    def test_artifact_regex_requires_regex(self):
        """Test that regex is required."""
        with pytest.raises(ValidationError):
            ArtifactRegEx()


class TestArtifactCostEntry:
    """Tests for ArtifactCostEntry model."""

    def test_artifact_cost_entry_valid(self):
        """Test creating valid ArtifactCostEntry."""
        cost = ArtifactCostEntry(standalone_cost=5.0, total_cost=10.5)

        assert cost.standalone_cost == 5.0
        assert cost.total_cost == 10.5

    def test_artifact_cost_entry_requires_total_cost_field(self):
        """Test that total_cost is required."""
        with pytest.raises(ValidationError):
            ArtifactCostEntry(standalone_cost=5.0)

    def test_artifact_cost_entry_requires_total_cost(self):
        """Test that total_cost is required."""
        with pytest.raises(ValidationError):
            ArtifactCostEntry(id="123")


class TestConstants:
    """Tests for module constants."""

    def test_valid_types_contains_model(self):
        """Test that VALID_TYPES includes 'model'."""
        assert "model" in VALID_TYPES

    def test_valid_types_is_set(self):
        """Test that VALID_TYPES is a set."""
        assert isinstance(VALID_TYPES, set)

    def test_artifact_id_pattern_exists(self):
        """Test that ARTIFACT_ID_PATTERN is defined."""
        assert ARTIFACT_ID_PATTERN is not None
        assert hasattr(ARTIFACT_ID_PATTERN, "pattern")  # It's a compiled regex
