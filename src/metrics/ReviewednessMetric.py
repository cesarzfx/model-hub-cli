"""
ReviewednessMetric.py
=====================

Evaluates the fraction of code introduced through reviewed pull requests.

Signal
------
- Positive signal when a high percentage of merged pull requests have
  been reviewed
- Negative signal when code is merged without proper review processes

Inputs (from context)
---------------------
- GitHub repository metadata including:
    - Pull requests with review information
    - Merged vs unmerged pull requests

Heuristics
----------
- Count merged pull requests with at least one review
- Calculate fraction of reviewed PRs vs total merged PRs
- Consider projects with no PRs as having no reviewedness data (-1.0)

Scoring (0.0–1.0)
-----------------
- 0.0: No GitHub repository, no pull request data, or no reviewed PRs
- 0.0–1.0: Fraction of merged PRs that were reviewed before merging

Limitations
-----------
- Only considers the most recent 100 pull requests
- Does not account for the depth or quality of reviews
- Self-reviews and bot reviews are counted equally
- May not reflect current practices if repository is old

Note
----
This metric corresponds to the "Reviewedness" metric in the specification,
providing an estimate of code quality based on peer review practices.
"""

from typing import Any, Dict, List

from loguru import logger

from src.ModelData import ModelData
from src.Metric import Metric


class ReviewednessMetric(Metric):
    """
    Evaluates code reviewedness based on pull request review data.
    Returns:
        0.0-1.0 representing fraction of code introduced through reviewed PRs
        0.0 if no GitHub repository is available
    """

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate the reviewedness score for the given model.

        Args:
            model: ModelData object containing GitHub metadata

        Returns:
            float: Reviewedness score from 0.0 (no data/reviews) to 1.0 (all reviewed)
        """
        logger.debug("Evaluating ReviewednessMetric...")

        # Get GitHub metadata
        github_metadata = model.github_metadata
        if not github_metadata:
            logger.info("ReviewednessMetric: No GitHub metadata, using HF heuristic")
            hf_meta = model.hf_metadata or {}
            return self._heuristic_score(hf_meta)

        # Get pull requests data
        pull_requests = github_metadata.get("pull_requests", [])
        if not pull_requests:
            logger.info("ReviewednessMetric: No pull requests found → 0.0")
            return 0.0

        reviewedness_score = self._calculate_reviewedness(pull_requests)
        logger.debug("ReviewednessMetric: Calculated score {:.3f}", reviewedness_score)

        return reviewedness_score

    def _calculate_reviewedness(self, pull_requests: List[Dict[str, Any]]) -> float:
        """
        Calculate the fraction of merged PRs that were reviewed.

        Args:
            pull_requests: List of pull request objects from GitHub API

        Returns:
            float: Fraction of reviewed merged PRs (0.0 to 1.0)
        """
        if not pull_requests:
            return 0.0

        merged_prs = [pr for pr in pull_requests if pr.get("merged_at") is not None]

        if not merged_prs:
            logger.debug("No merged pull requests found")
            return 0.0

        # Count PRs with reviews
        # A PR is considered reviewed if it has:
        # - comments > 0 (review comments), OR
        # - review_comments > 0, OR
        # - requested_reviewers or requested_teams present
        reviewed_prs = []
        for pr in merged_prs:
            has_review = (
                pr.get("comments", 0) > 0
                or pr.get("review_comments", 0) > 0
                or len(pr.get("requested_reviewers", [])) > 0
                or len(pr.get("requested_teams", [])) > 0
            )
            if has_review:
                reviewed_prs.append(pr)

        reviewedness_fraction = len(reviewed_prs) / len(merged_prs)

        logger.debug(
            "Reviewedness calculation: {} reviewed PRs out of {} merged PRs",
            len(reviewed_prs),
            len(merged_prs),
        )

        return reviewedness_fraction

    def _heuristic_score(self, hf_meta: dict) -> float:
        """
        Heuristic reviewedness based on HuggingFace community engagement.
        """
        score = 0.0

        # High likes suggest community review
        likes = hf_meta.get("likes", 0)
        if likes > 100:
            score += 0.5
        elif likes > 30:
            score += 0.3
        elif likes > 10:
            score += 0.1

        # High downloads suggest usage and implicit review
        downloads = hf_meta.get("downloads", 0)
        if downloads > 50000:
            score += 0.4
        elif downloads > 10000:
            score += 0.2

        # Official library integration implies review
        if hf_meta.get("library_name") in ["transformers", "diffusers"]:
            score += 0.2

        return min(1.0, score)
