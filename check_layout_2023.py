import fitz
import os


def check_pdf_layout(pdf_path):
    print(f"Checking layout for: {pdf_path}")
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc[i]
        width = page.rect.width
        height = page.rect.height

        # Check for vertical lines near the center
        paths = page.get_drawings()
        v_lines = []
        for p in paths:
            r = p["rect"]
            # Line is thin, tall, and near the middle X
            if (
                r.width < 3
                and r.height > height * 0.5
                and 0.4 * width < r.x0 < 0.6 * width
            ):
                v_lines.append(r)

        # Check for tables
        tables = page.find_tables() or []
        spanning_table = False
        for t in tables:
            # Table is wide (> 80% of page width)
            # t.bbox is (x0, y0, x1, y1)
            t_width = t.bbox[2] - t.bbox[0]
            if t_width > width * 0.8:
                spanning_table = True
                break

        # Check for text distribution
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

        selectable = len(text_blocks) > 0

        msg = f"Page {i:2}: "
        if v_lines:
            msg += f"LINE FOUND at X={v_lines[0].x0:.1f}. "
        else:
            msg += "NO LINE. "

        if spanning_table:
            msg += "SPANNING TABLE. "

        if not selectable:
            msg += "NOT SELECTABLE (Image). "
        else:
            msg += f"Selectable ({len(text_blocks)} blocks). "

        print(msg)
    doc.close()


if __name__ == "__main__":
    check_pdf_layout("download/قانون-المالية-2023.pdf")
