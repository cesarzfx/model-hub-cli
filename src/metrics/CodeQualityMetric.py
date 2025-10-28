"""
CodeQualityMetric.py
====================

Evaluates code quality based on GitHub repository analysis.

Score Breakdown (Total: 1.0)
----------------------------
- Code Popularity (stars, forks): up to 0.2
- Test Suite Coverage (test files vs source files): up to 0.3
- Total Commits (up to 300 commits): up to 0.3
- Documentation presence (LICENSE, README, CONTRIBUTING): up to 0.2

Requirements
------------
- GitHub metadata with repository stats and clone URL
- Git installed and available in the environment
- Python modules: pathlib, subprocess, GitPython

Limitations
-----------
- Cloning may be slow or fail due to access or network issues
- Test file detection depends on naming and structure
- Documentation score is basic (file presence only)
- Git subprocess usage may pose security risks
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from git import Repo
from git.exc import GitCommandError, GitError
from loguru import logger

from src.ModelData import ModelData
from src.Metric import Metric


class CodeQualityMetric(Metric):
    """
    Evaluates code quality using GitHub metadata and repository content analysis.
    Score is based on:
    - Popularity (stars, forks)
    - Test Suite Coverage (test files vs source files)
    - Total Commits (up to 100 commits)
    - Documentation presence (LICENSE, README, CONTRIBUTING)
    """

    def __init__(self) -> None:
        self.temp_dirs: List[str] = []

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate code quality for the given model.

        Args:
            model: ModelData object containing URLs and metadata

        Returns:
            float: Code quality score from 0.0 to 1.0
        """
        logger.info("Evaluating CodeQualityMetric...")

        if not getattr(model, "_github_metadata", None):
            logger.info("CodeQualityMetric: No GitHub metadata found → 0.0")
            return 0.0

        gh_meta = model._github_metadata
        clone_url = gh_meta.get("clone_url")

        popularity_score = self._calculate_popularity_score(gh_meta)
        commit_score = self._calculate_commit_score(gh_meta)

        if not clone_url:
            total = popularity_score + commit_score
            logger.info(
                "CodeQualityMetric: No clone URL, returning base score {:.3f}", total
            )
            return min(total, 1.0)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                if self._clone_repository(clone_url, temp_dir):
                    test_score, doc_score = self._clone_and_analyze(temp_dir)
                    total = popularity_score + commit_score + test_score + doc_score
                    logger.info("Popularity Score: {:.3f}", popularity_score)
                    logger.info("Total Commits Score: {:.3f}", commit_score)
                    logger.info("Test Score: {:.3f}", test_score)
                    logger.info("Documentation Score: {:.3f}", doc_score)
                    logger.info(
                        "CodeQualityMetric: Full analysis score → {:.3f}", total
                    )
                    return min(total, 1.0)
                else:
                    logger.warning(
                        "CodeQualityMetric: Clone failed, returning base score only"
                    )
                    total = popularity_score + commit_score
                    return min(total, 1.0)
        except Exception as e:
            logger.error("CodeQualityMetric: Exception during eval: {}", e)
            total = popularity_score + commit_score
            return min(total, 1.0)

    def _calculate_popularity_score(self, gh_meta: Dict[str, Any]) -> float:
        """Calculate popularity score based on stars and forks."""
        stars = gh_meta.get("stargazers_count", 0)
        forks = gh_meta.get("forks_count", 0)

        star_score = min(stars // 50 * 0.01, 0.1)
        fork_score = min(forks // 10 * 0.01, 0.1)

        return star_score + fork_score

    def _calculate_commit_score(self, gh_meta: Dict[str, Any]) -> float:
        """Calculate commit score based on total number of commits.

        (max 0.3 for 300+ commits).
        """
        total_commits = gh_meta.get("commits_count", 0)

        # Linear scale: 0.001 points per commit, maxing out at 0.3 for 300 commits
        score = min(total_commits * 0.001, 0.3)

        logger.debug("Total commits: {} → commit score: {:.3f}", total_commits, score)
        return score

    def _clone_repository(self, clone_url: str, temp_dir: str) -> bool:
        """Clone a repository into the given directory. Returns True if successful."""
        logger.debug("Cloning repo: {} → {}", clone_url, temp_dir)
        try:
            Repo.clone_from(clone_url, temp_dir, depth=1)
            logger.debug("Clone succeeded.")
            return True
        except GitCommandError as e:
            logger.error("GitCommandError cloning {}: {}", clone_url, e)
        except GitError as e:
            logger.error("GitError cloning {}: {}", clone_url, e)
        except Exception as e:
            logger.error("Unexpected error cloning {}: {}", clone_url, e)
        return False

    def _clone_and_analyze(self, repo_path: str) -> tuple[float, float]:
        """Analyze the cloned repository and return (test_score, doc_score)."""
        test_score = self._evaluate_testing_quality(repo_path)
        doc_score = self._evaluate_documentation(repo_path)
        return test_score, doc_score

    def _evaluate_testing_quality(self, repo_path: str) -> float:
        """Evaluate testing quality based on ratio of test to source files."""
        test_files = self._count_test_files(repo_path)
        source_files = self._count_source_files(repo_path)

        if source_files == 0:
            return 0.0

        ratio = test_files / source_files
        return min(ratio * 0.3, 0.3)

    def _count_test_files(self, repo_path: str) -> int:
        """Count test files across all programming languages (no duplicates)."""
        test_patterns = [
            # Directory patterns
            "tests/**/*",
            "test/**/*",
            "**/tests/**/*",
            "**/test/**/*",
            "spec/**/*",
            "**/spec/**/*",
            "__tests__/**/*",
            "**/__tests__/**/*",
            "src/test/**/*",
            "**/src/test/**/*",
            # File patterns (these cover all the specific ones)
            "**/test_*.*",
            "**/*_test.*",
            "**/*Test.*",
            "**/*Tests.*",
            "**/*.test.*",
            "**/*.spec.*",
            "**/Test*.*",
        ]

        # Use a set to avoid counting the same file multiple times
        unique_files = set()
        for pattern in test_patterns:
            for file_path in Path(repo_path).glob(pattern):
                if file_path.is_file():  # Only count actual files
                    unique_files.add(str(file_path))

        count = len(unique_files)
        logger.debug("Test files found: {}", count)
        return count

    def _count_source_files(self, repo_path: str) -> int:
        """Count source files based on extensions in non-test folders."""
        source_extensions = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".php",
            ".rb",
            ".swift",
            ".kt",
            ".scala",
        }

        count = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {
                    "node_modules",
                    "venv",
                    "__pycache__",
                    "build",
                    "dist",
                    "tests",
                    "test",
                }
            ]
            for file in files:
                if Path(file).suffix.lower() in source_extensions:
                    count += 1
        logger.debug("Source files found: {}", count)
        return count

    def _evaluate_documentation(self, repo_path: str) -> float:
        """Evaluate documentation quality based on presence of key files."""
        logger.debug("Evaluating documentation in: {}", repo_path)
        score = 0.0
        found_docs = []

        if any(Path(repo_path).glob("LICENSE*")) or any(
            Path(repo_path).glob("license*")
        ):
            score += 0.05
            found_docs.append("LICENSE")

        if any(Path(repo_path).glob("README*")) or any(Path(repo_path).glob("readme*")):
            score += 0.05
            found_docs.append("README")

        if any(Path(repo_path).glob("CONTRIBUTING*")) or any(
            Path(repo_path).glob("contributing*")
        ):
            score += 0.10
            found_docs.append("CONTRIBUTING")

        logger.debug("Found docs: {} → doc score: {}", found_docs, score)
        return score
