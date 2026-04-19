# Plan: Auto-Crop and Debug Visualization Improvements

## Objective
Implement automatic page number detection for cropping (`crop_top="auto"`, `crop_bottom="auto"`) and synchronize the debug visualization (`draw_page_layout`) to show exactly what the extraction pipeline filters out.

## Key Files
- `pdf2text_arabic/_extract.py`: Core extraction logic and cropping helpers.
- `pdf2text_arabic/debug.py`: Debug visualization tool for Jupyter/IPython.

## Implementation Steps

### 1. Enhance Cropping Logic in `_extract.py`
- Add a helper `_auto_detect_page_number_y(page, side="bottom")` to find the Y-coordinate of page numbers in margins.
- Update `_compute_clip` to accept the `page` object and handle `Literal["auto"]` for `crop_top` and `crop_bottom`.
    - If `crop_top="auto"`, it will scan the top 15% for a page number.
    - If `crop_bottom="auto"`, it will scan the bottom 15% for a page number.
- Update public API signatures (`extract_page`, `extract_pdf`, `extract_pdf_result`) to support `float | Literal["auto"]`.

### 2. Synchronize Debug Visualization in `debug.py`
- Update `draw_page_layout` signature to include `detect_footer: bool = True`.
- Update it to use the new `_compute_clip` (supporting `"auto"`).
- **Visualize Footers**:
    - Call `detect_footer_y` if `detect_footer` is True.
    - Draw a shaded rectangle over the detected footer region.
- **Visualize Filtered Page Numbers**:
    - Modify the block filtering logic. Instead of skipping page-number blocks, mark them as `type: "PAGE_NUM"`.
    - In the drawing loop, color `PAGE_NUM` blocks **Grey** and label them `PN`.
- **Visualize Crops**:
    - Ensure both manual and `"auto"` crop regions are shaded correctly.

## Verification
- Test `draw_page_layout` in a notebook with `crop_bottom="auto"` and `detect_footer=True`.
- Confirm that:
    - The page number is highlighted in grey and labelled `PN`.
    - The footer area is shaded.
    - The automated crop region matches the grey shaded area at the bottom.
- Verify that `extract_page` with the same parameters yields the expected text without the page number or footer.
