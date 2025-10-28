"""
ModelData.py
=============
Defines structural contracts shared across the system.


Purpose
-------
The `ModelData` protocol provides a lightweight interface for accessing
URLs and metadata associated with a model. It allows metric classes to
interact with model instances in a consistent, type-safe way—without
depending on a specific implementation.


Typical Types
-------------
Attributes expected by the protocol:

- `modelLink` (str): Hugging Face model URL (required).
- `codeLink` (Optional[str]): GitHub repository URL (optional).
- `datasetLink` (Optional[str]): Dataset source URL (optional).

Cached metadata properties (dicts, typically from API fetchers):

- `hf_metadata`: Hugging Face model metadata.
- `github_metadata`: GitHub repository metadata.
- `dataset_metadata`: Dataset metadata (from Hugging Face or other sources).


Usage
-----
Implemented by the `Model` class and passed to each `Metric` for evaluation:

    class SomeMetric(Metric):
        def evaluate(self, model: ModelData) -> float:
            stars = model.github_metadata.get("stargazers_count", 0)
            return stars / 100.0

Because this is a structural protocol, any object matching the signature
can be used—making it easy to test with mocks or stubs.


Notes
-----
- All metadata properties must return a `dict` (even if empty).
- Protocols enable decoupling logic from concrete implementations.
- This file should remain small and implementation-agnostic.
"""

from abc import abstractmethod
from typing import Any, Dict, Optional, Protocol


class ModelData(Protocol):

    modelLink: str
    codeLink: Optional[str]
    datasetLink: Optional[str]

    @property
    @abstractmethod
    def hf_metadata(self) -> Optional[Dict[str, Any]]:
        """Cached HuggingFace metadata (may be None if unavailable)"""
        ...

    @property
    @abstractmethod
    def github_metadata(self) -> Optional[Dict[str, Any]]:
        """Cached GitHub metadata (may be None if unavailable)"""
        ...

    @property
    @abstractmethod
    def dataset_metadata(self) -> Optional[Dict[str, Any]]:
        """Cached Dataset metadata (may be None if unavailable)"""
        ...
