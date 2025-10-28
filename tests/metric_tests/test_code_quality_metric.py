import pytest
from unittest.mock import patch, MagicMock
from typing import Any
from loguru import logger

from src.metrics.CodeQualityMetric import CodeQualityMetric
from tests.metric_tests.base_metric_test import BaseMetricTest


class TestCodeQualityMetric(BaseMetricTest):

    @pytest.fixture
    def metric(self) -> CodeQualityMetric:
        return CodeQualityMetric()

    @pytest.fixture
    def model_no_github(self, base_model: Any) -> Any:
        model = base_model
        model._github_metadata = None
        return model

    @pytest.fixture
    def model_popularity_only(self, base_model: Any) -> Any:
        model = base_model
        model._github_metadata = {
            "stargazers_count": 150,
            "forks_count": 30,
            "commits_count": 100,
        }
        return model

    @pytest.fixture
    def model_with_clone_url(self, base_model: Any) -> Any:
        model = base_model
        model._github_metadata = {
            "stargazers_count": 100,
            "forks_count": 20,
            "commits_count": 100,
            "clone_url": "https://github.com/test/repo.git",
        }
        return model

    def test_no_github_metadata(
        self, metric: CodeQualityMetric, model_no_github: Any
    ) -> None:
        logger.info("Testing CodeQualityMetric with no GitHub metadata...")
        score = metric.evaluate(model_no_github)
        assert score == 0.0

    def test_popularity_only_score(
        self, metric: CodeQualityMetric, model_popularity_only: Any
    ) -> None:
        logger.info("Testing CodeQualityMetric with popularity only...")
        score = metric.evaluate(model_popularity_only)
        assert score == pytest.approx(0.16, abs=0.01)

    @patch("src.metrics.CodeQualityMetric.Repo.clone_from")
    def test_clone_repository_success(
        self, mock_clone: MagicMock, metric: CodeQualityMetric
    ) -> None:
        logger.info("Testing successful repository cloning...")
        mock_clone.return_value = MagicMock()

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is True
        mock_clone.assert_called_once_with(
            "https://github.com/test/repo.git", "/tmp/test", depth=1
        )

    @patch("src.metrics.CodeQualityMetric.Repo.clone_from")
    def test_clone_repository_failure(
        self, mock_clone: MagicMock, metric: CodeQualityMetric
    ) -> None:
        logger.info("Testing repository cloning failure...")
        from git.exc import GitCommandError

        mock_clone.side_effect = GitCommandError("clone", "git clone failed")

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is False

    @patch("src.metrics.CodeQualityMetric.Repo.clone_from")
    def test_clone_repository_git_error(
        self, mock_clone: MagicMock, metric: CodeQualityMetric
    ) -> None:
        logger.info("Testing repository cloning git error...")
        from git.exc import GitError

        mock_clone.side_effect = GitError("git error")

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is False

    @patch("src.metrics.CodeQualityMetric.Repo.clone_from")
    def test_clone_repository_general_exception(
        self, mock_clone: MagicMock, metric: CodeQualityMetric
    ) -> None:
        logger.info("Testing repository cloning general exception...")
        mock_clone.side_effect = Exception("Unexpected error")

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is False

    def test_calculate_popularity_score(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing popularity score calculation...")

        # High stars and forks
        gh_meta = {"stargazers_count": 500, "forks_count": 100}
        score = metric._calculate_popularity_score(gh_meta)
        assert score == 0.2

        # Low stars and forks
        gh_meta = {"stargazers_count": 25, "forks_count": 5}
        score = metric._calculate_popularity_score(gh_meta)
        assert score == 0.0

    def test_calculate_commit_score(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing commit score calculation...")

        # High activity
        gh_meta = {"commits_count": 300.0}
        score = metric._calculate_commit_score(gh_meta)
        assert score == 0.3

        # Low activity
        gh_meta = {"commits_count": 10.0}
        score = metric._calculate_commit_score(gh_meta)
        assert score == 0.010

    @patch("src.metrics.CodeQualityMetric.Repo.clone_from")
    def test_full_evaluation_with_clone(
        self,
        mock_clone: MagicMock,
        metric: CodeQualityMetric,
        model_with_clone_url: Any,
    ) -> None:
        logger.info("Testing full evaluation with repository cloning...")

        mock_clone.return_value = MagicMock()

        with patch.object(
            metric, "_evaluate_testing_quality", return_value=0.2
        ), patch.object(metric, "_evaluate_documentation", return_value=0.15):

            score = metric.evaluate(model_with_clone_url)

            expected_score = 0.02 + 0.02 + 0.1 + 0.2 + 0.15
            assert score == pytest.approx(expected_score, abs=0.01)

    def test_evaluate_testing_quality(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing testing quality evaluation...")

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "tests"
            test_dir.mkdir()
            (test_dir / "test_file1.py").touch()
            (test_dir / "test_file2.py").touch()

            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            (src_dir / "source1.py").touch()
            (src_dir / "source2.py").touch()
            (src_dir / "source3.py").touch()

            score = metric._evaluate_testing_quality(temp_dir)
            assert score == pytest.approx(0.2, abs=0.01)

    def test_evaluate_documentation(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing documentation evaluation...")

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "README.md").touch()
            (Path(temp_dir) / "LICENSE").touch()
            (Path(temp_dir) / "CONTRIBUTING.md").touch()

            score = metric._evaluate_documentation(temp_dir)
            assert score == 0.20

    def test_count_test_files(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing test file counting...")

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_file1.py").touch()
            (tests_dir / "test_file2.py").touch()

            test_dir = Path(temp_dir) / "test"
            test_dir.mkdir()
            (test_dir / "test_file3.py").touch()

            count = metric._count_test_files(temp_dir)
            assert count == 3

    def test_count_source_files(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing source file counting...")

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "main.py").touch()
            (Path(temp_dir) / "utils.js").touch()
            (Path(temp_dir) / "config.ts").touch()
            (Path(temp_dir) / "README.md").touch()
            (Path(temp_dir) / "data.txt").touch()

            count = metric._count_source_files(temp_dir)
            assert count == 3

    def test_evaluation_with_clone_failure(
        self, metric: CodeQualityMetric, model_with_clone_url: Any
    ) -> None:
        logger.info("Testing evaluation when clone fails...")

        with patch.object(metric, "_clone_repository", return_value=False):
            score = metric.evaluate(model_with_clone_url)
            expected_score = 0.02 + 0.02 + 0.1
            assert score == pytest.approx(expected_score, abs=0.01)

    def test_score_capping_at_one(self, metric: CodeQualityMetric) -> None:
        logger.info("Testing score capping at 1.0...")

        model = MagicMock()
        model._github_metadata = {
            "stargazers_count": 10000,
            "forks_count": 1000,
            "avg_daily_commits_30d": 20.0,
            "clone_url": "https://github.com/test/repo.git",
        }

        # Mock successful clone and high analysis scores
        with patch.object(metric, "_clone_repository", return_value=True), patch.object(
            metric, "_evaluate_testing_quality", return_value=0.5
        ), patch.object(metric, "_evaluate_documentation", return_value=0.5):

            score = metric.evaluate(model)
            assert score == 1.0  # Should be capped at 1.0
