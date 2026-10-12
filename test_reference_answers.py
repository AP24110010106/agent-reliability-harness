
import json
import unittest
from pathlib import Path

from reliability_harness import CASES, check_concepts


REFERENCE_FILE = Path(__file__).parent / "reference_answers.json"


class TestReferenceAnswers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with REFERENCE_FILE.open(
            "r", encoding="utf-8"
        ) as file:
            cls.references = json.load(file)

        cls.live_cases = [
            case for case in CASES
            if case.mode == "research"
        ]

    def test_all_20_cases_have_references(self):
        expected_ids = {
            case.id for case in self.live_cases
        }
        actual_ids = set(self.references)

        self.assertEqual(expected_ids, actual_ids)
        self.assertEqual(len(actual_ids), 20)

    def test_reference_answers_not_empty(self):
        for case in self.live_cases:
            with self.subTest(case=case.id):
                reference = self.references[case.id]

                self.assertTrue(
                    reference["reference_answer"].strip()
                )

    def test_required_concepts_match_cases(self):
        for case in self.live_cases:
            with self.subTest(case=case.id):
                reference = self.references[case.id]

                self.assertEqual(
                    reference["required_concepts"],
                    case.expected_terms
                )

    def test_reference_answers_pass_concept_checks(self):
        for case in self.live_cases:
            with self.subTest(case=case.id):
                answer = self.references[
                    case.id
                ]["reference_answer"]

                missing = check_concepts(case, answer)

                self.assertEqual(
                    missing,
                    [],
                    f"{case.id} missing concepts: {missing}"
                )


if __name__ == "__main__":
    unittest.main()
