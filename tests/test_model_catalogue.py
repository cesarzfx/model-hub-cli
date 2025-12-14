import json

from unittest.mock import MagicMock

from src.Metric import Metric
from src.ModelData import ModelData
from src.ModelCatalogue import ModelCatalogue


class StubMetric(Metric):
    """Metric that returns a constant float value."""

    def __init__(self, name="StubMetric", value=0.42) -> None:
        self._name = name
        self._value = value

    def evaluate(self, model: ModelData) -> float:
        return self._value


class StubMetric1(StubMetric):
    pass


class StubMetric2(StubMetric):
    pass


class StubSizeMetric(Metric):
    """Stub metric simulating SizeMetric device-specific scores."""

    def evaluate(self, model: ModelData) -> dict[str, float]:
        return {
            "raspberry_pi": 0.6,
            "jetson_nano": 0.6,
            "desktop_pc": 0.8,
            "aws_server": 0.8,
        }


def test_add_model_adds_to_internal_list(sample_model):
    catalogue = ModelCatalogue()
    assert len(catalogue.models) == 0

    catalogue.addModel(sample_model)
    assert len(catalogue.models) == 1
    assert catalogue.models[0] == sample_model


def test_evaluate_models_runs_all_metrics(sample_model):
    catalogue = ModelCatalogue()
    sample_model.computeNetScore = MagicMock()

    catalogue.metrics = [
        StubMetric1("StubMetric1", 0.3),
        StubMetric2("StubMetric2", 0.7),
    ]

    catalogue.addModel(sample_model)
    catalogue.evaluateModels()

    model = catalogue.models[0]
    assert "StubMetric1" in model.evaluations
    assert "StubMetric2" in model.evaluations
    sample_model.computeNetScore.assert_called_once()


def test_generate_report_format(sample_model):
    catalogue = ModelCatalogue()

    # Mock computeNetScore to avoid needing full metrics
    sample_model.computeNetScore = MagicMock(return_value=0.42)

    # Use predictable stub metrics
    catalogue.metrics = [
        StubMetric("LicenseMetric", 1.0),
        StubMetric("BusFactorMetric", 0.8),
        StubMetric("RampUpMetric", 0.6),
        StubMetric("AvailabilityMetric", 0.7),
        StubMetric("DatasetQualityMetric", 0.6),
        StubMetric("CodeQualityMetric", 0.65),
        StubMetric("PerformanceClaimsMetric", 0.55),
        StubSizeMetric(),  # returns dict
    ]

    catalogue.addModel(sample_model)
    catalogue.evaluateModels()
    report = catalogue.generateReport()

    # Validate NDJSON format
    lines = report.strip().splitlines()
    assert len(lines) == 1

    model_json = json.loads(lines[0])
    assert isinstance(model_json, dict)

    expected_keys = {
        "name",
        "category",
        "net_score",
        "net_score_latency",
        "ramp_up_time",
        "ramp_up_time_latency",
        "bus_factor",
        "bus_factor_latency",
        "performance_claims",
        "performance_claims_latency",
        "license",
        "license_latency",
        "size_score",
        "size_score_latency",
        "dataset_and_code_score",
        "dataset_and_code_score_latency",
        "dataset_quality",
        "dataset_quality_latency",
        "code_quality",
        "code_quality_latency",
    }

    assert expected_keys.issubset(
        model_json.keys()
    ), f"Missing keys: {expected_keys - model_json.keys()}"


def test_get_model_ndjson_defaults(sample_model):
    catalogue = ModelCatalogue()
    ndjson_str = catalogue.getModelNDJSON(sample_model)
    data = json.loads(ndjson_str)

    assert isinstance(data["net_score"], float)
    assert isinstance(data["net_score_latency"], int)
    assert isinstance(data["size_score"], dict)
