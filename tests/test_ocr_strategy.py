import unittest
import warnings

from pdf2text_arabic._extract import _resolve_ocr_strategy


class OCRStrategyTests(unittest.TestCase):
    def test_default_strategy_preserves_existing_behavior(self):
        self.assertEqual(_resolve_ocr_strategy(), "warn")

    def test_new_strategy_values_are_used_directly(self):
        self.assertEqual(_resolve_ocr_strategy(ocr_strategy="auto"), "auto")
        self.assertEqual(_resolve_ocr_strategy(ocr_strategy="force"), "force")
        self.assertEqual(_resolve_ocr_strategy(ocr_strategy="never"), "never")

    def test_on_empty_is_deprecated_compatibility_alias(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            strategy = _resolve_ocr_strategy(on_empty="ocr")

        self.assertEqual(strategy, "force")
        self.assertTrue(
            any(item.category is DeprecationWarning for item in caught),
            "on_empty should emit a DeprecationWarning",
        )

    def test_old_on_empty_values_map_to_new_strategy_names(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.assertEqual(_resolve_ocr_strategy(on_empty="ignore"), "never")
            self.assertEqual(_resolve_ocr_strategy(on_empty="warn"), "warn")
            self.assertEqual(_resolve_ocr_strategy(on_empty="auto"), "auto")
            self.assertEqual(_resolve_ocr_strategy(on_empty="ocr"), "force")

    def test_conflicting_new_and_old_options_raise(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with self.assertRaises(ValueError):
                _resolve_ocr_strategy(ocr_strategy="auto", on_empty="ocr")


if __name__ == "__main__":
    unittest.main()
