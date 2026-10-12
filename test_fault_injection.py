
import unittest
from unittest.mock import patch

from reliability_harness import CASE_LOOKUP, execute


class TestFaultInjection(unittest.TestCase):

    def setUp(self):
        self.case = CASE_LOOKUP["Q14"]

    def make_agent_output(
        self,
        *,
        success=True,
        termination="finish",
        answer=None,
        error=None,
    ):
        if answer is None:
            answer = (
                "RAM is volatile memory while "
                "an SSD provides persistent storage [S1]."
            )

        return {
            "success": success,
            "termination": termination,
            "answer": answer,
            "iterations": 3,
            "tool_calls": 2,
            "input_tokens": 1000,
            "output_tokens": 200,
            "source_ids": ["S1"],
            "sources": {
                "S1": {
                    "url": "https://example.com/reference"
                }
            },
            "error": error,
        }

    @patch("reliability_harness.run_agent")
    def test_successful_agent_run(self, mock_agent):
        mock_agent.return_value = self.make_agent_output()

        result = execute(self.case, 1)

        self.assertTrue(result.passed)
        self.assertEqual(result.failure, "none")
        self.assertEqual(result.total_tokens, 1200)
        mock_agent.assert_called_once_with(
            self.case.question
        )

    @patch("reliability_harness.run_agent")
    def test_rate_limit_fault(self, mock_agent):
        mock_agent.side_effect = RuntimeError(
            "Error code: 429 - rate_limit_exceeded"
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(result.failure, "rate_limit")

    @patch("reliability_harness.run_agent")
    def test_network_timeout_fault(self, mock_agent):
        mock_agent.side_effect = TimeoutError(
            "Network request timed out"
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(result.failure, "runtime_error")
        self.assertEqual(result.termination, "exception")

    @patch("reliability_harness.run_agent")
    def test_malformed_agent_response(self, mock_agent):
        mock_agent.return_value = "invalid response"

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(result.failure, "runtime_error")

    @patch("reliability_harness.run_agent")
    def test_token_limit_fault(self, mock_agent):
        mock_agent.return_value = self.make_agent_output(
            success=False,
            termination="token_limit",
            answer="",
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(result.failure, "token_limit")

    @patch("reliability_harness.run_agent")
    def test_iteration_limit_fault(self, mock_agent):
        mock_agent.return_value = self.make_agent_output(
            success=False,
            termination="iteration_limit",
            answer="",
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(result.failure, "iteration_limit")

    @patch("reliability_harness.run_agent")
    def test_missing_citation_fault(self, mock_agent):
        mock_agent.return_value = self.make_agent_output(
            answer=(
                "RAM is volatile memory while "
                "SSD provides persistent storage."
            )
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(
            result.failure,
            "missing_citations"
        )

    @patch("reliability_harness.run_agent")
    def test_invalid_citation_fault(self, mock_agent):
        mock_agent.return_value = self.make_agent_output(
            answer=(
                "RAM is volatile memory while "
                "SSD provides persistent storage [S9]."
            )
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(
            result.failure,
            "undeclared_citation"
        )

    @patch("reliability_harness.run_agent")
    def test_missing_content_fault(self, mock_agent):
        mock_agent.return_value = self.make_agent_output(
            answer="This technology stores information [S1]."
        )

        result = execute(self.case, 1)

        self.assertFalse(result.passed)
        self.assertEqual(
            result.failure,
            "missing_expected_content"
        )


if __name__ == "__main__":
    unittest.main()
