"""
test_reviewedness_metric.py
============================

Unit tests for the ReviewednessMetric class.

Tests cover:
- No GitHub metadata
- No pull requests
- No merged pull requests
- All merged PRs reviewed
- Partial PR review coverage
- PRs with different review indicators
"""

import pytest

from src.metrics.ReviewednessMetric import ReviewednessMetric
from tests.conftest import StubModelData
from tests.metric_tests.base_metric_test import BaseMetricTest


class TestReviewednessMetric(BaseMetricTest):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.metric = ReviewednessMetric()

    def test_no_github_metadata(self):
        """Test that -1.0 is returned when no GitHub metadata is available"""
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
        )
        self.run_metric_test(self.metric, model, -1.0)

    def test_no_pull_requests(self):
        """Test that -1.0 is returned when no pull requests are found"""
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": []},
        )
        self.run_metric_test(self.metric, model, -1.0)

    def test_no_merged_pull_requests(self):
        """Test that 0.0 is returned when no PRs have been merged"""
        pull_requests = [
            {"merged_at": None, "comments": 5, "review_comments": 2},
            {"merged_at": None, "comments": 3, "review_comments": 1},
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        self.run_metric_test(self.metric, model, 0.0)

    def test_all_merged_prs_reviewed(self):
        """Test that 1.0 is returned when all merged PRs have reviews"""
        pull_requests = [
            {"merged_at": "2024-01-01", "comments": 5, "review_comments": 2},
            {"merged_at": "2024-01-02", "comments": 3, "review_comments": 1},
            {"merged_at": "2024-01-03", "comments": 2, "review_comments": 0},
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        self.run_metric_test(self.metric, model, 1.0)

    def test_partial_review_coverage(self):
        """Test that correct fraction is returned when some PRs are reviewed"""
        pull_requests = [
            {"merged_at": "2024-01-01", "comments": 5, "review_comments": 2},
            {"merged_at": "2024-01-02", "comments": 0, "review_comments": 0},
            {"merged_at": "2024-01-03", "comments": 3, "review_comments": 1},
            {"merged_at": "2024-01-04", "comments": 0, "review_comments": 0},
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        # 2 out of 4 merged PRs have reviews = 0.5
        self.run_metric_test(self.metric, model, 0.5)

    def test_review_via_requested_reviewers(self):
        """Test that PRs with requested reviewers are counted as reviewed"""
        pull_requests = [
            {
                "merged_at": "2024-01-01",
                "comments": 0,
                "review_comments": 0,
                "requested_reviewers": [{"login": "reviewer1"}],
                "requested_teams": [],
            },
            {
                "merged_at": "2024-01-02",
                "comments": 0,
                "review_comments": 0,
                "requested_reviewers": [],
                "requested_teams": [],
            },
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        # 1 out of 2 merged PRs have requested reviewers = 0.5
        self.run_metric_test(self.metric, model, 0.5)

    def test_review_via_requested_teams(self):
        """Test that PRs with requested teams are counted as reviewed"""
        pull_requests = [
            {
                "merged_at": "2024-01-01",
                "comments": 0,
                "review_comments": 0,
                "requested_reviewers": [],
                "requested_teams": [{"name": "team1"}],
            },
            {
                "merged_at": "2024-01-02",
                "comments": 0,
                "review_comments": 0,
                "requested_reviewers": [],
                "requested_teams": [],
            },
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        # 1 out of 2 merged PRs have requested teams = 0.5
        self.run_metric_test(self.metric, model, 0.5)

    def test_mixed_merged_and_unmerged_prs(self):
        """Test that only merged PRs are considered in the calculation"""
        pull_requests = [
            {"merged_at": "2024-01-01", "comments": 5, "review_comments": 2},
            {"merged_at": None, "comments": 10, "review_comments": 5},  # Not merged
            {"merged_at": "2024-01-02", "comments": 3, "review_comments": 1},
            {"merged_at": None, "comments": 8, "review_comments": 3},  # Not merged
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        # 2 out of 2 merged PRs have reviews = 1.0
        self.run_metric_test(self.metric, model, 1.0)

    def test_no_reviews_on_merged_prs(self):
        """Test that 0.0 is returned when merged PRs have no reviews"""
        pull_requests = [
            {
                "merged_at": "2024-01-01",
                "comments": 0,
                "review_comments": 0,
                "requested_reviewers": [],
                "requested_teams": [],
            },
            {
                "merged_at": "2024-01-02",
                "comments": 0,
                "review_comments": 0,
                "requested_reviewers": [],
                "requested_teams": [],
            },
        ]
        model = StubModelData(
            modelLink="",
            codeLink=None,
            datasetLink=None,
            _github_metadata={"pull_requests": pull_requests},
        )
        self.run_metric_test(self.metric, model, 0.0)
