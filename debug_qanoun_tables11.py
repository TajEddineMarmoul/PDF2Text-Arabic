import fitz
import inspect
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
print(inspect.signature(doc[0].find_tables))
