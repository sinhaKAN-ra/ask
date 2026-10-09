"""Offline regression tests for slug generation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aolbeam_ask.ask import slugify


class SlugifyTests(unittest.TestCase):
    def test_normalizes_whitespace_case_and_punctuation(self):
        self.assertEqual(slugify("  Hello, World!  "), "hello-world")

    def test_empty_or_punctuation_only_input_uses_fallback(self):
        self.assertEqual(slugify(""), "conversation")
        self.assertEqual(slugify("!!!"), "conversation")

    def test_length_boundary_truncates_or_uses_fallback(self):
        self.assertEqual(slugify("alphabet", maxlen=5), "alpha")
        self.assertEqual(slugify("alphabet", maxlen=0), "conversation")

    def test_non_string_text_and_non_integer_length_are_rejected(self):
        for value in (None, 42):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    slugify(value)
        with self.assertRaises(TypeError):
            slugify("alphabet", maxlen="5")


if __name__ == "__main__":
    unittest.main()
