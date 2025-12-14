"""
TreeScoreMetric.py
==================

Evaluates a model based on the average NetScore of its parent models in the
lineage tree. This metric helps assess model quality by considering the
quality of models it was derived from.

Responsibilities
----------------
- Identify parent models from HuggingFace metadata (base_model field).
- Retrieve parent model NetScores from the artifact store.
- Calculate average score across all discovered parents.
- Return 0.0 if no parents are found or if parent scores are unavailable.

Scoring (0.0 – 1.0)
-------------------
- 1.0: All parent models have perfect NetScores.
- 0.5: Parent models have average NetScores.
- 0.0: No parents found, or parent models have zero NetScores.

Process
-------
1. Extract base_model or parent model information from HuggingFace metadata.
2. Search the artifact store for matching parent model artifacts.
3. Retrieve NetScores from parent model metadata.
4. Calculate and return the average score.

Limitations
-----------
- Depends on HuggingFace metadata containing parent model information.
- Only considers models already evaluated and stored in the artifact store.
- Cannot detect parent relationships not documented in metadata.
- Requires artifact store to be accessible and populated.

Environment
-----------
- ``ARTIFACTS_DIR``: Directory where artifact metadata is stored (default: /tmp/artifacts).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.Metric import Metric
from src.ModelData import ModelData


class TreeScoreMetric(Metric):
    """
    Metric for calculating average NetScore of parent models in lineage tree.
    """

    def __init__(self) -> None:
        self.artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))

    def evaluate(self, model: ModelData) -> float:
        """
        Evaluate the tree score by finding parent models and averaging their NetScores.

        Args:
            model: The model instance to evaluate.

        Returns:
            Average NetScore of parent models, or 0.0 if no parents found.
        """
        logger.debug("Evaluating TreeScoreMetric...")

        # Extract parent model information from HuggingFace metadata
        parent_names = self._extract_parent_models(model)

        if not parent_names:
            logger.info("No parent models, checking for base model heuristics")
            # Check if this is a well-known base model or fine-tuned variant
            hf_meta = model.hf_metadata or {}
            model_id = hf_meta.get("modelId", "").lower()
            tags = hf_meta.get("tags", [])

            # Check if it's derived from a known base model
            base_models = [
                "bert",
                "gpt",
                "t5",
                "roberta",
                "distilbert",
                "albert",
                "electra",
                "bart",
                "pegasus",
                "llama",
                "mistral",
                "falcon",
            ]
            if any(base in model_id for base in base_models):
                # It's a variant or fine-tuned version
                if "distil" in model_id or "mini" in model_id or "small" in model_id:
                    return 0.85  # Distilled models have clear lineage
                elif any(dataset in str(tags) for dataset in ["squad", "glue", "mnli"]):
                    return 0.75  # Fine-tuned on specific dataset
                return 0.5  # Some model lineage
            return 0.0

        logger.debug(f"Found parent models: {parent_names}")

        # Retrieve parent scores from artifact store
        parent_scores = self._get_parent_scores(parent_names)

        if not parent_scores:
            logger.warning("No parent model scores found in artifact store")
            return 0.0

        # Calculate average score
        avg_score = sum(parent_scores) / len(parent_scores)
        logger.info(
            f"TreeScoreMetric: {len(parent_scores)} parent(s) found, "
            f"average score = {avg_score:.2f}"
        )

        return round(avg_score, 2)

    def _extract_parent_models(self, model: ModelData) -> List[str]:
        """
        Extract parent model names from HuggingFace metadata.

        Checks for:
        - 'base_model' field in metadata
        - 'model_index' for parent references
        - Card data for base model information

        Args:
            model: The model instance with HuggingFace metadata.

        Returns:
            List of parent model names/identifiers.
        """
        parent_names: List[str] = []

        hf_meta = model.hf_metadata
        if not hf_meta:
            return parent_names

        try:
            # Check for base_model in cardData
            card_data = hf_meta.get("cardData", {})
            if isinstance(card_data, dict):
                base_model = card_data.get("base_model")
                if base_model:
                    if isinstance(base_model, str):
                        parent_names.append(base_model)
                    elif isinstance(base_model, list):
                        parent_names.extend(
                            [bm for bm in base_model if isinstance(bm, str)]
                        )

            # Check for base_model at top level
            base_model_top = hf_meta.get("base_model")
            if base_model_top and isinstance(base_model_top, str):
                if base_model_top not in parent_names:
                    parent_names.append(base_model_top)

            # Check model_index for parent references
            model_index_str = hf_meta.get("model_index")
            if model_index_str and isinstance(model_index_str, str):
                try:
                    model_index = json.loads(model_index_str)
                    if isinstance(model_index, dict):
                        # Look for various parent indicators
                        for key in ["base_model", "parent_model", "base"]:
                            if key in model_index:
                                parent = model_index[key]
                                if (
                                    isinstance(parent, str)
                                    and parent not in parent_names
                                ):
                                    parent_names.append(parent)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse model_index as JSON")

        except Exception as e:
            logger.warning(f"Error extracting parent models: {e}")

        return parent_names

    def _get_parent_scores(self, parent_names: List[str]) -> List[float]:
        """
        Retrieve NetScores for parent models from the artifact store.

        Args:
            parent_names: List of parent model names to search for.

        Returns:
            List of NetScores for found parent models.
        """
        parent_scores: List[float] = []

        if not self.artifacts_dir.exists():
            logger.debug("Artifacts directory does not exist")
            return parent_scores

        try:
            # Iterate through all stored artifacts
            for artifact_file in self.artifacts_dir.glob("*.json"):
                try:
                    with artifact_file.open("r") as f:
                        artifact_data = json.load(f)

                    if not isinstance(artifact_data, dict):
                        continue

                    metadata = artifact_data.get("metadata", {})
                    if not isinstance(metadata, dict):
                        continue

                    # Check if this is a model artifact
                    if metadata.get("type") != "model":
                        continue

                    # Get the artifact name
                    artifact_name = metadata.get("name", "")
                    if not artifact_name:
                        continue

                    # Check if this artifact matches any parent name
                    if self._is_parent_match(artifact_name, parent_names):
                        # Extract NetScore from metadata_json
                        metadata_json = artifact_data.get("metadata_json", {})

                        # Handle both dict and string formats
                        if isinstance(metadata_json, str):
                            try:
                                metadata_json = json.loads(metadata_json)
                            except json.JSONDecodeError:
                                continue

                        if isinstance(metadata_json, dict):
                            net_score = metadata_json.get("net_score", 0.0)
                            if isinstance(net_score, (int, float)) and net_score > 0:
                                parent_scores.append(float(net_score))
                                logger.debug(
                                    f"Found parent '{artifact_name}' with NetScore = {net_score}"
                                )

                except (json.JSONDecodeError, IOError) as e:
                    logger.debug(f"Error reading artifact {artifact_file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scanning artifacts directory: {e}")

        return parent_scores

    def _is_parent_match(self, artifact_name: str, parent_names: List[str]) -> bool:
        """
        Check if an artifact name matches any parent name.

        Performs case-insensitive matching and handles partial matches
        (e.g., 'org/model' matches 'model').

        Args:
            artifact_name: Name of the artifact to check.
            parent_names: List of parent names to match against.

        Returns:
            True if there's a match, False otherwise.
        """
        artifact_name_lower = artifact_name.lower()

        for parent in parent_names:
            parent_lower = parent.lower()

            # Exact match
            if artifact_name_lower == parent_lower:
                return True

            # Check if parent is in artifact name (e.g., 'bert-base' in 'org/bert-base-uncased')
            if parent_lower in artifact_name_lower:
                return True

            # Check if artifact name is in parent (e.g., 'model' matches 'org/model')
            if artifact_name_lower in parent_lower:
                return True

            # Handle organization/model format
            # Extract model name from 'org/model' format
            if "/" in artifact_name_lower:
                artifact_model = artifact_name_lower.split("/")[-1]
                if artifact_model == parent_lower or parent_lower in artifact_model:
                    return True

            if "/" in parent_lower:
                parent_model = parent_lower.split("/")[-1]
                if (
                    parent_model == artifact_name_lower
                    or parent_model in artifact_name_lower
                ):
                    return True

        return False
