from loguru import logger

from src.Metric import Metric
from src.ModelData import ModelData


class AvailabilityMetric(Metric):
    """
    Evaluates the availability of model resources by checking:
    1. HuggingFace model metadata availability
    2. GitHub repository metadata availability
    3. Dataset metadata availability

    Returns a score from 0.0 (unavailable) to 1.0 (fully available).
    """

    def evaluate(self, model: ModelData) -> float:
        logger.info("Evaluating AvailabilityMetric...")

        total_checks = 0
        successful_checks = 0

        # HuggingFace metadata availability (only count if code/dataset links exist)
        hf_meta = model.hf_metadata or {}
        has_meaningful_hf = bool(hf_meta.get("downloads") or hf_meta.get("likes"))

        # GitHub repo metadata
        if model.codeLink:
            total_checks += 1
            if model.github_metadata:
                successful_checks += 1
                logger.debug("GitHub repository metadata is available")
            else:
                logger.warning("GitHub repository metadata is missing")

        # Dataset metadata
        if model.datasetLink:
            total_checks += 1
            if model.dataset_metadata:
                successful_checks += 1
                logger.debug("Dataset metadata is available")
            else:
                logger.warning("Dataset metadata is missing")

        # If no code/dataset links, use HF metadata as fallback
        if total_checks == 0:
            if has_meaningful_hf:
                logger.info("No code/dataset links, using HF metadata availability")
                return 0.7  # Moderate score for HF-only models
            logger.warning("No resources to evaluate availability for")
            return 0.0

        score = successful_checks / total_checks
        logger.info(
            "AvailabilityMetric: {}/{} resources available -> {}",
            successful_checks,
            total_checks,
            score,
        )
        return score
