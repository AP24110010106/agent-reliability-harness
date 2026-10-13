import unittest

import cost_analyzer


class TestCostAnalyzer(unittest.TestCase):

    def test_default_pricing_is_configured(self):
        self.assertEqual(
            cost_analyzer.DEFAULT_MODEL,
            "openai/gpt-oss-120b"
        )
        self.assertEqual(
            cost_analyzer.DEFAULT_INPUT_RATE,
            0.15
        )
        self.assertEqual(
            cost_analyzer.DEFAULT_OUTPUT_RATE,
            0.60
        )
        self.assertTrue(
            cost_analyzer.PRICING_SOURCE_URL.startswith(
                "https://console.groq.com/"
            )
        )


if __name__ == "__main__":
    unittest.main()
