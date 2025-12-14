"""
Pytest configuration and reusable fixtures for model-hub-cli tests.
"""

from dataclasses import dataclass
from loguru import logger
from typing import Any, Dict, Optional
import logging
import pytest

from src.Model import Model


@dataclass
class StubModelData:
    modelLink: str
    codeLink: Optional[str]
    datasetLink: Optional[str]
    _hf_metadata: Optional[Dict[str, Any]] = None
    _github_metadata: Optional[Dict[str, Any]] = None

    @property
    def hf_metadata(self) -> Optional[Dict[str, Any]]:
        return self._hf_metadata

    @hf_metadata.setter
    def hf_metadata(self, value: Optional[Dict[str, Any]]):
        self._hf_metadata = value

    @property
    def github_metadata(self) -> Optional[Dict[str, Any]]:
        return self._github_metadata

    @github_metadata.setter
    def github_metadata(self, value: Optional[Dict[str, Any]]):
        self._github_metadata = value

    @property
    def dataset_metadata(self) -> Optional[Dict[str, Any]]:
        return self._dataset_metadata

    @dataset_metadata.setter
    def dataset_metadata(self, value: Optional[Dict[str, Any]]):
        self._dataset_metadata = value


@pytest.fixture
def base_model() -> StubModelData:
    """
    Fixture that returns a fully populated StubModelData instance.
    Used as a baseline test model with valid HuggingFace and GitHub URLs.
    """
    return StubModelData(
        modelLink="https://huggingface.co/microsoft/DialoGPT-medium",
        codeLink="https://github.com/huggingface/transformers",
        datasetLink="https://huggingface.co/datasets/squad",
    )


@pytest.fixture
def sample_model(sample_urls) -> Model:
    """
    Fixture that returns a Model instance created from sample URLs.
    Used as a baseline test model for testing Model-related functionality.
    """
    return Model(sample_urls)


@pytest.fixture
def sample_urls() -> list[str]:
    """
    Fixture that provides a sample list of model, dataset, and code URLs.
    Used to simulate bundled input.
    """
    return [
        "https://github.com/huggingface/transformers",  # codeLink
        "https://huggingface.co/datasets/squad",  # datasetLink
        "https://huggingface.co/microsoft/DialoGPT-medium",  # modelLink
    ]


@pytest.fixture(autouse=True)
def intercept_loguru_logs(caplog):
    """
    Redirect loguru logs to standard logging so pytest caplog can capture them.
    """

    class PropagateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    logging.basicConfig(level=logging.DEBUG)  # ensure root logger handles all messages
    logger.remove()  # remove default loguru handlers
    logger.add(PropagateHandler(), level="DEBUG")
    yield
    logger.remove()
