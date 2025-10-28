"""
main.py
=======
CLI entry point for the Model Hub evaluation tool.

This script reads a CSV-style input file where each line includes up to three URLs
(model, code, dataset — in any order). It validates and classifies the URLs, evaluates
each model using a fixed set of metrics, and prints results to STDOUT in NDJSON format.

Responsibilities
----------------
- Validate environment and command-line arguments.
- Parse and classify URLs from the input file.
- Coordinate evaluation via the `ModelCatalogue` class.
- Output one NDJSON object per model to STDOUT.

Expected Input Format
---------------------
Each line must contain **exactly three comma-separated fields** in the following order:
    - Code repository URL (optional)
    - Dataset URL (optional)
    - Model URL (required)

Example:
    https://github.com/org/repo,https://dataset.url,https://huggingface.co/org/model

Environment
-----------
- `GITHUB_TOKEN` (required): Used to authenticate GitHub API requests.
- `LOG_LEVEL` (optional): Set to 1 (INFO) or 2 (DEBUG) to enable logging.
- `LOG_FILE` (optional): Path to a file where logs should be written.

Exit Codes
----------
- 0: Success
- 1: CLI, input, or evaluation error

Usage
-----
With helper script:
    $ ./run /absolute/path/to/input.txt

Or directly:
    $ python -m src.main /absolute/path/to/input.txt

Notes
-----
- URL validation and metadata fetching are handled by utilities and metric classes.
- Logging is optional and silent by default unless explicitly enabled.
- This module avoids direct network calls aside from GitHub token validation.
"""

import os
import sys
import requests

from loguru import logger

from src.Model import Model
from src.ModelCatalogue import ModelCatalogue


def validate_github_token() -> bool:
    """
    Validate the GITHUB_TOKEN environment variable.

    Returns:
        bool: True if token is valid, False otherwise
    """
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is not set")
        return False

    # Skip validation in test environment
    if any(x in sys.modules for x in ["pytest", "_pytest"]):
        logger.info("Skipping GitHub token validation in test environment")
        return True

    try:
        # Test token with a simple API call
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}",
        }

        # Use a simple API call to validate the token
        response = requests.get(
            "https://api.github.com/user", headers=headers, timeout=10
        )

        if response.status_code == 200:
            logger.info("GitHub token is valid")
            return True
        else:
            logger.error(
                f"GitHub token validation failed with status {response.status_code}"
            )
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Error validating GitHub token: {e}")
        return False


def run_catalogue(file_path: str) -> int:
    if not validate_github_token():
        logger.error("Invalid or missing GITHUB_TOKEN. Exiting.")
        return 1

    logger.info(f"Running model catalogue on file: {file_path}")
    catalogue = ModelCatalogue()

    try:
        with open(file_path, "r", encoding="ascii") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    logger.warning(f"Skipping empty line {line_num}")
                    continue

                # Parse URL Fields into Parts
                parts = [part.strip() for part in line.split(",")]

                # Exactly 3 URL Fields Must Exist
                if len(parts) != 3:
                    logger.error(
                        f"Line {line_num} must have 3 comma-separated fields: {line}"
                    )
                    return 1
                code_url, dataset_url, model_url = parts

                # Model URL Must Exist
                if not model_url:
                    logger.error(
                        f"Line {line_num} is missing a required model URL: {line}"
                    )
                    return 1

                try:
                    catalogue.addModel(Model([code_url, dataset_url, model_url]))
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    return 1

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error reading file: {e}")
        return 1

    catalogue.evaluateModels()
    print(catalogue.generateReport())
    return 0


def configure_logging() -> None:
    logger.remove()
    log_level_env = os.getenv("LOG_LEVEL", "0").strip()
    log_file = os.getenv("LOG_FILE", "").strip()

    if log_level_env == "2":
        log_level = "DEBUG"
    elif log_level_env == "1":
        log_level = "INFO"
    else:
        return  # Silent -- No Logging

    if log_file:
        try:
            if not os.path.exists(log_file):
                print(f"Log file does not exist: '{log_file}'")
                sys.exit(1)
            logger.add(log_file, rotation="1 MB", level=log_level)
        except Exception as e:
            print(f"Failed to configure log file '{log_file}': {e}")
            exit(1)
    else:
        logger.add(sys.stderr, level=log_level)


if __name__ == "__main__":
    # Prevent huggingface_hub from printing to stdout
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    configure_logging()
    if len(sys.argv) < 2:
        print("Usage: run <absolute_path_to_input_file>")
        sys.exit(1)
    sys.exit(run_catalogue(sys.argv[1]))
