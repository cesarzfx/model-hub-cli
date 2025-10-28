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
        readme_text: Optional[str] = model.hf_metadata.get("readme")
        if not readme_text:
            logger.warning(
                "No README.md or model_index.json data found in model metadata; "
                "returning 0.0 score."
            )
            return 0.0

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
        response: str = self.llm.send_prompt(full_prompt)
        score: float = self.llm.extract_score(response)

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
