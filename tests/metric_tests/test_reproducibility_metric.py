"""
Tests for ReproducibilityMetric.

Tests the 3-level scoring system:
- 1.0: Demo code works out of the box
- 0.5: Demo code exists but fails execution
- 0.0: No demo code found
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Any
from loguru import logger

from src.metrics.ReproducibilityMetric import ReproducibilityMetric
from tests.metric_tests.base_metric_test import BaseMetricTest


class TestReproducibilityMetric(BaseMetricTest):

    @pytest.fixture
    def metric(self) -> ReproducibilityMetric:
        return ReproducibilityMetric()

    @pytest.fixture
    def model_no_github(self, base_model: Any) -> Any:
        """Model with no GitHub metadata."""
        model = base_model
        model._github_metadata = None
        return model

    @pytest.fixture
    def model_no_demo_files(self, base_model: Any) -> Any:
        """Model with GitHub metadata but no demo files."""
        model = base_model
        model._github_metadata = {
            "clone_url": "https://github.com/test/repo.git",
            "tree": [
                {"path": "README.md"},
                {"path": "src/main.py"},
                {"path": "tests/test_main.py"},
            ],
        }
        return model

    @pytest.fixture
    def model_with_demo_no_clone(self, base_model: Any) -> Any:
        """Model with demo files but no clone URL."""
        model = base_model
        model._github_metadata = {
            "tree": [
                {"path": "demo.py"},
                {"path": "README.md"},
            ],
        }
        return model

    @pytest.fixture
    def model_with_demo_and_clone(self, base_model: Any) -> Any:
        """Model with demo files and clone URL."""
        model = base_model
        model._github_metadata = {
            "clone_url": "https://github.com/test/repo.git",
            "tree": [
                {"path": "demo.py"},
                {"path": "README.md"},
                {"path": "src/main.py"},
            ],
        }
        return model

    @pytest.fixture
    def model_with_example_file(self, base_model: Any) -> Any:
        """Model with example files in examples directory."""
        model = base_model
        model._github_metadata = {
            "clone_url": "https://github.com/test/repo.git",
            "tree": [
                {"path": "examples/example.py"},
                {"path": "README.md"},
            ],
        }
        return model

    # --- Test Cases for Score = 0.0 (No demo code) ---

    def test_no_github_metadata(
        self, metric: ReproducibilityMetric, model_no_github: Any
    ) -> None:
        """Should return 0.0 when no GitHub metadata is available."""
        logger.info("Testing ReproducibilityMetric with no GitHub metadata...")
        score = metric.evaluate(model_no_github)
        assert score == 0.0

    def test_no_demo_files_found(
        self, metric: ReproducibilityMetric, model_no_demo_files: Any
    ) -> None:
        """Should return 0.0 when no demo files are found in repository."""
        logger.info("Testing ReproducibilityMetric with no demo files...")
        score = metric.evaluate(model_no_demo_files)
        assert score == 0.0

    # --- Test Cases for Score = 0.5 (Demo exists but fails) ---

    def test_demo_exists_no_clone_url(
        self, metric: ReproducibilityMetric, model_with_demo_no_clone: Any
    ) -> None:
        """Should return 0.5 when demo exists but no clone URL available."""
        logger.info("Testing ReproducibilityMetric with demo but no clone URL...")
        score = metric.evaluate(model_with_demo_no_clone)
        assert score == 0.5

    @patch("git.Repo.clone_from")
    def test_clone_failure(
        self,
        mock_clone: MagicMock,
        metric: ReproducibilityMetric,
        model_with_demo_and_clone: Any,
    ) -> None:
        """Should return 0.5 when cloning fails."""
        logger.info("Testing ReproducibilityMetric when clone fails...")
        from git.exc import GitCommandError

        mock_clone.side_effect = GitCommandError("clone", "git clone failed")
        score = metric.evaluate(model_with_demo_and_clone)
        assert score == 0.5

    @patch("git.Repo.clone_from")
    def test_demo_execution_fails(
        self,
        mock_clone: MagicMock,
        metric: ReproducibilityMetric,
        model_with_demo_and_clone: Any,
    ) -> None:
        """Should return 0.5 when demo execution fails with non-zero exit code."""
        logger.info("Testing ReproducibilityMetric when demo execution fails...")
        mock_clone.return_value = MagicMock()

        with patch.object(metric, "_try_execute_demo", return_value=False):
            score = metric.evaluate(model_with_demo_and_clone)
            assert score == 0.5

    # --- Test Cases for Score = 1.0 (Demo works) ---

    @patch("git.Repo.clone_from")
    def test_demo_execution_succeeds(
        self,
        mock_clone: MagicMock,
        metric: ReproducibilityMetric,
        model_with_demo_and_clone: Any,
    ) -> None:
        """Should return 1.0 when demo executes successfully."""
        logger.info("Testing ReproducibilityMetric when demo executes successfully...")
        mock_clone.return_value = MagicMock()

        with patch.object(metric, "_try_execute_demo", return_value=True):
            score = metric.evaluate(model_with_demo_and_clone)
            assert score == 1.0

    # --- Helper Method Tests ---

    def test_has_demo_files_with_demo_py(self, metric: ReproducibilityMetric) -> None:
        """Should detect demo.py in repository tree."""
        logger.info("Testing _has_demo_files with demo.py...")
        gh_meta = {
            "tree": [
                {"path": "demo.py"},
                {"path": "src/main.py"},
            ]
        }
        assert metric._has_demo_files(gh_meta) is True

    def test_has_demo_files_with_example_py(
        self, metric: ReproducibilityMetric
    ) -> None:
        """Should detect example.py in repository tree."""
        logger.info("Testing _has_demo_files with example.py...")
        gh_meta = {
            "tree": [
                {"path": "examples/example.py"},
                {"path": "README.md"},
            ]
        }
        assert metric._has_demo_files(gh_meta) is True

    def test_has_demo_files_with_main_py(self, metric: ReproducibilityMetric) -> None:
        """Should detect main.py in repository tree."""
        logger.info("Testing _has_demo_files with main.py...")
        gh_meta = {
            "tree": [
                {"path": "main.py"},
                {"path": "utils.py"},
            ]
        }
        assert metric._has_demo_files(gh_meta) is True

    def test_has_demo_files_no_demo(self, metric: ReproducibilityMetric) -> None:
        """Should return False when no demo files exist."""
        logger.info("Testing _has_demo_files with no demo files...")
        gh_meta = {
            "tree": [
                {"path": "README.md"},
                {"path": "src/utils.py"},
                {"path": "tests/test_utils.py"},
            ]
        }
        assert metric._has_demo_files(gh_meta) is False

    def test_has_demo_files_empty_tree(self, metric: ReproducibilityMetric) -> None:
        """Should return False when tree is empty."""
        logger.info("Testing _has_demo_files with empty tree...")
        gh_meta = {"tree": []}
        assert metric._has_demo_files(gh_meta) is False

    def test_has_demo_files_no_tree(self, metric: ReproducibilityMetric) -> None:
        """Should return False when tree key is missing."""
        logger.info("Testing _has_demo_files with no tree key...")
        gh_meta = {}
        assert metric._has_demo_files(gh_meta) is False

    @patch("git.Repo.clone_from")
    def test_clone_repository_success(
        self, mock_clone: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should successfully clone repository."""
        logger.info("Testing successful repository cloning...")
        mock_clone.return_value = MagicMock()

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is True
        mock_clone.assert_called_once_with(
            "https://github.com/test/repo.git", "/tmp/test", depth=1
        )

    @patch("git.Repo.clone_from")
    def test_clone_repository_git_command_error(
        self, mock_clone: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should handle GitCommandError gracefully."""
        logger.info("Testing repository cloning with GitCommandError...")
        from git.exc import GitCommandError

        mock_clone.side_effect = GitCommandError("clone", "git clone failed")

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is False

    @patch("git.Repo.clone_from")
    def test_clone_repository_git_error(
        self, mock_clone: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should handle GitError gracefully."""
        logger.info("Testing repository cloning with GitError...")
        from git.exc import GitError

        mock_clone.side_effect = GitError("git error")

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is False

    @patch("git.Repo.clone_from")
    def test_clone_repository_general_exception(
        self, mock_clone: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should handle general exceptions gracefully."""
        logger.info("Testing repository cloning with general exception...")
        mock_clone.side_effect = Exception("Unexpected error")

        result = metric._clone_repository(
            "https://github.com/test/repo.git", "/tmp/test"
        )

        assert result is False

    @patch("subprocess.run")
    def test_try_execute_demo_success_python(
        self, mock_run: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should return True when Python demo executes successfully."""
        logger.info("Testing successful Python demo execution...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            demo_path = Path(temp_dir) / "demo.py"
            demo_path.write_text("print('Hello, World!')")

            # Mock successful execution
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            result = metric._try_execute_demo(temp_dir)

            assert result is True
            assert mock_run.called

    @patch("subprocess.run")
    def test_try_execute_demo_failure_python(
        self, mock_run: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should return False when Python demo fails with non-zero exit."""
        logger.info("Testing failed Python demo execution...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            demo_path = Path(temp_dir) / "demo.py"
            demo_path.write_text("raise Exception('Test error')")

            # Mock failed execution
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_run.return_value = mock_process

            result = metric._try_execute_demo(temp_dir)

            assert result is False

    @patch("subprocess.run")
    def test_try_execute_demo_timeout(
        self, mock_run: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should return False when demo execution times out."""
        logger.info("Testing demo execution timeout...")

        import tempfile
        from subprocess import TimeoutExpired

        with tempfile.TemporaryDirectory() as temp_dir:
            demo_path = Path(temp_dir) / "demo.py"
            demo_path.write_text("import time; time.sleep(60)")

            # Mock timeout
            mock_run.side_effect = TimeoutExpired(cmd="python3", timeout=30)

            result = metric._try_execute_demo(temp_dir)

            assert result is False

    def test_try_execute_demo_no_files(self, metric: ReproducibilityMetric) -> None:
        """Should return False when no demo files are found."""
        logger.info("Testing demo execution with no files...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            result = metric._try_execute_demo(temp_dir)
            assert result is False

    @patch("subprocess.run")
    def test_try_execute_demo_shell_script(
        self, mock_run: MagicMock, metric: ReproducibilityMetric
    ) -> None:
        """Should execute shell scripts successfully."""
        logger.info("Testing successful shell script execution...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            demo_path = Path(temp_dir) / "demo.sh"
            demo_path.write_text("#!/bin/bash\necho 'Hello'")

            # Mock successful execution
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            result = metric._try_execute_demo(temp_dir)

            assert result is True

    def test_find_demo_files(self, metric: ReproducibilityMetric) -> None:
        """Should find demo files in repository."""
        logger.info("Testing _find_demo_files...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create demo files
            (Path(temp_dir) / "demo.py").touch()
            (Path(temp_dir) / "example.py").touch()
            examples_dir = Path(temp_dir) / "examples"
            examples_dir.mkdir()
            (examples_dir / "demo.py").touch()

            demo_files = metric._find_demo_files(temp_dir)

            assert len(demo_files) > 0
            # Should find at least demo.py and example.py
            file_names = [f.name for f in demo_files]
            assert "demo.py" in file_names or "example.py" in file_names

    def test_find_demo_files_empty_directory(
        self, metric: ReproducibilityMetric
    ) -> None:
        """Should return empty list for empty directory."""
        logger.info("Testing _find_demo_files with empty directory...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            demo_files = metric._find_demo_files(temp_dir)
            assert len(demo_files) == 0

    def test_find_demo_files_sorting(self, metric: ReproducibilityMetric) -> None:
        """Should prioritize demo and example files in sorting."""
        logger.info("Testing _find_demo_files sorting...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple files
            (Path(temp_dir) / "demo.py").touch()
            (Path(temp_dir) / "example.py").touch()
            (Path(temp_dir) / "main.py").touch()
            (Path(temp_dir) / "run.py").touch()

            demo_files = metric._find_demo_files(temp_dir)

            # Demo and example should come first
            assert len(demo_files) > 0
            first_files = [f.name for f in demo_files[:2]]
            assert any("demo" in name for name in first_files) or any(
                "example" in name for name in first_files
            )

    def test_find_demo_files_limit(self, metric: ReproducibilityMetric) -> None:
        """Should limit results to 5 files."""
        logger.info("Testing _find_demo_files limit...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many demo files
            for i in range(10):
                (Path(temp_dir) / f"demo{i}.py").touch()

            demo_files = metric._find_demo_files(temp_dir)
            assert len(demo_files) <= 5

    # --- Integration Tests ---

    @patch("git.Repo.clone_from")
    @patch("subprocess.run")
    def test_full_evaluation_success(
        self,
        mock_run: MagicMock,
        mock_clone: MagicMock,
        metric: ReproducibilityMetric,
        model_with_demo_and_clone: Any,
    ) -> None:
        """Integration test: Full successful evaluation."""
        logger.info("Testing full successful evaluation...")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup mock clone
            mock_clone.return_value = MagicMock()

            # Create demo file
            demo_path = Path(temp_dir) / "demo.py"
            demo_path.write_text("print('Success')")

            # Mock successful execution
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            # Mock _clone_repository to use our temp_dir
            with patch.object(
                metric, "_clone_repository", return_value=True
            ), patch.object(metric, "_try_execute_demo", return_value=True):
                score = metric.evaluate(model_with_demo_and_clone)
                assert score == 1.0

    def test_exception_handling_during_evaluation(
        self, metric: ReproducibilityMetric, model_with_demo_and_clone: Any
    ) -> None:
        """Should handle exceptions gracefully and return 0.5."""
        logger.info("Testing exception handling during evaluation...")

        with patch.object(
            metric, "_clone_repository", side_effect=Exception("Unexpected error")
        ):
            score = metric.evaluate(model_with_demo_and_clone)
            assert score == 0.5
