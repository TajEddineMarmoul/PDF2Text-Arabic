# Arabic Document OCR Model Benchmarks (2026)

This document summarizes the real-time performance testing of various Vision-Language Models (VLMs) on complex Arabic legal documents (tables, titles, and dense text).

## 📊 Global Leaderboard

| Rank | Model | Parameters | Spelling Accuracy | Table Structure | Speed (avg) | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 🥇 | **DeepSeek-OCR** | 3B | **9.5/10** | 6/10 | 30s | **Best for Legal/Accuracy.** Most reliable text. |
| 🥉 | **HunyuanOCR (SFT)** | 1B | 7/10 | **10/10** | **9s** | **Speed Champion.** Fastest inference yet. |
| 4 | **olmOCR (AllenAI)**| 7B | 8/10 | 9/10 | 14s | **Best All-Rounder.** Stable native logic. |
| 4 | **Gemma 4 (Google)** | ?B | 6/10 | 9/10 | 61s | Good formatting, but "Western bias" in RTL. |
| 5 | **Qwen3-VL** | 4B | 6/10 | 9/10 | 47s | Great linguist, but semantic hallucinations. |
| 6 | **Qari-OCR** | 2B | 7/10 | 4/10 | 15s | Good styling, but broken table logic. |

---

## 🔍 Detailed Analysis

### 1. DeepSeek-OCR (3B)
*   **Strengths:** Unrivaled character recognition. Correctly identifies legal terms like `الجنحة` and `المخالفات` where every other model failed or "guessed."
*   **Weaknesses:** Messy raw table output. Splits single logical rows into multiple fragments.
*   **Fix:** Requires the custom Python `TableParser` (in `local_model_test.ipynb`) to merge rows by ID.

### 2. olmOCR-7B (AllenAI)
*   **Strengths:** Highly stable. Uses `<br>` tags inside cells to preserve multi-line text without breaking the table. Works perfectly even without a prompt.
*   **Weaknesses:** Visual hallucinations (e.g., writing `الجناية` instead of `الجنحة`).

### 3. HunyuanOCR (1B)
*   **Strengths:** Fastest model tested. Native HTML output is structurally perfect and needs zero post-processing.
*   **Weaknesses:** Visual typos due to small size (confuses `ح` with `ع`).

### 4. Gemma 4 (Google)
*   **Strengths:** Very clean Markdown table syntax and proper document hierarchy detection.
*   **Weaknesses:** Confuses column order in RTL documents. Swapped data columns in the "Violations" table. Slowest inference time.

### 5. Qwen3-VL (4B)
*   **Strengths:** Understands Arabic grammar well; adds Tashkeel (vowels) to titles correctly.
*   **Weaknesses:** "Semantic Hallucinations." Replaces difficult words with common ones (e.g., `سياقة` -> `مسافة`).

### 6. Qari-OCR-0.3 (2B)
*   **Strengths:** Understands rich text features like bolding and underlining in the original image.
*   **Weaknesses:** Table reconstruction is unstable; data frequently drifts between columns.

---

## 🏆 Final Recommendation for `pdf2text-arabic`

For high-precision Arabic document digitization, the **DeepSeek-OCR (3B)** pipeline is the winner. While others are faster or have better "table manners," DeepSeek is the only one that doesn't hallucinate the meaning of legal text.

**The Winning Pipeline:**
1. Use **DeepSeek-OCR (3B)** with the `<|grounding|>` prompt.
2. Use **Python Post-Processing** to clean tags and merge rows.

*Last Updated: 11 April 2026*
