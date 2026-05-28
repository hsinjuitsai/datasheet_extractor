import json
from pathlib import Path

import fitz

from azure_backend import extract_dimensions_from_images, extract_electrical_from_text
from pdf_reader import extract_pdf_text, render_page_to_png
from validators import validate_dimension_result


DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

RESULTS_PATH = OUTPUT_DIR / "full_results.json"


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


REQUIRED_FIELDS = [
    "Minimum Operating Temperature(°C)",
    "Maximum Operating Temperature (°C)",
    "Maximum Length (mm)",
    "Maximum Width (mm)",
    "Maximum Height (mm)",
    "PIN Number",
    "I_O、I_F (A)",
    "V_F(Forward Voltage) (V)",
    "V_RRM(Peak Repetitive Reverse Voltage) (V)",
    "I_R(Reverse Current) ",
]


def guess_part_number(pdf_path: Path) -> str:
    return PART_NAME_MAP.get(pdf_path.stem, pdf_path.stem)


def load_existing_results() -> dict:
    if RESULTS_PATH.exists():
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return {}


def save_results(results: dict) -> None:
    RESULTS_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_complete(record: dict) -> bool:
    if not record:
        return False

    if "_error" in record:
        return False

    return all(record.get(field) is not None for field in REQUIRED_FIELDS)


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

    print("[1/2] VLM dimensions")
    page_images = build_page_images(pdf_path)
    dimension_result = extract_dimensions_from_images(
        page_images=page_images,
        part_number=part_number,
    )

    dimension_data = dimension_result.model_dump()
    dimension_data, dimension_fixes = validate_dimension_result(dimension_data)

    if dimension_fixes:
        print("dimension validator fixes:")
        for fix in dimension_fixes:
            print(" -", fix)

    print(json.dumps(dimension_data, ensure_ascii=False, indent=2))

    print("[2/2] Text electrical")
    pdf_text = extract_pdf_text(pdf_path, max_pages=6)
    electrical_result = extract_electrical_from_text(
        pdf_text=pdf_text,
        part_number=part_number,
    )

    electrical_data = electrical_result.model_dump()
    print(json.dumps(electrical_data, ensure_ascii=False, indent=2))

    combined = {
        "Part Number": part_number,
        "Minimum Operating Temperature(°C)": electrical_data.get("min_operating_temp_c"),
        "Maximum Operating Temperature (°C)": electrical_data.get("max_operating_temp_c"),
        "Maximum Length (mm)": dimension_data.get("max_length_mm"),
        "Maximum Width (mm)": dimension_data.get("max_width_mm"),
        "Maximum Height (mm)": dimension_data.get("max_height_mm"),
        "PIN Number": dimension_data.get("pin_number"),
        "I_O、I_F (A)": electrical_data.get("io_if_a"),
        "V_F(Forward Voltage) (V)": electrical_data.get("vf"),
        "V_RRM(Peak Repetitive Reverse Voltage) (V)": electrical_data.get("vrrm_v"),
        "I_R(Reverse Current) ": electrical_data.get("ir"),
        "_dimension_evidence": dimension_data.get("evidence"),
        "_electrical_evidence": electrical_data.get("evidence"),
    }

    return combined


def main() -> None:
    pdf_paths = sorted(DATA_DIR.glob("*.pdf"))
    results = load_existing_results()

    for pdf_path in pdf_paths:
        part_number = guess_part_number(pdf_path)

        if is_complete(results.get(part_number, {})):
            print(f"[SKIP] {part_number}: already complete")
            continue

        try:
            results[part_number] = extract_one_pdf(pdf_path)
        except Exception as e:
            print(f"[ERROR] {part_number}: {e}")
            results[part_number] = {
                "Part Number": part_number,
                "_error": str(e),
            }

        save_results(results)

    save_results(results)
    print("\n已輸出：", RESULTS_PATH)


if __name__ == "__main__":
    main()