import unittest

from cost_analyzer import is_true


class TestIsTrue(unittest.TestCase):
    def test_rejects_empty_and_unicode_lookalike_values(self):
        """Only the documented ASCII spellings enable a boolean option."""
        for value in ("", "   ", "ｙｅｓ", "sí", "真"):
            with self.subTest(value=value):
                self.assertFalse(is_true(value))


if __name__ == "__main__":
    unittest.main()
