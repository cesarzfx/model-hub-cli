"""Unit tests for the PerformanceClaimsMetric."""

import pytest
from unittest.mock import MagicMock

from src.metrics.PerformanceClaimsMetric import PerformanceClaimsMetric
from tests.conftest import StubModelData


@pytest.fixture
def metric():
    metric = PerformanceClaimsMetric()
    # Patch LLMClient methods for deterministic tests
    metric.llm_client.send_prompt = MagicMock()
    metric.llm_client.extract_score = MagicMock()
    return metric


@pytest.fixture
def hf_model():
    model = StubModelData(
        modelLink="https://huggingface.co/facebook/bart-large",
        codeLink="https://github.com/huggingface/transformers",
        datasetLink="https://huggingface.co/datasets/squad",
    )
    model._hf_metadata = {
        "cardData": {
            "model_description": "This model achieves 95% accuracy on ImageNet",
            "model_summary": "High performance model with 0.92 F1 score",
        },
        "readme": "Model achieves great results on ImageNet and GLUE benchmarks.",
    }
    return model


def test_llm_score_full_claims(metric, hf_model):
    """Test LLM scoring for strong claims and benchmarks."""
    metric.llm_client.send_prompt.return_value = "1.0"
    metric.llm_client.extract_score.return_value = 1.0
    score = metric.evaluate(hf_model)
    assert score == 1.0


def test_llm_score_no_claims(metric, hf_model):
    """Test LLM scoring for no claims or benchmarks."""
    hf_model._hf_metadata["cardData"]["model_description"] = ""
    hf_model._hf_metadata["readme"] = ""
    metric.llm_client.send_prompt.return_value = "0.0"
    metric.llm_client.extract_score.return_value = 0.0
    score = metric.evaluate(hf_model)
    assert score == 0.0


def test_llm_score_missing_metadata(metric):
    """Test LLM scoring when metadata is missing."""
    model = StubModelData(modelLink="", codeLink="", datasetLink="")
    model._hf_metadata = None
    metric.llm_client.send_prompt.return_value = "0.0"
    metric.llm_client.extract_score.return_value = 0.0
    score = metric.evaluate(model)
    assert score == 0.0


def test_llm_score_invalid_metadata(metric):
    """Test LLM scoring when metadata is invalid."""
    model = StubModelData(modelLink="", codeLink="", datasetLink="")
    model._hf_metadata = {"invalid": "data"}
    metric.llm_client.send_prompt.return_value = "0.0"
    metric.llm_client.extract_score.return_value = 0.0
    score = metric.evaluate(model)
    assert score == 0.0
