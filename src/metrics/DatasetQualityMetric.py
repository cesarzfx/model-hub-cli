"""
DatasetQualityMetric.py
=======================

Evaluates dataset quality using LLM analysis of dataset metadata.

Signals (examples)
------------------
- Dataset size and completeness
- Documentation quality and clarity
- Community engagement metrics (downloads, likes)
- Maintenance and recency indicators
- Academic backing and credibility

Inputs (from context)
---------------------
- Dataset metadata JSON (from model.dataset_metadata)
- Dataset link for logging and reference

Scoring (0.0 – 1.0)
-------------------
- Returns a float score indicating dataset quality
- Based on LLM assessment of metadata factors

Limitations
-----------
- Requires valid API key for external LLM service
- Dependent on quality and completeness of dataset metadata
- Relies on external API; subject to latency and availability
- Assumes LLM scoring is reliable and unbiased
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
from loguru import logger
import requests

from src.ModelData import ModelData
from src.Metric import Metric


class DatasetQualityMetric(Metric):
    """
    DatasetQualityMetric evaluates dataset quality using
    LLM analysis of dataset metadata.

    Scoring System:
    Uses Purdue GenAI Studio's LLM
    to analyze dataset metadata and return a quality score
    from 0.0 to 1.0 based on factors like:
    - Dataset size and completeness
    - Documentation quality
    - Community engagement (downloads, likes)
    - Maintenance and recency
    - Academic backing and credibility
    """

    def __init__(self) -> None:
        self.api_key: Optional[str] = os.getenv("GEN_AI_STUDIO_API_KEY")
        if not self.api_key:
            logger.warning(
                "GEN_AI_STUDIO_API_KEY not found in environment variables"
            )

        self.api_url: str = (
            "https://genai.rcac.purdue.edu/api/chat/completions"
        )
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate dataset quality using LLM analysis.
        Returns a score between 0.0 and 1.0.
        """
        try:
            # Get dataset metadata
            if not model.dataset_metadata:
                logger.warning(
                    f"No dataset metadata available for {model.datasetLink}"
                )
                return 0.0

            # Generate LLM prompt
            prompt: str = self._create_quality_prompt(model.dataset_metadata)

            # Get LLM assessment
            score: Optional[float] = self._get_llm_score(prompt)

            return score if score is not None else 0.0

        except Exception as e:
            logger.error(f"Error evaluating dataset quality: {e}")
            return 0.0

    def _create_quality_prompt(self, metadata: Dict[str, Any]) -> str:
        """Create a prompt for LLM to evaluate dataset quality."""

        # Convert metadata to formatted JSON string
        metadata_json: str = json.dumps(metadata, indent=2)

        prompt: str = f"""
You are an expert dataset evaluator.
Analyze the following dataset metadata JSON and provide a quality score from 0.0 to 1.0.

Dataset Metadata:
{metadata_json}

Evaluation Criteria:
1. Dataset Size & Completeness (0-0.3):
    File count, storage size, data volume, comprehensiveness
2. Documentation Quality (0-0.3): Description clarity, metadata completeness, tags,
    categorization
3. Community Engagement (0-0.2):
    Downloads, likes, usage indicators, popularity
4. Maintenance & Recency (0-0.2):

Please provide ONLY a numerical score between 0.0 and 1.0 as your response.
No explanation needed.
"""

        return prompt

    def _get_llm_score(self, prompt: str) -> Optional[float]:
        """Get quality score from LLM API."""
        try:
            body: Dict[str, Any] = {
                "model": "llama3.1:latest",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,  # We want a complete response, not streaming
            }

            response = requests.post(
                self.api_url, headers=self.headers, json=body
            )

            if response.status_code != 200:
                logger.error(
                    f"API request failed: {response.status_code}, {response.text}"
                )
                return None

            response_data: Dict[str, Any] = response.json()

            # Extract the content from the response
            if (
                "choices" in response_data
                and len(response_data["choices"]) > 0
            ):
                content: str = response_data["choices"][0]["message"][
                    "content"
                ].strip()

                # Try to parse the score from the response
                score: Optional[float] = self._parse_score(content)
                if score is not None:
                    logger.debug(f"LLM returned score: {score}")
                    return max(0.0, min(1.0, score))  # Clamp between 0 and 1
                else:
                    logger.warning(
                        f"Could not parse score from LLM response: {content}"
                    )

            return None

        except Exception as e:
            logger.error(f"Error getting LLM score: {e}")
            return None

    def _parse_score(self, content: str) -> Optional[float]:
        """Extract numerical score from LLM response."""
        try:
            # Look for decimal numbers
            matches: List[str] = re.findall(r"\b\d*\.?\d+\b", content)

            if matches:
                # Take the first number found
                score: float = float(matches[0])
                if 0.0 <= score <= 1.0:
                    return score
                # If score is > 1, assume it might be out of 10 or 100
                elif score <= 10:
                    return score / 10.0
                elif score <= 100:
                    return score / 100.0

            return None

        except (ValueError, IndexError):
            return None
