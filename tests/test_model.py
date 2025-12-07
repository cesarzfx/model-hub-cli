from unittest.mock import patch

from src.Metric import Metric
from src.Model import Model


class DummyMetric(Metric):
    def evaluate(self, model) -> float:
        return 0.5


class ComplexDummyMetric(Metric):
    def evaluate(self, model) -> dict[str, float]:
        return {
            "raspberry_pi": 0.6,
            "jetson_nano": 0.6,
            "desktop_pc": 0.8,
            "aws_server": 0.8,
        }


def test_model_initialization_and_url_classification(sample_urls):
    model = Model(sample_urls)

    # Check that URLs were classified correctly
    assert model.modelLink.startswith("https://huggingface.co/")
    assert model.codeLink.startswith("https://github.com/")
    assert model.datasetLink.startswith("https://huggingface.co/datasets/")


def test_get_category_string(sample_urls):
    model = Model(sample_urls)
    category = model.getCategory()
    assert category == "MODEL"


def test_evaluation_and_latency_storage(sample_urls):
    model = Model(sample_urls)
    metric = DummyMetric()

    # Evaluate using the new batch method with a single metric
    model.evaluate_all([metric])

    # Check evaluations and latencies are stored correctly
    assert "DummyMetric" in model.evaluations
    assert model.evaluations["DummyMetric"] == 0.5

    assert "DummyMetric" in model.evaluationsLatency
    assert isinstance(model.evaluationsLatency["DummyMetric"], float)


def test_get_score_and_latency_methods_with_float(sample_urls):
    model = Model(sample_urls)
    metric = DummyMetric()
    model.evaluate_all([metric])

    assert model.getScore("DummyMetric") == 0.5
    assert isinstance(model.getLatency("DummyMetric"), int)


def test_get_score_with_dict(sample_urls):
    model = Model(sample_urls)
    metric = ComplexDummyMetric()
    model.evaluate_all([metric])

    expected_dict = {
        "raspberry_pi": 0.6,
        "jetson_nano": 0.6,
        "desktop_pc": 0.8,
        "aws_server": 0.8,
    }

    assert model.getScore("ComplexDummyMetric") == expected_dict


def computeNetScore(self) -> float:
    license_score = self.evaluations.get("LicenseMetric", 0.0) or 0.0
    size_score = self.evaluations.get("SizeMetric", {})
    rampup_score = self.evaluations.get("RampUpMetric", 0.0) or 0.0
    bus_score = self.evaluations.get("BusFactorMetric", 0.0) or 0.0
    avail_score = self.evaluations.get("AvailabilityMetric", 0.0) or 0.0
    data_qual_score = self.evaluations.get("DatasetQualityMetric", 0.0) or 0.0
    code_qual_score = self.evaluations.get("CodeQualityMetric", 0.0) or 0.0
    perf_score = self.evaluations.get("PerformanceClaimsMetric", 0.0) or 0.0

    avg_size_score = sum(size_score.values()) / len(size_score) if size_score else 0.0

    weighted_sum = (
        0.2 * avg_size_score
        + 0.3 * rampup_score
        + 0.1 * bus_score
        + 0.1 * avail_score
        + 0.1 * data_qual_score
        + 0.1 * code_qual_score
        + 0.1 * perf_score
    )

    net_score = license_score * weighted_sum

    self.evaluations["NetScore"] = net_score
    self.evaluationsLatency["NetScore"] = 0.0  # Derived metric

    return round(net_score, 2)


def test_evaluate_all_runs_multiple_metrics(sample_urls):
    model = Model(sample_urls)
    metrics = [DummyMetric(), ComplexDummyMetric()]

    # Patch computeNetScore to avoid relying on real metric values
    with patch.object(Model, "computeNetScore", return_value=0.0):
        model.evaluate_all(metrics)

    assert "DummyMetric" in model.evaluations
    assert "ComplexDummyMetric" in model.evaluations


def test_compute_net_score_all_metrics_present(sample_urls):
    model = Model(sample_urls)

    # Fake evaluation values
    model.evaluations = {
        "LicenseMetric": 1.0,
        "SizeMetric": {
            "raspberry_pi": 0.6,
            "jetson_nano": 0.6,
            "desktop_pc": 0.8,
            "aws_server": 0.8,
        },
        "RampUpMetric": 0.7,
        "BusFactorMetric": 0.8,
        "AvailabilityMetric": 0.9,
        "DatasetQualityMetric": 0.6,
        "CodeQualityMetric": 0.7,
        "PerformanceClaimsMetric": 0.5,
    }

    expected_size_avg = 0.7  # (0.6 + 0.6 + 0.8 + 0.8) / 4

    expected_weighted = (
        0.15 * expected_size_avg
        + 0.25 * 0.7
        + 0.10 * 0.8
        + 0.10 * 0.9
        + 0.10 * 0.6
        + 0.10 * 0.7
        + 0.10 * 0.5
        + 0.10 * 0.0  # ReproducibilityMetric missing, treated as 0
    )

    expected_score = round(1.0 * expected_weighted, 2)
    model.computeNetScore()

    assert abs(model.evaluations["NetScore"] - expected_score) < 1e-6


def test_compute_net_score_missing_license_returns_zero(sample_urls):
    model = Model(sample_urls)

    model.evaluations = {
        # "LicenseMetric" is missing
        "SizeMetric": {
            "raspberry_pi": 0.6,
            "jetson_nano": 0.6,
            "desktop_pc": 0.8,
            "aws_server": 0.8,
        },
        "RampUpMetric": 0.7,
        "BusFactorMetric": 0.8,
        "AvailabilityMetric": 0.9,
        "DatasetQualityMetric": 0.6,
        "CodeQualityMetric": 0.7,
        "PerformanceClaimsMetric": 0.5,
    }

    model.computeNetScore()

    assert model.evaluations["NetScore"] == 0.0
    assert model.evaluationsLatency["NetScore"] == 0.0


def test_compute_net_score_handles_missing_metrics_as_zero(sample_urls):
    model = Model(sample_urls)

    # Some metrics missing from evaluations
    model.evaluations = {
        "LicenseMetric": 1.0,
        # SizeMetric missing
        "RampUpMetric": 0.5,
        # BusFactorMetric missing
        "AvailabilityMetric": 0.7,
        "DatasetQualityMetric": 0.6,
        "CodeQualityMetric": 0.65,
        # PerformanceClaimsMetric missing
    }

    expected_weighted = (
        0.15 * 0.0  # SizeMetric treated as 0
        + 0.25 * 0.5
        + 0.10 * 0.0  # BusFactorMetric treated as 0
        + 0.10 * 0.7
        + 0.10 * 0.6
        + 0.10 * 0.65
        + 0.10 * 0.0  # PerformanceClaimsMetric treated as 0
        + 0.10 * 0.0  # ReproducibilityMetric treated as 0
    )

    expected_score = round(1.0 * expected_weighted, 2)
    model.computeNetScore()

    assert round(model.evaluations["NetScore"], 2) == expected_score


def test_compute_net_score_with_invalid_size_metric(sample_urls):
    model = Model(sample_urls)

    # SizeMetric is not a dict (should be ignored)
    model.evaluations = {
        "LicenseMetric": 1.0,
        "SizeMetric": 0.6,  # Invalid format
        "RampUpMetric": 0.7,
        "BusFactorMetric": 0.8,
        "AvailabilityMetric": 0.9,
        "DatasetQualityMetric": 0.6,
        "CodeQualityMetric": 0.7,
        "PerformanceClaimsMetric": 0.5,
    }

    # Size gets treated as 0.0
    expected_weighted = (
        0.0  # size
        + 0.25 * 0.7
        + 0.10 * 0.8
        + 0.10 * 0.9
        + 0.10 * 0.6
        + 0.10 * 0.7
        + 0.10 * 0.5
        + 0.10 * 0.0  # ReproducibilityMetric missing, treated as 0
    )
    expected_score = round(1.0 * expected_weighted, 2)
    model.computeNetScore()

    assert round(model.evaluations["NetScore"], 2) == expected_score
