"""
LLMClient.py
============

Provides a reusable interface for querying an LLM via the Purdue GenAI API,
primarily to support metric evaluations that rely on language model analysis.

Responsibilities
----------------
- Encapsulate all HTTP logic and error handling for LLM calls.
- Abstract away prompt formatting and parsing from metrics.
- Return float scores extracted from LLM output (if applicable).

Key Concepts
------------
- **Prompt**: A formatted string sent to the LLM to evaluate a model or document.
- **Score Extraction**: Pull a floating-point score (0.0–1.0) from the first line
  of the LLM response, used for metric scoring.
- **Model Selection**: Allows override of the default LLM model.

Typical Flow
------------
1. Instantiate `LLMClient`.
2. Call `send_prompt()` with your formatted input to receive a response string.
3. Call `extract_score(response)` to parse a numeric result.

Inputs & Outputs
----------------
- Input: Prompt string to be sent to the LLM.
- Output: Raw string response from the LLM or a numeric score extracted from it.

Error Handling
--------------
- Logs API failures, timeouts, and invalid responses.
- Returns safe fallback values (e.g. 0.0 score) on failure.
- Clamps out-of-range floats between 0.0 and 1.0.

Testing Notes
-------------
- Mock HTTP responses to test `send_prompt`.
- Provide sample completions to test `extract_score`.
"""

import os
from typing import Optional, Final

import requests
from loguru import logger


class LLMClient:
    DEFAULT_MODEL: Final[str] = "llama3.1:latest"
    API_URL: Final[str] = "https://genai.rcac.purdue.edu/api/chat/completions"

    def __init__(self) -> None:
        # Use provided key or fallback to environment variable
        self.api_key: str = os.getenv("GEN_AI_STUDIO_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "GEN_AI_STUDIO_API_KEY is not set. LLM requests may fail."
            )

    def send_prompt(
        self, prompt: str, model: Optional[str] = None
    ) -> Optional[str]:
        # Prepare Request Headers and Body
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, object] = {
            "model": model or self.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        try:
            # Make the HTTP POST request to the LLM API
            response: requests.Response = requests.post(
                self.API_URL,
                json=body,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            # Parse and return the content from the response
            json_data: dict = response.json()
            content: str = (
                json_data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            return content or None

        except Exception as e:
            logger.error(f"Failed to query LLM API: {e}")
            return None

    def extract_score(self, response: Optional[str]) -> float:
        # Return 0.0 if the response is empty or missing
        if not response:
            return 0.0

        try:
            # Extract the first line and parse it as a float
            first_line: str = response.splitlines()[0].strip()
            score: float = float(first_line)

            # Clamp the score to the valid range [0.0, 1.0]
            if not (0.0 <= score <= 1.0):
                logger.warning(f"Score out of range: {score}, clamping.")
                return max(0.0, min(1.0, score))

            return score

        except ValueError:
            logger.warning(f"Could not parse score from response: {response}")
            return 0.0
