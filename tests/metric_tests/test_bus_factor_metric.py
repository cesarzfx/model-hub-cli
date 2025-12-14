import pytest

from src.metrics.BusFactorMetric import BusFactorMetric
from tests.conftest import StubModelData
from tests.metric_tests.base_metric_test import BaseMetricTest


class TestBusFactorMetric(BaseMetricTest):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.metric = BusFactorMetric()

    def test_large_company_author(self):
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _hf_metadata={"author": "google"},
        )
        self.run_metric_test(self.metric, model, 1.0)

    def test_large_company_id(self):
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _hf_metadata={"id": "facebook/model"},
        )
        self.run_metric_test(self.metric, model, 1.0)

    def test_no_metadata(self):
        model = StubModelData(modelLink="", codeLink=None, datasetLink=None)
        self.run_metric_test(self.metric, model, 0.0)

    def test_no_contributors(self):
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _hf_metadata={},
            _github_metadata={},
        )
        self.run_metric_test(self.metric, model, 0.0)

    def test_zero_contributions(self):
        contribs = [{"contributions": 0}, {"contributions": 0}]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"contributors": contribs},
        )
        self.run_metric_test(self.metric, model, 0.0)

    def test_contributors_even_distribution(self):
        contribs = [
            {"contributions": 10},
            {"contributions": 10},
            {"contributions": 10},
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"contributors": contribs},
        )
        expected = 0.3  # 3 contributors * 0.1 max_score * perfect distribution
        self.run_metric_test(self.metric, model, expected)

    def test_contributors_skewed_distribution(self):
        contribs = [
            {"contributions": 10},
            {"contributions": 5},
            {"contributions": 1},
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"contributors": contribs},
        )
        expected = (1 / 10) * 0.3  # min/max * max_score
        self.run_metric_test(self.metric, model, expected)
