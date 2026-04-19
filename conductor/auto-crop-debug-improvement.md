# Plan: Auto-Crop and Debug Visualization Improvements

## Objective
Implement automatic page number detection for cropping (`crop_top="auto"`, `crop_bottom="auto"`) and synchronize the debug visualization (`draw_page_layout`) to show exactly what the extraction pipeline filters out.

## Key Files
- `pdf2text_arabic/_extract.py`: Core extraction logic and cropping helpers.
- `pdf2text_arabic/debug.py`: Debug visualization tool for Jupyter/IPython.

## Implementation Steps

### 1. Enhance Cropping Logic in `_extract.py`
- Add a helper `_auto_detect_top_y(page)` to find repeating headers (text or image) or page numbers.
- Add a helper `_auto_detect_bottom_y(page)` to find page numbers in the bottom margin.
- Update `_compute_clip` to use these helpers when `auto_crop_top` or `auto_crop_bottom` is True.
- Update public API signatures to use boolean flags with smart defaults.

### 2. Implement Smart OCR Region Merging
- Add `_merge_regions_safely(page, regions)` helper.
    - Clusters image regions that are vertically close.
    - Verifies that no selectable text exists in the gaps before merging.
- Update `_image_only_regions` to return consolidated, safer bboxes.
- This fixes the "khitab malak" edge case where 40+ tiny images were causing separate API calls.

### 3. Synchronize Debug Visualization in `debug.py`
- Update `draw_page_layout` to match the new boolean parameter logic and improved defaults.
- Ensure footer detection correctly trims the "Reading Order" boxes so no boxes appear over ignored footers.
- Use the updated unified `_is_page_number_block` for consistent filtering.

## Verification
- Run `draw_page_layout` on `khitab malak` to confirm fragmented images are now grouped.
- Run on `قانون المالية 1978` to confirm footnote numbers are no longer boxed.
- Confirm all existing PDFs process correctly with new defaults.
