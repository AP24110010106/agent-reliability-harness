
import unittest

from reliability_harness import (
    CASE_LOOKUP,
    check_citations,
    check_concepts,
    classify_failure,
    grade,
    is_rate_limit_error,
)


class TestOfflineFaults(unittest.TestCase):

    def setUp(self):
        self.case = CASE_LOOKUP["Q14"]

        self.valid_output = {
            "success": True,
            "termination": "finish",
            "answer": (
                "RAM is volatile working memory, "
                "while an SSD provides persistent "
                "storage [S1]."
            ),
            "steps": 3,
            "tool_calls": 2,
            "input_tokens": 1000,
            "output_tokens": 300,
            "source_ids": ["S1"],
            "sources": {
                "S1": {
                    "url": "https://example.com/reference"
                }
            },
            "error": "",
        }

    def test_valid_answer_passes(self):
        passed, failure = grade(
            self.case,
            self.valid_output
        )

        self.assertTrue(passed)
        self.assertEqual(failure, "none")

    def test_missing_citation_fails(self):
        output = self.valid_output.copy()
        output["answer"] = (
            "RAM is volatile memory. "
            "SSD provides persistent storage."
        )

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "missing_citations"
        )

    def test_undeclared_citation_fails(self):
        output = self.valid_output.copy()
        output["answer"] = (
            "RAM and SSD are different [S2]."
        )

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "undeclared_citation"
        )

    def test_missing_expected_content_fails(self):
        output = self.valid_output.copy()
        output["answer"] = (
            "This technology stores information [S1]."
        )

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "missing_expected_content"
        )

    def test_token_limit_classification(self):
        output = self.valid_output.copy()
        output["success"] = False
        output["termination"] = "token_limit"

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "token_limit"
        )

    def test_iteration_limit_classification(self):
        output = self.valid_output.copy()
        output["success"] = False
        output["termination"] = "iteration_limit"

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "iteration_limit"
        )

    def test_groq_rate_limit_classification(self):
        output = self.valid_output.copy()
        output["success"] = False
        output["termination"] = "model_error"
        output["error"] = (
            "Error code: 429 - rate_limit_exceeded"
        )

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "rate_limit"
        )

    def test_http_429_detection(self):
        self.assertTrue(
            is_rate_limit_error(
                "Error code: 429"
            )
        )

    def test_normal_model_error(self):
        output = self.valid_output.copy()
        output["success"] = False
        output["termination"] = "model_error"
        output["error"] = "Invalid model response"

        passed, failure = grade(
            self.case,
            output
        )

        self.assertFalse(passed)
        self.assertEqual(
            failure,
            "model_error"
        )

    def test_valid_citation(self):
        passed, failure = check_citations(
            self.valid_output["answer"],
            self.valid_output["source_ids"],
            self.valid_output["sources"]
        )

        self.assertTrue(passed)
        self.assertEqual(failure, "none")


if __name__ == "__main__":
    unittest.main()
