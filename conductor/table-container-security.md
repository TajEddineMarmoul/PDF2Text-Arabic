# Plan: Implement 'Container Discard' Security Layer for Table Extraction

This plan adds a security layer to the table extraction engine. If a detected table fully contains another table, the outer (parent) table is discarded as a layout artifact (likely a multi-column page container), ensuring only real data tables are extracted.

## Objective
Enhance the robustness of the table detection pipeline by filtering out "container" tables that wrap more granular data tables.

## Key Files & Context
- `pdf2text_arabic/_tables.py`: The core table extraction logic where candidates are identified and processed.

## Implementation Steps

### 1. Update `extract_tables` in `pdf2text_arabic/_tables.py`
- Locate the section where the `candidates` list is finalized and sorted.
- Insert a "Containment Filter" loop that uses `fitz.Rect(t1.bbox).contains(fitz.Rect(t2.bbox))` to identify parent tables.
- Discard parent tables and only keep "leaf" tables in the final `candidates` list.

## Verification & Testing
- Run `audit_nested.py` again to ensure no regressions.
- Verify that standard multi-table pages (like Page 58) are still processed correctly (they are side-by-side, so they don't contain each other).
- Manually verify that any future layout-heavy PDFs correctly drop their container wrappers.
