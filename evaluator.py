import json
from pathlib import Path

import openpyxl


SPEC_FIELDS = {
    "max_length_mm": "Maximum Length (mm)",
    "max_width_mm": "Maximum Width (mm)",
    "max_height_mm": "Maximum Height (mm)",
    "pin_number": "PIN Number",
}


def close_enough(actual, expected, tolerance=0.02) -> bool:
    if actual is None or expected is None:
        return actual == expected

    try:
        return abs(float(actual) - float(expected)) <= tolerance
    except (TypeError, ValueError):
        return str(actual).strip() == str(expected).strip()


def load_specbook(path: str | Path) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    headers = list(rows[0])

    spec = {}
    for row in rows[1:]:
        record = dict(zip(headers, row))
        part_number = str(record["Part Number"]).strip()
        spec[part_number] = record

    return spec


def evaluate_dimensions(results_path: str | Path, specbook_path: str | Path) -> dict:
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    spec = load_specbook(specbook_path)

    report = {
        "overall": {"correct": 0, "total": 0, "accuracy": 0},
        "rows": [],
    }

    for part_number, expected_record in spec.items():
        actual_record = results.get(part_number, {})

        for actual_field, spec_field in SPEC_FIELDS.items():
            expected = expected_record.get(spec_field)
            actual = actual_record.get(actual_field)

            matched = close_enough(actual, expected)

            report["rows"].append({
                "part_number": part_number,
                "field": actual_field,
                "expected": expected,
                "actual": actual,
                "match": matched,
            })

            report["overall"]["total"] += 1
            if matched:
                report["overall"]["correct"] += 1

    total = report["overall"]["total"]
    correct = report["overall"]["correct"]
    report["overall"]["accuracy"] = correct / total if total else 0

    return report


if __name__ == "__main__":
    report = evaluate_dimensions(
        results_path="output/dimensions_results.json",
        specbook_path="data/specboook.xlsx",
    )

    for row in report["rows"]:
        symbol = "OK" if row["match"] else "NG"
        print(
            f"{symbol} {row['part_number']} {row['field']}: "
            f"expected={row['expected']} actual={row['actual']}"
        )

    overall = report["overall"]
    print()
    print(
        f"Dimension accuracy: "
        f"{overall['correct']}/{overall['total']} = {overall['accuracy'] * 100:.1f}%"
    )