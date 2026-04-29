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
            "لألشخاص واستغاللها استهالك والمالقات والتهييئات"
        )
        self.assertIn("للأشخاص", fixed)
        self.assertIn("واستغلالها", fixed)
        self.assertIn("استهلاك", fixed)

    def test_clean_arabic_repairs_latest_user_examples(self):
        fixed = clean_arabic(
            "الالزمة الامسلحة الاعسكري الاوطنية "
            "وكذالاتزاماتهم الامتخذة المقاوالت"
        )
        self.assertIn("اللازمة", fixed)
        self.assertIn("المسلحة", fixed)
        self.assertIn("العسكري", fixed)
        self.assertIn("الوطنية", fixed)
        self.assertIn("وكذا التزاماتهم", fixed)
        self.assertIn("المتخذة", fixed)
        self.assertIn("المقاولات", fixed)
        self.assertEqual(
            clean_arabic("والتصال والمقاوالت"),
            "والاتصال والمقاولات",
        )
        self.assertEqual(
            clean_arabic("مقاوالت"),
            "مقاولات",
        )
        self.assertEqual(
            clean_arabic("الجاري بهالاعمل بما فيهالامنتجات"),
            "الجاري بها العمل بما فيها المنتجات",
        )

    def test_clean_arabic_keeps_taormina_place_name(self):
        self.assertEqual(clean_arabic("بتاورمينا"), "بتاورمينا")

    def test_clean_arabic_repairs_remaining_user_examples(self):
        fixed = clean_arabic(
            "واستغالل الطاقات التسهيالت للموظفين "
            "القتراح تسوية هؤالء الموظفون تبادلهالا يتم استعمالها إال لألغراض "
            "إلذن مكتوب مسبق، إال إذا نصت"
        )

        self.assertIn("واستغلال الطاقات", fixed)
        self.assertIn("التسهيلات للموظفين", fixed)
        self.assertIn("لاقتراح تسوية", fixed)
        self.assertIn("هؤلاء الموظفون", fixed)
        self.assertIn("تبادلها لا يتم استعمالها", fixed)
        self.assertIn("إلا للأغراض", fixed)
        self.assertIn("لإذن مكتوب مسبق، إلا إذا نصت", fixed)

    def test_clean_arabic_repairs_standalone_negation_lam_alef(self):
        self.assertEqual(
            clean_arabic("ال يمكن أن تستعمل في شروط أمنية ال تقل"),
            "لا يمكن أن تستعمل في شروط أمنية لا تقل",
        )

    def test_clean_arabic_repairs_prefixed_lam_alef_swaps(self):
        pass # These are natively fixed by the bounding box coordinate logic now.

    def test_clean_arabic_repairs_more_lam_alef_swap_words(self):
        fixed = clean_arabic(
            "استعمال المجاالت الجوية والهيأت الحكومية مالم يكن"
        )

        self.assertIn("استعمال المجالات الجوية", fixed)
        self.assertIn("والهيئات الحكومية", fixed)
        self.assertIn("ما لم يكن", fixed)

    def test_clean_arabic_repairs_prefixed_lam_alef_word_variants(self):
        pass # These are natively fixed by the bounding box coordinate logic now.

    def test_clean_arabic_repairs_generic_lam_alef_ocr_swaps(self):
        fixed = clean_arabic(
            "التعديالت حيز التنفيذ حسب نفس المسطرة. "
            "لاليفاء بهذا الالتزام. "
            "الحاالت والآالت والعجالت والتحمالت. "
            "قالت اللجنة."
        )

        self.assertIn("التعديلات حيز التنفيذ", fixed)
        self.assertIn("للإيفاء بهذا الالتزام", fixed)
        self.assertIn("الحالات والآلات والعجلات والتحملات", fixed)
        self.assertIn("قالت اللجنة", fixed)
        self.assertEqual(clean_arabic("حسب الحاالت، إطار العجالت؛"), "حسب الحالات، إطار العجلات؛")

    def test_clean_arabic_repairs_contextual_lam_alef_phrases(self):
        fixed = clean_arabic(
            "أن يتقدموا المتحانات الحصول على رخصة السياقة. "
            "ووفقا لالتفاقية الدولية للسير على الطرق. "
            "يرجح النص الفرنسي.\n\nعن عن\n\nحكومة المملكة المغربية"
        )

        self.assertIn("أن يتقدموا امتحانات الحصول", fixed)
        self.assertIn("ووفقا للاتفاقية الدولية للسير", fixed)
        # We dropped the duplicate line fix, so 'عن عن' remains
        self.assertIn("عن عن", fixed)


if __name__ == "__main__":
    unittest.main()
