from pathlib import Path

from azure_backend import extract_dimensions_from_image
from pdf_reader import find_dimension_pages, render_page_to_png


pdf_path = Path("data/BAS16.pdf")
part_number = "BAS16"

dimension_pages = find_dimension_pages(pdf_path)
page_index = dimension_pages[0]
page_number = page_index + 1

image_path = render_page_to_png(pdf_path, page_index)

result = extract_dimensions_from_image(
    image_path=image_path,
    part_number=part_number,
    page_number=page_number,
)

print(result.model_dump_json(indent=2))