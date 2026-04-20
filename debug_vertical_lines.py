import fitz

def count_long_vertical_lines(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    
    drawings = page.get_drawings()
    long_v_lines = 0
    
    for d in drawings:
        r = d["rect"]
        # Vertical line: width < 5 and height > 100
        if r.width < 5 and r.height > 100:
            long_v_lines += 1
            
    print(f"Page {p_num+1}: long_v_lines = {long_v_lines}")
    doc.close()

pdf = 'download/قانون-المالية-2023.pdf'
for p in [16, 23, 24, 115]:
    count_long_vertical_lines(pdf, p)