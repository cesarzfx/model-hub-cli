import pytest
import os
from unittest.mock import Mock, patch
from typing import Iterator
from src.metrics.DatasetQualityMetric import DatasetQualityMetric


class TestDatasetQualityMetric:

    @pytest.fixture
    def metric(self) -> DatasetQualityMetric:
        with patch.dict(os.environ, {"GEN_AI_STUDIO_API_KEY": "test-api-key"}):
            return DatasetQualityMetric()

    @pytest.fixture
    def model_with_dataset_metadata(
        self, base_model
    ):  # base_model type comes from conftest
        base_model._dataset_metadata = {
            "id": "test/dataset",
            "description": "A test dataset",
            "downloads": 1000,
            "likes": 50,
            "siblings": [{"name": "file1"}, {"name": "file2"}],
            "usedStorage": 1000000,
        }
        return base_model

    @pytest.fixture
    def model_no_dataset_metadata(
        self, base_model
    ):  # base_model type comes from conftest
        base_model._dataset_metadata = None
        return base_model

    @pytest.fixture(autouse=True)
    def patch_requests_post(self) -> Iterator[Mock]:
        with patch(
            "src.metrics.DatasetQualityMetric.requests.post"
        ) as mock_post:
            yield mock_post

    # --- Tests ---

    def test_evaluate_with_valid_metadata(
        self,
        metric: DatasetQualityMetric,
        model_with_dataset_metadata,
        patch_requests_post: Mock,
    ) -> None:
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "0.8"}}]
        }
        patch_requests_post.return_value = mock_response

        score = metric.evaluate(model_with_dataset_metadata)

        assert score == 0.8
        patch_requests_post.assert_called_once()

    def test_evaluate_no_dataset_metadata(
        self, metric: DatasetQualityMetric, model_no_dataset_metadata
    ) -> None:
        score = metric.evaluate(model_no_dataset_metadata)
        assert score == 0.0

    def test_evaluate_api_failure(
        self,
        metric: DatasetQualityMetric,
        model_with_dataset_metadata,
        patch_requests_post: Mock,
    ) -> None:
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        patch_requests_post.return_value = mock_response

        score = metric.evaluate(model_with_dataset_metadata)
        assert score == 0.0

    def test_evaluate_exception(
        self,
        metric: DatasetQualityMetric,
        model_with_dataset_metadata,
        patch_requests_post: Mock,
    ) -> None:
        # Mock exception during API call
        patch_requests_post.side_effect = Exception("Network error")

        score = metric.evaluate(model_with_dataset_metadata)
        assert score == 0.0

    def test_parse_score_valid_float(
        self, metric: DatasetQualityMetric
    ) -> None:
        assert metric._parse_score("0.75") == 0.75
        assert metric._parse_score("0.0") == 0.0
        assert metric._parse_score("1.0") == 1.0

    def test_parse_score_out_of_10(self, metric: DatasetQualityMetric) -> None:
        assert metric._parse_score("7.5") == 0.75
        assert metric._parse_score("10") == 1.0

    def test_parse_score_out_of_100(
        self, metric: DatasetQualityMetric
    ) -> None:
        assert metric._parse_score("75") == 0.75
        assert metric._parse_score("100") == 1.0

    def test_parse_score_with_text(self, metric: DatasetQualityMetric) -> None:
        assert metric._parse_score("The score is 0.8") == 0.8
        assert metric._parse_score("Score: 0.65") == 0.65

    def test_parse_score_invalid(self, metric: DatasetQualityMetric) -> None:
        assert metric._parse_score("invalid") is None
        assert metric._parse_score("") is None
        assert metric._parse_score("no numbers here") is None

    def test_create_quality_prompt(self, metric: DatasetQualityMetric) -> None:
        metadata = {"id": "test/dataset", "description": "Test"}
        prompt = metric._create_quality_prompt(metadata)

        assert "test/dataset" in prompt
        assert "Test" in prompt
        assert "0.0 to 1.0" in prompt
        assert "ONLY a numerical score" in prompt

    def test_no_api_key_warning(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "src.metrics.DatasetQualityMetric.logger"
            ) as mock_logger:
                metric = DatasetQualityMetric()
                mock_logger.warning.assert_called_once()
                assert metric.api_key is None

    def test_get_llm_score_no_choices(
        self, metric: DatasetQualityMetric, patch_requests_post: Mock
    ) -> None:
        # Mock response with no choices
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}
        patch_requests_post.return_value = mock_response

        result = metric._get_llm_score("test prompt")
        assert result is None

    def test_get_llm_score_unparseable_content(
        self, metric: DatasetQualityMetric, patch_requests_post: Mock
    ) -> None:
        # Mock response with unparseable content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "I cannot provide a score"}}]
        }
        patch_requests_post.return_value = mock_response

        result = metric._get_llm_score("test prompt")
        assert result is None
