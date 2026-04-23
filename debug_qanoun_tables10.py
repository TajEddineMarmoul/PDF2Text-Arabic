import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
print(doc[0].find_tables.__doc__)
