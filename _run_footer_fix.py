"""Run the logic from test_footer_fix.ipynb as a plain script and write per-page PNGs."""
import os
import statistics
import fitz

PDFS = {
    "1978_p0": (r"download/قانون المالية 1978-1747912262117.pdf", 0),
    "2023_p1": (r"download/قانون-المالية-2023.pdf", 1),
    "2023_p14": (r"download/قانون-المالية-2023.pdf", 14),
}


def collect_candidates(page, clip, min_width_ratio):
    page_width = clip.x1 - clip.x0
    min_w = page_width * min_width_ratio
    out = []
    for d in page.get_drawings():
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2.0 and abs(p1.x - p2.x) >= min_w:
                    out.append((max(p1.y, p2.y), {"kind": "line", "w": abs(p1.x - p2.x)}))
            elif item[0] == "re":
                r = item[1]
                if r.height < 3.0 and r.width >= min_w:
                    out.append((r.y0, {"kind": "rect", "w": r.width, "h": r.height}))
    return out


def font_samples_around(page, clip, y, band=100):
    data = page.get_text("dict", clip=clip)
    above, below = [], []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line["spans"]:
                txt = span.get("text", "").strip()
                if not txt:
                    continue
                sz = span.get("size", 0)
                sy = (line["bbox"][1] + line["bbox"][3]) / 2
                if 0 < y - sy < band:
                    above.append(sz)
                elif 0 < sy - y < band:
                    below.append(sz)
    return above, below


def detect_footer_line_fixed(page, clip, table_bboxes,
                             min_width_ratio=0.05,
                             font_ratio=0.85,
                             min_samples_below=3):
    decisions = []
    if table_bboxes:
        return None, [(None, None, "SKIP_STRATEGY1_tables_present", {})]
    cands = collect_candidates(page, clip, min_width_ratio)
    if not cands:
        return None, decisions
    page_h = clip.y1 - clip.y0
    y_lo = clip.y0 + page_h * 0.30
    y_hi = clip.y0 + page_h * 0.90
    valid = []
    for y, meta in cands:
        if not (y_lo < y < y_hi):
            decisions.append((y, meta, "REJECT_y_bounds", {}))
            continue
        if any(b.y0 <= y <= b.y1 for b in table_bboxes):
            decisions.append((y, meta, "REJECT_inside_table", {}))
            continue
        above, below = font_samples_around(page, clip, y)
        if len(below) < min_samples_below:
            decisions.append((y, meta, "REJECT_too_few_below", {"n_below": len(below)}))
            continue
        if not above:
            decisions.append((y, meta, "REJECT_no_above", {}))
            continue
        m_above = statistics.median(above)
        m_below = statistics.median(below)
        ratio = m_below / m_above if m_above else 1.0
        if m_below >= m_above * font_ratio:
            decisions.append((y, meta, "REJECT_font_ratio",
                              {"above": round(m_above, 2), "below": round(m_below, 2),
                               "ratio": round(ratio, 3)}))
            continue
        decisions.append((y, meta, "ACCEPT",
                          {"above": round(m_above, 2), "below": round(m_below, 2),
                           "ratio": round(ratio, 3)}))
        valid.append(y)
    return (min(valid) if valid else None), decisions


def detect_footer_line_old(page, clip, min_width_ratio=0.15):
    best = None
    page_w = clip.x1 - clip.x0
    min_w = page_w * min_width_ratio
    cutoff = clip.y0 + (clip.y1 - clip.y0) * 0.2
    for d in page.get_drawings():
        for item in d.get("items", []):
            y = None
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2.0 and abs(p1.x - p2.x) >= min_w:
                    y = max(p1.y, p2.y)
            elif item[0] == "re":
                r = item[1]
                if r.height < 3.0 and r.width >= min_w:
                    y = r.y0
            if y is not None and clip.y0 < y < clip.y1 and y > cutoff:
                if best is None or y < best:
                    best = y
    return best


def render(pdf_path, page_num, label):
    print(f"\n{'='*70}\n{label}\n  {os.path.basename(pdf_path)} page {page_num}\n{'='*70}")
    if not os.path.exists(pdf_path):
        print("  missing file"); return
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    clip = page.rect
    tables = page.find_tables()
    table_bboxes = [fitz.Rect(t.bbox) for t in tables.tables]
    old_y = detect_footer_line_old(page, clip)
    new_y, decisions = detect_footer_line_fixed(page, clip, table_bboxes)
    print(f"  tables found:       {len(table_bboxes)}")
    print(f"  OLD (0.15 min-y):   {old_y}")
    print(f"  NEW (#1+#2):        {new_y}")
    for y, meta, verdict, extra in decisions:
        y_txt = f"{y:7.2f}" if y is not None else "   ---"
        print(f"    y={y_txt}  {verdict:<25}  {extra}")

    for b in table_bboxes:
        page.draw_rect(b, color=(0, 0, 1), width=1.5)
    for y, meta, verdict, extra in decisions:
        if y is None:
            continue
        color = (0, 0.7, 0) if verdict == "ACCEPT" else (0.6, 0.6, 0.6)
        page.draw_line(fitz.Point(clip.x0, y), fitz.Point(clip.x1, y),
                       color=color, width=1.2)
        page.insert_text((clip.x0 + 4, y - 2), verdict,
                         color=color, fontsize=7, fontname="helv")
    if old_y is not None and old_y != new_y:
        page.draw_line(fitz.Point(clip.x0, old_y), fitz.Point(clip.x1, old_y),
                       color=(1, 0, 0), width=1.0, dashes="[3 3] 0")
        page.insert_text((clip.x0 + 4, old_y - 2), "OLD-pick",
                         color=(1, 0, 0), fontsize=7, fontname="helv")
    if new_y is not None:
        band = fitz.Rect(clip.x0, new_y, clip.x1, clip.y1)
        page.draw_rect(band, color=None, fill=(1, 1, 0), fill_opacity=0.15)

    pix = page.get_pixmap(dpi=130)
    out = f"footer_fix_{label}.png"
    pix.save(out)
    print(f"  -> wrote {out}")
    doc.close()


if __name__ == "__main__":
    for label, (p, n) in PDFS.items():
        render(p, n, label)
