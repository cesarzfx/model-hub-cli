import re
from typing import Dict, Optional

from loguru import logger

from src.Metric import Metric
from src.ModelData import ModelData
from src.util.LLMClient import LLMClient


class RampUpMetric(Metric):
    def __init__(self) -> None:
        self.llm: LLMClient = LLMClient()

    def evaluate(self, model: ModelData) -> float:
        logger.debug("Evaluating Ramp Up Time Metric...")

        # Extract README
        hf_meta = model.hf_metadata or {}
        readme_maybe = hf_meta.get("readme")

        # Fallback heuristic if no README or LLM fails
        if not readme_maybe or not isinstance(readme_maybe, str):
            logger.warning("No README found, using HuggingFace metadata heuristics")
            return self._heuristic_score(hf_meta)

        readme_text: str = readme_maybe

        # Extract Relevant Sections
        readme_text = self._extract_relevant_sections(readme_text or "")

        # Construct the prompt for the LLM
        prompt: str = (
            "You are evaluating how easy it is for a new developer team to "
            "understand and use an AI model, based only on the provided README "
            "and model index.\n"
            "Score the model's 'ramp-up ease' from 0.0 (extremely difficult to "
            "learn) to 1.0 (extremely easy to learn). Your output must contain "
            "only a single float on the first line, with no additional "
            "explanation or commentary.\n"
            "To determine the score, award up to 0.20 points each for:\n"
            "- A clear and helpful README\n"
            "- Clear installation instructions\n"
            "- Usage examples\n"
            "- A dataset description\n"
            "- A training script\n"
            "Again, respond with a single float (e.g., 0.60) on the first line. "
            "You may include justifications *after* the score if needed, but "
            "only the first line will be used as the final metric.\n"
        )
        full_prompt: str = readme_text + "\n\n" + prompt

        # Query the LLM and extract the score
        response: Optional[str] = self.llm.send_prompt(full_prompt)
        score: float = self.llm.extract_score(response)

        # If LLM fails, use heuristic
        if score == 0.0 and response is None:
            logger.info("LLM failed, using heuristic score for RampUpMetric")
            return self._heuristic_score(hf_meta)

        logger.debug(f"Ramp Up Time Metric score: {score}")
        return score

    def _extract_relevant_sections(self, readme: str, max_chars: int = 8000) -> str:
        """
        Extract key sections from a long README to prepare a concise,
        high-signal LLM prompt.
        """
        if not readme:
            return ""

        sections_to_extract = {
            "Installation": ["installation", "setup", "getting started"],
            "Usage": ["usage", "how to use", "examples"],
            "Dataset": ["dataset", "data", "inputs"],
            "Training": ["training", "train", "fine-tune", "finetune"],
        }

        # Match H2/H3 markdown headings and their content
        pattern = re.compile(r"(#{2,3})\s+(.*)", re.IGNORECASE)
        matches = list(pattern.finditer(readme))

        # Extract sections based on headings
        extracted_sections: Dict[str, str] = {}
        for i, match in enumerate(matches):
            heading = match.group(2).strip().lower()
            content_start = match.end()
            content_end = (
                matches[i + 1].start() if i + 1 < len(matches) else len(readme)
            )
            content = readme[content_start:content_end].strip()

            # Check if this heading matches any target sections
            for section_name, keywords in sections_to_extract.items():
                if any(keyword in heading for keyword in keywords):
                    if section_name not in extracted_sections:
                        extracted_sections[section_name] = (
                            f"## {section_name}\n{content}"
                        )
                    break

        # Fallback: return first max_chars characters if no section found
        if not extracted_sections:
            return readme[:max_chars] + "\n..."

        combined = "\n\n".join(extracted_sections.values())
        return combined[:max_chars] + ("\n..." if len(combined) > max_chars else "")

    def _heuristic_score(self, hf_meta: dict) -> float:
        """
        Heuristic scoring based on HuggingFace metadata when LLM is unavailable.
        """
        score = 0.0

        # Base score from documentation presence
        if hf_meta.get("readme"):
            readme_len = len(str(hf_meta.get("readme", "")))
            if readme_len > 5000:
                score += 0.20  # Detailed README
            elif readme_len > 1000:
                score += 0.15  # Basic README
            elif readme_len > 100:
                score += 0.08  # Minimal README

        # Widget data indicates usage examples
        if hf_meta.get("widgetData") or hf_meta.get("cardData", {}).get("widget"):
            score += 0.15  # Has usage examples

        # Pipeline tag indicates clear use case
        if hf_meta.get("pipeline_tag"):
            score += 0.12  # Clear task definition

        # Popularity indicates community validation and documentation
        downloads = hf_meta.get("downloads", 0)
        likes = hf_meta.get("likes", 0)
        if downloads > 10000 or likes > 50:
            score += 0.20  # Popular models tend to have better docs
        elif downloads > 1000 or likes > 10:
            score += 0.12

        # ArXiv papers indicate academic documentation
        tags = hf_meta.get("tags", [])
        if any("arxiv:" in tag for tag in tags):
            score += 0.08

        return min(0.85, score)  # Cap at 0.85 for heuristic
