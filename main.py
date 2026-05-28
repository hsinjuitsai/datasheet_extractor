import json
from pathlib import Path

import fitz
from validators import validate_dimension_result
from azure_backend import extract_dimensions_from_images
from pdf_reader import render_page_to_png


DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


PART_NAME_MAP = {
    "1N4148W N0571 REV.E": "1N4148W",
    "BAS16": "BAS16",
    "BAS21HT1-D": "BAS21H",
    "BAT750": "BAT750",
    "BAV99W_datasheet_en_20171221": "BAV99W",
    "CD4148WTP": "CD4148WTP",
    "DFLS160": "DFLS160",
    "MBR15U150(TO-277)": "MBR15U150",
    "MSB30M": "MSB30M",
    "SBR05U20LPS": "SBR05U20LPS",
}


def guess_part_number(pdf_path: Path) -> str:
    return PART_NAME_MAP.get(pdf_path.stem, pdf_path.stem)


def build_page_images(pdf_path: Path) -> list[tuple[int, Path]]:
    doc = fitz.open(pdf_path)
    page_count = min(len(doc), 10)

    page_images = []
    for page_index in range(page_count):
        page_number = page_index + 1
        image_path = render_page_to_png(pdf_path, page_index)
        page_images.append((page_number, image_path))

    return page_images


def extract_one_pdf(pdf_path: Path) -> dict:
    part_number = guess_part_number(pdf_path)

    print(f"\n=== {part_number} ===")

    page_images = build_page_images(pdf_path)
    print("送入頁面：", [page_number for page_number, _ in page_images])

    result = extract_dimensions_from_images(
        page_images=page_images,
        part_number=part_number,
    )

    data = result.model_dump()
    data, fixes = validate_dimension_result(data)

    if fixes:
        print("validator fixes:")
    for fix in fixes:
        print(" -", fix)

    print(json.dumps(data, ensure_ascii=False, indent=2))

    return data


def main() -> None:
    pdf_paths = sorted(DATA_DIR.glob("*.pdf"))
    results = {}

    for pdf_path in pdf_paths:
        part_number = guess_part_number(pdf_path)

        try:
            results[part_number] = extract_one_pdf(pdf_path)
        except Exception as e:
            print(f"[ERROR] {part_number}: {e}")
            results[part_number] = {
                "part_number": part_number,
                "error": str(e),
            }

    output_path = OUTPUT_DIR / "dimensions_results.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n已輸出：", output_path)


if __name__ == "__main__":
    main()