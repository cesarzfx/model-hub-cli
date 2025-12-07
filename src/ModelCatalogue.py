"""
ModelCatalogue.py
=================

Coordinates model evaluation using a fixed set of metrics and generates
structured reports for further consumption.

Responsibilities
----------------
- Maintain a catalogue of models to be evaluated.
- Store a fixed set of metrics applied to all models.
- Run evaluations across all models.
- Generate an NDJSON report with scores and evaluation latencies.

Key Concepts
------------
- **Model**: Represents a machine learning model with associated URLs and metadata.
- **Metric**: Abstract evaluation logic applied to a model (e.g., license check, size).
- **NDJSON**: Newline-delimited JSON, ideal for streaming analytics or ingestion.

Typical Flow
------------
1. Instantiate `ModelCatalogue`.
2. Use `addModel()` to register each `Model`.
3. Call `evaluateModels()` to run all metrics on all models.
4. Call `generateReport()` to produce a report.

Inputs & Outputs
----------------
- Input: A list of `Model` instances (each with code, model, and dataset URLs).
- Output: NDJSON report string, where each line is a model's evaluation result.

Error Handling
--------------
- Assumes individual `Model.evaluate()` implementations handle their own exceptions.
- Logging is used to trace model addition and report generation steps.

Testing Notes
-------------
- Core test targets include:
    - Model addition (`addModel`)
    - Evaluation workflow (`evaluateModels`)
    - Output format and field presence (`generateReport`, `getModelNDJSON`)
- Use mocked metrics to simulate model scoring in tests.
"""

import json

from loguru import logger

from src.Metric import Metric
from src.metrics.AvailabilityMetric import AvailabilityMetric
from src.metrics.BusFactorMetric import BusFactorMetric
from src.metrics.CodeQualityMetric import CodeQualityMetric
from src.metrics.DatasetQualityMetric import DatasetQualityMetric
from src.metrics.LicenseMetric import LicenseMetric
from src.metrics.PerformanceClaimsMetric import PerformanceClaimsMetric
from src.metrics.RampUpMetric import RampUpMetric
from src.metrics.ReproducibilityMetric import ReproducibilityMetric
from src.metrics.ReviewednessMetric import ReviewednessMetric
from src.metrics.SizeMetric import SizeMetric
from src.Model import Model


class ModelCatalogue:

    # models holds all Model instances in the catalogue.
    # metrics holds all Metric instances to be applied to models.

    def __init__(self) -> None:
        self.models: list[Model] = []
        self.metrics: list[Metric] = [
            LicenseMetric(),
            AvailabilityMetric(),
            PerformanceClaimsMetric(),
            BusFactorMetric(),
            SizeMetric(),
            CodeQualityMetric(),
            DatasetQualityMetric(),
            RampUpMetric(),
            ReviewednessMetric(),
            ReproducibilityMetric(),
        ]

    def addModel(self, model: Model) -> None:
        self.models.append(model)

        logger.debug(
            """Model added to the catalogue:
            Model URL = '{}',
            Dataset URL = '{}',
            Code URL = '{}'""",
            model.modelLink,
            model.datasetLink,
            model.codeLink,
        )

    def evaluateModels(self) -> None:
        for model in self.models:
            model.evaluate_all(self.metrics)

    def generateReport(self) -> str:
        ndjson_report = []
        for model in self.models:
            ndjson_report.append(self.getModelNDJSON(model))

        logger.debug("Report generated for {} models.", len(self.models))
        return "\n".join(ndjson_report)

    def getModelNDJSON(self, model: Model) -> str:
        ndjson_obj = {
            "name": model.name,
            "category": model.getCategory(),
            "net_score": model.getScore("NetScore"),
            "net_score_latency": model.getLatency("NetScore"),
            "ramp_up_time": model.getScore("RampUpMetric"),
            "ramp_up_time_latency": model.getLatency("RampUpMetric"),
            "bus_factor": model.getScore("BusFactorMetric"),
            "bus_factor_latency": model.getLatency("BusFactorMetric"),
            "performance_claims": model.getScore("PerformanceClaimsMetric"),
            "performance_claims_latency": model.getLatency("PerformanceClaimsMetric"),
            "license": model.getScore("LicenseMetric"),
            "license_latency": model.getLatency("LicenseMetric"),
            "size_score": model.getScore("SizeMetric", {}),  # may be dict
            "size_score_latency": model.getLatency("SizeMetric"),
            "dataset_and_code_score": model.getScore("AvailabilityMetric"),
            "dataset_and_code_score_latency": model.getLatency("AvailabilityMetric"),
            "dataset_quality": model.getScore("DatasetQualityMetric"),
            "dataset_quality_latency": model.getLatency("DatasetQualityMetric"),
            "code_quality": model.getScore("CodeQualityMetric"),
            "code_quality_latency": model.getLatency("CodeQualityMetric"),
            "reviewedness": model.getScore("ReviewednessMetric"),
            "reviewedness_latency": model.getLatency("ReviewednessMetric"),
            "reproducibility": model.getScore("ReproducibilityMetric"),
            "reproducibility_latency": model.getLatency("ReproducibilityMetric"),
        }

        # Convert model evaluation to a single NDJSON line
        return json.dumps(ndjson_obj, separators=(",", ":"))
