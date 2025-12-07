"""
Model.py
========

This module defines the `Model` class, which represents a machine learning model
alongside its metadata, source code, dataset, and evaluation scores.

Responsibilities
----------------
- Encapsulate the model, dataset, and code URLs.
- Fetch and cache metadata from HuggingFace (model, dataset) and GitHub (code).
- Evaluate the model using a list of provided Metric objects.
- Store evaluation results and compute an overall NetScore.

Attributes (typical)
--------------------
- modelLink (str): Required. HuggingFace model URL.
- codeLink (Optional[str]): Optional GitHub repository URL.
- datasetLink (Optional[str]): Optional HuggingFace dataset URL.
- evaluations (dict): Maps metric names to scores (float or dict of floats).
- evaluationsLatency (dict): Maps metric names to evaluation time in seconds.

Workflow
--------
1. Instantiate the `Model` with one to three URLs: `[<code>, <dataset>, model]`.
2. Metrics can be evaluated with `evaluate()` or in batch with `evaluate_all()`.
3. Metadata properties (e.g. `hf_metadata`) lazily fetch and cache external data.
4. Final NetScore is computed from individual metric scores via `computeNetScore()`.

Scoring
-------
- Scores may be simple floats (e.g., 0.85) or structured (e.g., size by device).
- `computeNetScore()` uses a weighted combination of metric scores.
- The LicenseMetric acts as a gating multiplier on the final score.
- Metrics with missing or invalid values default to 0.

Error Handling & Resilience
---------------------------
- Fallbacks are in place for missing metadata or failed metric evaluations.
- Invalid types (e.g. non-dict SizeMetric) are logged and treated as zero.
- If metadata fetchers fail, the system proceeds with partial data.

Environment
-----------
- ``GITHUB_TOKEN`` (REQUIRED): Used to authenticate GitHub API requests, which
  increases rate limits and allows access to private repositories if needed.

"""

import concurrent.futures
import os
import time
from typing import Any, Dict, List, Optional, Union, Tuple

from loguru import logger

from src.Metric import Metric
from src.ModelData import ModelData
from src.util.metadata_fetchers import (
    DatasetFetcher,
    GitHubFetcher,
    HuggingFaceFetcher,
)


class Model(ModelData):
    def __init__(self, urls: List[str]) -> None:
        # Extract URLs
        self.codeLink: Optional[str] = urls[0] if urls[0] else None
        self.datasetLink: Optional[str] = urls[1] if urls[1] else None
        self.modelLink: str = urls[2]

        # Validate Model URL Exists
        if not self.modelLink:
            raise ValueError("Model URL is required")

        # Metadata Caching
        self._hf_metadata: Optional[Dict[str, Any]] = None
        self._github_metadata: Optional[Dict[str, Any]] = None
        self._dataset_metadata: Optional[Dict[str, Any]] = None

        # Get GitHub token from environment (validated at startup)
        self._github_token: Optional[str] = os.getenv("GITHUB_TOKEN")

        # evaluations: maps metric names to their scores
        #   scores: a float or a dictionary of floats for complex metrics (SizeMetric)
        # evaluationsLatency: maps metric names to the time taken to compute them
        self.evaluations: dict[str, Union[float, dict[str, float]]] = {}
        self.evaluationsLatency: dict[str, float] = {}

    @property
    def name(self) -> str:
        try:
            if self.hf_metadata:
                return self.hf_metadata.get("id", "").split("/")[1]
        except (AttributeError, IndexError):
            pass
        return "UNKNOWN_MODEL"

    @property
    def hf_metadata(self) -> Optional[Dict[str, Any]]:
        if self._hf_metadata is None:
            fetcher = HuggingFaceFetcher()
            self._hf_metadata = fetcher.fetch_metadata(self.modelLink)
        return self._hf_metadata

    @property
    def github_metadata(self) -> Optional[Dict[str, Any]]:
        if self._github_metadata is None:
            fetcher = GitHubFetcher(token=self._github_token)
            self._github_metadata = fetcher.fetch_metadata(self.codeLink)
        return self._github_metadata

    @property
    def dataset_metadata(self) -> Optional[Dict[str, Any]]:
        if self._dataset_metadata is None:
            fetcher = DatasetFetcher()
            self._dataset_metadata = fetcher.fetch_metadata(self.datasetLink)
        return self._dataset_metadata

    def getScore(
        self, metric_name: str, default: Union[float, dict[str, float]] = 0.0
    ) -> Union[float, dict[str, float]]:
        value = self.evaluations.get(metric_name, default)
        if isinstance(value, dict):
            return {k: round(v, 2) for k, v in value.items()}
        return round(value, 2)

    def getLatency(self, metric_name: str) -> int:
        latency = self.evaluationsLatency.get(metric_name, 0.0)
        return int(latency * 1000)

    def evaluate_all(self, metrics: List[Metric]) -> None:
        def evaluate_metric(
            metric: Metric,
        ) -> Tuple[Metric, Union[float, Dict[str, float]], float]:
            start = time.time()
            score = metric.evaluate(self)
            latency = time.time() - start
            return (metric, score, latency)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(evaluate_metric, m) for m in metrics]

            for future in concurrent.futures.as_completed(futures):
                metric, score, latency = future.result()
                metric_name = type(metric).__name__
                self.evaluations[metric_name] = score
                self.evaluationsLatency[metric_name] = latency

        self.computeNetScore()

    def getCategory(self) -> str:
        return "MODEL"

    def computeNetScore(self) -> None:
        def safe_score(key: str) -> float:
            val = self.evaluations.get(key)
            if key == "SizeMetric":
                # Only accept dict for SizeMetric, else 0.0
                if isinstance(val, dict) and val:
                    return sum(val.values()) / len(val)
                else:
                    logger.warning(f"SizeMetric score is not a valid dict: {val}")
                    return 0.0
            else:
                if isinstance(val, dict):
                    return sum(val.values()) / len(val) if val else 0.0
                return val if val is not None else 0.0

        # Compute Net Score and Net Latency
        license_score = safe_score("LicenseMetric")
        weighted_sum = (
            0.15 * safe_score("SizeMetric")
            + 0.25 * safe_score("RampUpMetric")
            + 0.10 * safe_score("BusFactorMetric")
            + 0.10 * safe_score("AvailabilityMetric")
            + 0.10 * safe_score("DatasetQualityMetric")
            + 0.10 * safe_score("CodeQualityMetric")
            + 0.10 * safe_score("PerformanceClaimsMetric")
            + 0.10 * safe_score("ReproducibilityMetric")
        )
        self.evaluations["NetScore"] = license_score * weighted_sum
        self.evaluationsLatency["NetScore"] = sum(
            latency
            for key, latency in self.evaluationsLatency.items()
            if key != "NetScore"
        )
