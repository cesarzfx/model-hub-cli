"""
ReproducibilityMetric.py
=========================

Evaluates whether demo code in the model card/repository works out of the box.

Scoring (3-Level System)
------------------------
- 1.0: Demo code executes successfully without any modifications
- 0.5: Demo code exists but requires debugging or minor fixes to run
- 0.0: No demo code found or code fails to execute

Process
-------
1. Check if GitHub repository exists and has demo/example code
2. Clone repository and locate demo files (demo.py, example.py, main.py, etc.)
3. Attempt to execute demo code with a 30-second timeout
4. Return score based on execution results

Requirements
------------
- GitHub metadata with repository structure
- Git installed and available in the environment
- Python modules: pathlib, subprocess, GitPython

Limitations
-----------
- Limited to 30-second execution timeout
- Only attempts Python (.py) and shell (.sh, .bash) scripts
- Does not install dependencies before running
- May fail on repositories requiring complex setup or environment variables
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import Repo
from git.exc import GitCommandError, GitError
from loguru import logger

from src.Metric import Metric
from src.ModelData import ModelData


class ReproducibilityMetric(Metric):
    """
    Evaluates whether demo code works out of the box.

    Scoring:
    - 1.0: Code executes successfully
    - 0.5: Code exists but fails execution (would work with debugging)
    - 0.0: No demo code found
    """

    # Common demo/example file patterns to search for
    DEMO_FILE_PATTERNS = [
        "demo.py",
        "example.py",
        "main.py",
        "run.py",
        "app.py",
        "examples/demo.py",
        "examples/example.py",
        "examples/main.py",
        "demo.sh",
        "run.sh",
    ]

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate whether demo code works out of the box.

        Args:
            model: ModelData object containing URLs and metadata

        Returns:
            float: 1.0 (works), 0.5 (exists but fails), or 0.0 (missing)
        """
        logger.info("Evaluating ReproducibilityMetric...")

        # Get GitHub metadata
        gh_meta = {}
        if getattr(model, "_github_metadata", None) and isinstance(
            getattr(model, "_github_metadata"), dict
        ):
            gh_meta = getattr(model, "_github_metadata")
        elif getattr(model, "github_metadata", None) and isinstance(
            getattr(model, "github_metadata"), dict
        ):
            gh_meta = getattr(model, "github_metadata")

        if not gh_meta:
            logger.info("ReproducibilityMetric: No GitHub metadata found → 0.0")
            return 0.0

        # Check if demo files exist in repository
        has_demo = self._has_demo_files(gh_meta)
        if not has_demo:
            logger.info("ReproducibilityMetric: No demo files found → 0.0")
            return 0.0

        clone_url = gh_meta.get("clone_url")
        if not clone_url:
            logger.info("ReproducibilityMetric: Demo exists but no clone URL → 0.5")
            return 0.5

        # Try to execute demo code
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                if self._clone_repository(clone_url, temp_dir):
                    execution_success = self._try_execute_demo(temp_dir)
                    if execution_success:
                        logger.info(
                            "ReproducibilityMetric: Demo executed successfully → 1.0"
                        )
                        return 1.0
                    else:
                        logger.info(
                            "ReproducibilityMetric: Demo exists but failed execution → 0.5"
                        )
                        return 0.5
                else:
                    logger.warning(
                        "ReproducibilityMetric: Clone failed, demo exists → 0.5"
                    )
                    return 0.5
        except Exception as e:
            logger.error("ReproducibilityMetric: Exception during eval: {}", e)
            return 0.5  # Demo exists but couldn't be tested

    def _has_demo_files(self, gh_meta: Dict[str, Any]) -> bool:
        """
        Check if repository contains demo/example files.

        Args:
            gh_meta: GitHub metadata dictionary

        Returns:
            bool: True if demo files found, False otherwise
        """
        tree = gh_meta.get("tree", [])
        if not tree:
            return False

        for item in tree:
            path = item.get("path", "").lower()
            # Only match exact demo patterns (not any .py file)
            for pattern in self.DEMO_FILE_PATTERNS:
                # Exact match only (e.g., "demo.py" or "examples/demo.py")
                # Do NOT match "src/main.py" when pattern is "main.py"
                if path == pattern.lower():
                    logger.debug("Found demo file: {}", path)
                    return True
        return False

    def _clone_repository(self, clone_url: str, temp_dir: str) -> bool:
        """
        Clone a repository into the given directory.

        Args:
            clone_url: Git clone URL
            temp_dir: Temporary directory path

        Returns:
            bool: True if successful, False otherwise
        """
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

    def _try_execute_demo(self, repo_path: str) -> bool:
        """
        Try to execute demo code in the repository.

        Args:
            repo_path: Path to cloned repository

        Returns:
            bool: True if any demo executes successfully, False otherwise
        """
        demo_files = self._find_demo_files(repo_path)

        if not demo_files:
            logger.debug("No demo files found in cloned repository")
            return False

        for demo_file in demo_files:
            try:
                logger.debug("Attempting to execute: {}", demo_file)

                # Determine how to run the file based on extension
                if demo_file.suffix == ".py":
                    result = subprocess.run(
                        ["python3", str(demo_file)],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                elif demo_file.suffix in [".sh", ".bash"]:
                    result = subprocess.run(
                        ["bash", str(demo_file)],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                else:
                    continue

                if result.returncode == 0:
                    logger.debug("Demo code executed successfully!")
                    return True
                else:
                    logger.debug(
                        "Demo returned non-zero exit code: {}", result.returncode
                    )

            except subprocess.TimeoutExpired:
                logger.debug("Demo execution timed out after 30 seconds")
            except Exception as e:
                logger.debug("Could not execute demo: {}", e)
                continue

        logger.debug("No demos executed successfully")
        return False

    def _find_demo_files(self, repo_path: str) -> List[Path]:
        """
        Find demo/example files to execute.

        Args:
            repo_path: Path to cloned repository

        Returns:
            List[Path]: List of paths to potential demo files
        """
        demo_files = []
        root = Path(repo_path)

        for pattern in self.DEMO_FILE_PATTERNS:
            # Try exact match first
            matches = list(root.glob(pattern))
            demo_files.extend(matches)

            # Try recursive search
            if "/" not in pattern:
                matches = list(root.glob(f"**/{pattern}"))
                demo_files.extend(matches)

        # Remove duplicates and sort by likely importance
        unique_files = list(set(demo_files))
        unique_files.sort(
            key=lambda x: (
                "demo" not in x.name.lower(),
                "example" not in x.name.lower(),
                len(str(x)),
            )
        )

        logger.debug("Found {} potential demo files", len(unique_files))
        return unique_files[:5]  # Limit to first 5 candidates
