from pathlib import Path

from azure_backend import extract_electrical_from_text
from pdf_reader import extract_pdf_text


pdf_path = Path("data/BAS16.pdf")
part_number = "BAS16"

text = extract_pdf_text(pdf_path, max_pages=5)

result = extract_electrical_from_text(
    pdf_text=text,
    part_number=part_number,
)

print(result.model_dump_json(indent=2))