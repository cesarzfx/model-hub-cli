"""
metadata_fetchers.py
====================

Fetchers for external metadata used in model evaluation.


Responsibilities
----------------
- Abstract interface (`MetadataFetcher`) for all metadata fetchers.
- Implementations for:
    - `HuggingFaceFetcher`: Fetches model metadata from Hugging Face API.
    - `GitHubFetcher`: Fetches repository data, license, contributors, stars,
      forks, and recent commits from GitHub API.
    - `DatasetFetcher`: Fetches dataset metadata from Hugging Face datasets API.


Typical Functions
-----------------
- `fetch_metadata(url: Optional[str]) -> Dict[str, Any]`:
    Each fetcher implements this method to extract structured metadata
    from its respective source, returning a dictionary of relevant fields.
    Returns an empty dictionary on failure or if URL is None.


Error Handling
--------------
- Logs and skips gracefully when:
    - URLs are missing or malformed.
    - Network requests fail or time out.
    - Expected response structure is missing.
- All fetchers return an empty dict `{}` on failure, never `None`.


Testing
-------
- Each fetcher is injectable with a `requests.Session` for easier testing/mocking.
- URL parsing and validation is deterministic and testable.
- No side effects beyond network I/O and logging.


Notes
-----
- GitHub rate limits are affected by `GITHUB_TOKEN`.
- All fetchers assume standard URL structures and may skip custom or unrecognized
    formats.
"""

from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from huggingface_hub import hf_hub_download
from loguru import logger


class MetadataFetcher:
    def fetch_metadata(self, url: Optional[str]) -> Dict[str, Any]:
        """Fetch metadata from the given URL."""
        raise NotImplementedError("Must be implemented by subclasses.")


class HuggingFaceFetcher(MetadataFetcher):
    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.BASE_API_URL = "https://huggingface.co/api/models"

    def fetch_metadata(self, url: Optional[str]) -> Dict[str, Any]:
        """Fetch Hugging Face model metadata."""
        metadata: Dict[str, Any] = {}

        # Verify URL Exists
        # - Should Always Exist for Model URLs
        if not url:
            logger.error("No model URL provided to HuggingFaceFetcher.")
            return metadata

        # Verify URL is a HuggingFace Model URL
        # - Should Always Be a HuggingFace Model URL
        parsed = urlparse(url)
        if "huggingface.co" not in parsed.netloc:
            logger.error(f"Unsupported model URL: {url}")
            return metadata

        # Parse URL to Extract Organization ID and Model ID
        # - Expect URL Format: huggingface.co/{organization}/{model_id}
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            logger.warning(f"Malformed HuggingFace model URL: {url}")
            return metadata

        organization, model_id = parts[0], parts[1]
        api_url = f"{self.BASE_API_URL}/{organization}/{model_id}"
        repo_id = f"{organization}/{model_id}"

        # Fetch General Model Metadata from Hugging Face API
        try:
            logger.debug(f"Fetching HF metadata from: {api_url}")
            resp = self.session.get(api_url, timeout=5)

            if resp.ok:
                logger.debug(f"HF metadata retrieved for model: {model_id}")
                metadata = resp.json()
            else:
                logger.warning(
                    f"Failed to retrieve HF metadata (HTTP {resp.status_code}) "
                    f"for {url}"
                )
        except Exception as e:
            logger.exception(f"Exception fetching HF metadata: {e}")

        # Fetch README.md
        try:
            readme_path = hf_hub_download(repo_id=repo_id, filename="README.md")
            with open(readme_path, "r", encoding="utf-8") as f:
                metadata["readme"] = f.read()
                logger.debug("Successfully fetched README.md from Hugging Face")
        except Exception as e:
            logger.warning(f"Failed to fetch README.md via huggingface_hub: {e}")

        # Fetch model_index.json
        try:
            model_index_path = hf_hub_download(
                repo_id=repo_id, filename="model_index.json"
            )
            with open(model_index_path, "r", encoding="utf-8") as f:
                metadata["model_index"] = f.read()
                logger.debug("Successfully fetched model_index.json from Hugging Face")
        except Exception as e:
            logger.warning(f"Failed to fetch model_index.json via huggingface_hub: {e}")

        return metadata


class GitHubFetcher(MetadataFetcher):
    def __init__(
        self,
        token: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.token = token
        self.session = session or requests.Session()
        self.BASE_API_URL = "https://api.github.com/repos"

    def fetch_metadata(self, url: Optional[str]) -> Dict[str, Any]:
        """Fetch GitHub repository metadata."""
        metadata: Dict[str, Any] = {}

        # Verify URL Exists
        # - May Not Exist if No Code Link Provided
        if not url:
            logger.info("No repository URL provided to GitHubFetcher.")
            return metadata

        # Verify URL is a Valid GitHub URL
        # - May Not Be a GitHub URL if Unsupported Code Link Provided
        parsed = urlparse(url)
        if "github.com" not in parsed.netloc:
            logger.info(f"URL is not a GitHub URL: {url}")
            return metadata

        # Parse URL to Extract Owner and Repository Name
        # - Expect URL Format: github.com/{owner}/{repo}
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            logger.warning(f"Malformed GitHub URL: {url}")
            return metadata

        owner, repo = parts[0], parts[1]
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            # Fetch contributors
            contributors_url = f"{self.BASE_API_URL}/{owner}/{repo}/contributors"
            logger.debug(f"Fetching GitHub contributors from: {contributors_url}")
            resp = self.session.get(contributors_url, headers=headers, timeout=5)
            if resp.ok:
                metadata["contributors"] = resp.json()
            else:
                logger.warning(
                    f"Failed to fetch contributors (HTTP {resp.status_code}) for {url}"
                )

            # Fetch license
            license_url = f"{self.BASE_API_URL}/{owner}/{repo}/license"
            logger.debug(f"Fetching GitHub license from: {license_url}")
            resp = self.session.get(license_url, headers=headers, timeout=5)
            if resp.ok:
                license = resp.json().get("license", {}).get("spdx_id")
                metadata["license"] = license
            else:
                logger.warning(
                    f"Failed to fetch license (HTTP {resp.status_code}) for {url}"
                )

            # Fetch repository info
            repo_url = f"{self.BASE_API_URL}/{owner}/{repo}"
            logger.debug(f"Fetching GitHub repository info from: {repo_url}")
            resp = self.session.get(repo_url, headers=headers, timeout=5)
            if resp.ok:
                repo_data = resp.json()
                metadata["clone_url"] = repo_data.get("clone_url")
                metadata["stargazers_count"] = repo_data.get("stargazers_count", 0)
                metadata["forks_count"] = repo_data.get("forks_count", 0)
            else:
                logger.warning(
                    f"Failed to fetch repository info (HTTP {resp.status_code}) "
                    f"for {url}"
                )

            # Fetch recent commit activity
            commits_url = f"{self.BASE_API_URL}/{owner}/{repo}/commits"
            logger.debug(f"Fetching GitHub commits from: {commits_url}")
            params = {"per_page": 100}
            commits_resp = self.session.get(commits_url, params=params, headers=headers)
            if commits_resp.ok:
                commits = commits_resp.json()
                metadata["commits_count"] = len(commits)
            else:
                logger.warning(
                    f"Failed to fetch commits (HTTP {resp.status_code}) for {url}"
                )

        except Exception as e:
            logger.exception(f"Exception fetching GitHub metadata: {e}")

        return metadata


class DatasetFetcher(MetadataFetcher):
    """Fetches dataset metadata from Hugging Face datasets API."""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.BASE_API_URL = "https://huggingface.co/api/datasets"

    def fetch_metadata(self, url: Optional[str]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}

        # Verify URL Exists
        # - May Not Exist if No Dataset Link Provided
        if not url:
            logger.debug("No dataset URL provided to DatasetFetcher.")
            return metadata

        # Verify URL is a HuggingFace Dataset URL
        # - May Not Be a HuggingFace URL if Unsupported Dataset Link Provided
        parsed = urlparse(url)
        if parsed.netloc != "huggingface.co":
            logger.warning(f"Unsupported dataset URL domain: {url}")
            return metadata

        # Parse URL to Extract Organization and Dataset ID
        # - Expect URL Format: huggingface.co/datasets/{organization}/{dataset_id}
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "datasets":
            logger.warning(f"Malformed dataset URL path: {url}")
            return metadata

        organization, dataset_id = parts[1], parts[2]
        api_url = f"{self.BASE_API_URL}/{organization}/{dataset_id}"

        # Fetch Metadata from HuggingFace Datasets API
        try:
            logger.debug(f"Fetching HF dataset metadata from: {api_url}")
            resp = self.session.get(api_url, timeout=5)
            if resp.ok:
                metadata = resp.json()
            else:
                logger.warning(
                    f"Failed to retrieve HF dataset metadata (HTTP {resp.status_code}) "
                    f"for {url}"
                )
        except Exception as e:
            logger.exception(f"Exception fetching HF dataset metadata: {e}")

        return metadata
