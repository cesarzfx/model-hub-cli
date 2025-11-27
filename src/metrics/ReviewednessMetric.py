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

Scoring (-1.0 or 0.0–1.0)
-------------------------
- -1.0: No GitHub repository or no pull request data available
- 0.0: No merged pull requests have been reviewed
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
        -1.0 if no GitHub repository is available
        0.0-1.0 representing fraction of code introduced through reviewed PRs
    """

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate the reviewedness score for the given model.

        Args:
            model: ModelData object containing GitHub metadata

        Returns:
            float: Reviewedness score from -1.0 (no data) to 1.0 (all reviewed)
        """
        logger.debug("Evaluating ReviewednessMetric...")

        # Get GitHub metadata
        github_metadata = model.github_metadata
        if not github_metadata:
            logger.info("ReviewednessMetric: No GitHub metadata found → -1.0")
            return -1.0

        # Get pull requests data
        pull_requests = github_metadata.get("pull_requests", [])
        if not pull_requests:
            logger.info("ReviewednessMetric: No pull requests found → -1.0")
            return -1.0

        reviewedness_score = self._calculate_reviewedness(pull_requests)
        logger.debug(
            "ReviewednessMetric: Calculated score {:.3f}", reviewedness_score
        )

        return reviewedness_score

    def _calculate_reviewedness(
        self, pull_requests: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate the fraction of merged PRs that were reviewed.

        Args:
            pull_requests: List of pull request objects from GitHub API

        Returns:
            float: Fraction of reviewed merged PRs (0.0 to 1.0)
        """
        if not pull_requests:
            return -1.0

        merged_prs = [
            pr for pr in pull_requests if pr.get("merged_at") is not None
        ]

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
