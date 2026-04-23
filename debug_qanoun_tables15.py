import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._text import merge_lines_by_y, build_row_text, clean_arabic

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    t_def = page.find_tables(clip=clip)
    if t_def.tables:
        t = t_def.tables[0]
        if len(t.rows) == 1 and len(t.header.cells) > 2:
            print(f"Table has 1 row and {len(t.header.cells)} columns. Splitting manually by Y.")
            
            rawdict = page.get_text("rawdict", clip=fitz.Rect(t.bbox))
            
            # Map of row_y -> list of cells
            rows_map = {}
            
            for ci, cell in enumerate(t.rows[0].cells):
                if not cell: continue
                x0, y0, x1, y1 = cell
                
                # Extract lines for this cell
                lines_all = []
                for block in rawdict["blocks"]:
                    if "lines" not in block: continue
                    for line in block["lines"]:
                        filtered_spans = []
                        for span in line["spans"]:
                            filtered_chars = []
                            for ch in span["chars"]:
                                cx = (ch["bbox"][0] + ch["bbox"][2]) / 2
                                cy = (ch["bbox"][1] + ch["bbox"][3]) / 2
                                if x0 - 0.5 <= cx <= x1 + 0.5 and y0 - 0.5 <= cy <= y1 + 0.5:
                                    filtered_chars.append(ch)
                            if filtered_chars:
                                new_span = dict(span)
                                new_span["chars"] = filtered_chars
                                filtered_spans.append(new_span)
                        if filtered_spans:
                            new_line = dict(line)
                            new_line["spans"] = filtered_spans
                            lines_all.append(new_line)
                
                if not lines_all: continue
                merged = merge_lines_by_y(lines_all)
                for row in merged:
                    cy = row["cy"]
                    text = clean_arabic(build_row_text(row["spans"])).strip()
                    if text:
                        # Find an existing row that is within a small tolerance (e.g. 5 pixels)
                        found_y = None
                        for ry in rows_map.keys():
                            if abs(ry - cy) < 5.0:
                                found_y = ry
                                break
                        if found_y is None:
                            found_y = cy
                            rows_map[found_y] = {i: "" for i in range(len(t.header.cells))}
                        
                        rows_map[found_y][ci] = text
            
            # Sort the rows by Y
            sorted_ys = sorted(rows_map.keys())
            print(f"Constructed {len(sorted_ys)} rows.")
            for ry in sorted_ys[:5] + sorted_ys[-5:]: # Print first 5 and last 5
                row_data = [rows_map[ry][ci] for ci in range(len(t.header.cells))]
                print(f"  Y={ry:.1f}: {row_data}")
