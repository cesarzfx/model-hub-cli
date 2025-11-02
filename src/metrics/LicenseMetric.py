"""
LicenseMetric.py
================

Evaluates license compatibility of a model using cached metadata.

Inputs (from context)
---------------------
- HuggingFace model metadata (hf_metadata)
- GitHub repository metadata (github_metadata)

Scoring (0.0 – 1.0)
-------------------
- 1.0: Known license and fully compatible (e.g., MIT, Apache-2.0)
- 0.5: Unknown, ambiguous, or undetermined license
- 0.0: Known but incompatible license (e.g., GPL-3.0, AGPL-3.0, Proprietary)

Process
-------
1. Check license from HuggingFace metadata if available.
2. If not found, fallback to GitHub repository license.
3. Map detected license to compatibility score.

Limitations
-----------
- Only uses cached metadata, no live license detection.
- May misclassify if license metadata is missing or inconsistent.
"""

from typing import Dict

from loguru import logger

from src.Metric import Metric
from src.ModelData import ModelData


class LicenseMetric(Metric):
    LICENSE_COMPATIBILITY: Dict[str, float] = {
        # Compatible (1.0)
        "mit": 1.0,
        "bsd-2-clause": 1.0,
        "bsd-3-clause": 1.0,
        "lgpl-2.1": 1.0,
        "lgpl-2.1-or-later": 1.0,
        "gpl-2.0-or-later": 1.0,
        "apache-2.0": 1.0,
        # Ambiguous / Limited (0.5)
        "gpl-2.0": 0.5,
        "mpl-2.0": 0.5,
        "unlicense": 0.5,
        # Incompatible (0.0)
        "gpl-3.0": 0.0,
        "lgpl-3.0": 0.0,
        "agpl-3.0": 0.0,
        "proprietary": 0.0,
    }

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate the license compatibility of the model using cached metadata.

        Returns:
            float: Score from 0.0 (incompatible) to 1.0 (fully compatible).
        """
        logger.debug("Evaluating LicenseMetric...")

        license_id: str = "unknown"

        # Step 1: HuggingFace metadata
        hf_meta = model.hf_metadata
        if hf_meta:
            license_id = hf_meta.get("cardData", {}).get("license", "unknown")
            if license_id and license_id != "unknown":
                logger.debug(
                    "License found in HuggingFace metadata: {}", license_id
                )

        # Step 2: Fallback to GitHub if needed
        if license_id == "unknown":
            gh_meta = model.github_metadata
            if gh_meta:
                license_id = gh_meta.get("license", "unknown")
                if license_id and license_id != "unknown":
                    logger.debug(
                        "License found in GitHub metadata: {}", license_id
                    )

        # Step 3: Map to score
        license_key = license_id.lower() if license_id else "unknown"
        license_score = self.LICENSE_COMPATIBILITY.get(license_key, 0.5)

        logger.debug(
            "LicenseMetric: '{}' → score {}", license_key, license_score
        )
        return license_score
