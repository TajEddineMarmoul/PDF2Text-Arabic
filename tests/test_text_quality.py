import unittest

from pdf2text_arabic._text import clean_arabic, looks_like_scrambled_arabic


class ArabicTextQualityTests(unittest.TestCase):
    def test_detects_full_scrambled_arabic_text_layer(self):
        text = (
            "سداسلا دمحم كلملا ةلالجلا بحاص باطخ\n"
            "ةدعصألا عيمج ىلع اهرامث يطعت تأدب ،ةريخألا تاونسلا يف"
        )

        self.assertTrue(looks_like_scrambled_arabic(text))

    def test_does_not_flag_normal_arabic(self):
        text = (
            "خطاب صاحب الجلالة الملك محمد السادس إلى شعبه الوفي\n"
            "بدأت تعطي ثمارها على جميع الأصعدة في السنوات الأخيرة"
        )

        self.assertFalse(looks_like_scrambled_arabic(text))

    def test_detects_partial_scrambled_arabic_in_mixed_script_line(self):
        text = (
            "(DCI) Dénomination Commune Internationale "
            "ةكرتشملا ةيلودلا ةيمستلا )م-د-ت("
        )

        self.assertTrue(looks_like_scrambled_arabic(text))

    def test_clean_arabic_repairs_reversed_latin_and_parentheses(self):
        text = 'عدم احترام علامة "قف" )potS('

        self.assertEqual(clean_arabic(text), 'عدم احترام علامة "قف" (Stop)')

    def test_clean_arabic_keeps_normal_arabic_order(self):
        text = "خطاب صاحب الجلالة الملك محمد السادس"

        self.assertEqual(clean_arabic(text), text)

    def test_clean_arabic_repairs_mixed_script_arabic_run(self):
        text = (
            "(DCI) Dénomination Commune Internationale "
            "ةكرتشملا ةيلودلا ةيمستلا )م-د-ت("
        )

        self.assertIn(
            "التسمية الدولية المشتركة",
            clean_arabic(text),
        )

    def test_clean_arabic_repairs_two_word_reversed_arabic_term(self):
        self.assertIn(
            "حمض الفوسيديك",
            clean_arabic("- Acide Fusidique DCI م د ت كيديسوفلا ضمح -"),
        )

    def test_clean_arabic_hyphenates_known_dci_abbreviation(self):
        self.assertEqual(clean_arabic("DCI م د ت"), "DCI م-د-ت")

    def test_clean_arabic_repairs_joined_words_from_user_examples(self):
        fixed = clean_arabic(
            "خصائصهالاتقنية ومالءمة لهذالاغرض هذالاباب متنهالاطاقم"
        )
        self.assertIn("خصائصها التقنية", fixed)
        self.assertIn("وملاءمة", fixed)
        self.assertIn("لهذا الغرض", fixed)
        self.assertIn("هذا الباب", fixed)
        self.assertIn("متنها الطاقم", fixed)

    def test_clean_arabic_repairs_additional_user_examples(self):
        fixed = clean_arabic(
            "لألشخاص واستغاللها استهالك إصالحها صالبة إلعادة والمالقات والتهييئات"
        )
        self.assertIn("للأشخاص", fixed)
        self.assertIn("واستغلالها", fixed)
        self.assertIn("استهلاك", fixed)
        self.assertIn("إصلاحها", fixed)
        self.assertIn("صلبة", fixed)
        self.assertIn("لإعادة", fixed)
        self.assertIn("والملحقات", fixed)
        self.assertIn("والتهيئات", fixed)

    def test_clean_arabic_repairs_latest_user_examples(self):
        fixed = clean_arabic(
            "الإعالم الالزمة الامسلحة الاعسكري الاوطنية "
            "وكذالاتزاماتهم الامتخذة بالإعالم المقاوالت المالئمة"
        )
        self.assertIn("الإعلام", fixed)
        self.assertIn("اللازمة", fixed)
        self.assertIn("المسلحة", fixed)
        self.assertIn("العسكري", fixed)
        self.assertIn("الوطنية", fixed)
        self.assertIn("وكذا التزاماتهم", fixed)
        self.assertIn("المتخذة", fixed)
        self.assertIn("بالإعلام", fixed)
        self.assertIn("المقاولات", fixed)
        self.assertIn("الملائمة", fixed)
        self.assertEqual(
            clean_arabic("والإعالم والتصال والمقاوالت"),
            "والإعلام والاتصال والمقاولات",
        )
        self.assertEqual(
            clean_arabic("إعالم بإعالم مقاوالت ومالئمة"),
            "إعلام بإعلام مقاولات وملائمة",
        )
        self.assertEqual(
            clean_arabic("الجاري بهالاعمل بما فيهالامنتجات"),
            "الجاري بها العمل بما فيها المنتجات",
        )

    def test_clean_arabic_keeps_taormina_place_name(self):
        self.assertEqual(clean_arabic("بتاورمينا"), "بتاورمينا")


if __name__ == "__main__":
    unittest.main()
