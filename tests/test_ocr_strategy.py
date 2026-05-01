import unittest

from pdf2text_arabic._extract import _resolve_ocr_strategy


class OCRStrategyTests(unittest.TestCase):
    def test_default_strategy_preserves_existing_behavior(self):
        self.assertEqual(_resolve_ocr_strategy(), "warn")

    def test_new_strategy_values_are_used_directly(self):
        self.assertEqual(_resolve_ocr_strategy(ocr_strategy="auto"), "auto")
        self.assertEqual(_resolve_ocr_strategy(ocr_strategy="force"), "force")
        self.assertEqual(_resolve_ocr_strategy(ocr_strategy="never"), "never")

    def test_invalid_strategy_raises(self):
        with self.assertRaises(ValueError):
            _resolve_ocr_strategy(ocr_strategy="ocr")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
