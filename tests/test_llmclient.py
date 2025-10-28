import pytest
from unittest.mock import patch, MagicMock
from src.util.LLMClient import LLMClient


class TestLLMClient:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = LLMClient()

    @patch("src.util.LLMClient.requests.post")
    def test_send_prompt_success(self, mock_post):
        # Arrange: mock a successful HTTP response with valid JSON content
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "0.75\nExplanation text"}}]
        }
        mock_post.return_value = mock_response

        prompt = "Test prompt"
        result = self.client.send_prompt(prompt)

        assert result == "0.75\nExplanation text"
        mock_post.assert_called_once()
        # Check that Authorization header includes the API key
        headers_passed = mock_post.call_args[1]["headers"]
        assert "Authorization" in headers_passed
        assert headers_passed["Authorization"].startswith("Bearer ")

    @patch("src.util.LLMClient.requests.post")
    def test_send_prompt_http_error(self, mock_post):
        # Arrange: simulate an HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP error")
        mock_post.return_value = mock_response

        prompt = "Test prompt"
        result = self.client.send_prompt(prompt)

        assert result is None
        mock_post.assert_called_once()

    @patch("src.util.LLMClient.requests.post")
    def test_send_prompt_invalid_json(self, mock_post):
        # Arrange: simulate a response that raises an exception when calling .json()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        prompt = "Test prompt"
        result = self.client.send_prompt(prompt)

        assert result is None
        mock_post.assert_called_once()

    def test_extract_score_valid_float(self):
        response = "0.85\nAdditional info"
        score = self.client.extract_score(response)
        assert score == 0.85

    def test_extract_score_out_of_range_high(self):
        response = "1.5\nSome text"
        score = self.client.extract_score(response)
        assert score == 1.0  # Clamped to 1.0

    def test_extract_score_out_of_range_low(self):
        response = "-0.2\nSome text"
        score = self.client.extract_score(response)
        assert score == 0.0  # Clamped to 0.0

    def test_extract_score_empty_response(self):
        score = self.client.extract_score("")
        assert score == 0.0

        score = self.client.extract_score(None)
        assert score == 0.0

    def test_extract_score_non_float(self):
        response = "Not a number\nMore text"
        score = self.client.extract_score(response)
        assert score == 0.0

    def test_extract_score_whitespace_and_float(self):
        response = "   0.42  \nExtra"
        score = self.client.extract_score(response)
        assert score == 0.42
