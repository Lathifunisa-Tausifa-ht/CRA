import sys
from PyPDF2 import PdfReader

filepath = sys.argv[1]
reader = PdfReader(filepath)

text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
print(f"Extracted text from {filepath}:\n")
print(text[:500], "...")  # preview first 500 chars