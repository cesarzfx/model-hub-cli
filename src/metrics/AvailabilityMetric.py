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

        # HuggingFace metadata availability (always counts)
        total_checks += 1
        if model.hf_metadata:
            successful_checks += 1
            logger.debug("HuggingFace metadata is available")
        else:
            logger.warning("HuggingFace metadata is missing")

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

        if total_checks == 0:
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
