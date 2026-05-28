import json
import re
from pathlib import Path

import openpyxl


FIELDS = [
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

NUMERIC_FIELDS = {
    "Minimum Operating Temperature(°C)",
    "Maximum Operating Temperature (°C)",
    "Maximum Length (mm)",
    "Maximum Width (mm)",
    "Maximum Height (mm)",
    "PIN Number",
    "I_O、I_F (A)",
    "V_RRM(Peak Repetitive Reverse Voltage) (V)",
}

TEXT_FIELDS = {
    "V_F(Forward Voltage) (V)",
    "I_R(Reverse Current) ",
}


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


def compare_numeric(actual, expected, tolerance=0.02) -> bool:
    if actual is None or expected is None:
        return actual == expected

    try:
        return abs(float(actual) - float(expected)) <= tolerance
    except (TypeError, ValueError):
        return str(actual).strip() == str(expected).strip()


def normalize_text(value) -> str:
    if value is None:
        return ""

    text = str(value).lower()
    text = text.replace("µ", "u").replace("μ", "u")
    text = text.replace("，", ",").replace("、", ",")
    text = text.replace("+", "")
    text = text.replace(" ", "")

    # Remove common condition labels but keep the values.
    text = re.sub(r"\b(vr|if|tj|ta|tamb|tc)\s*=", "", text)

    # Normalize temperatures.
    text = text.replace("°c", "c")

    # Normalize numeric strings: 1.00 -> 1, 1.0a -> 1a, 0.50 -> 0.5.
    def normalize_number(match):
        number = match.group(0)
        if "." in number:
            number = number.rstrip("0").rstrip(".")
        return number

    text = re.sub(r"\d+\.\d+", normalize_number, text)

    return text


def compare_text(actual, expected) -> bool:
    actual_text = normalize_text(actual)
    expected_text = normalize_text(expected)

    if not expected_text:
        return not actual_text

    expected_parts = [p for p in expected_text.split(",") if p]
    if not expected_parts:
        return actual_text == expected_text

    return all(part in actual_text for part in expected_parts)


def evaluate_full(results_path: str | Path, specbook_path: str | Path) -> dict:
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    spec = load_specbook(specbook_path)

    rows = []
    correct = 0
    total = 0

    for part_number, expected_record in spec.items():
        actual_record = results.get(part_number, {})

        for field in FIELDS:
            expected = expected_record.get(field)
            actual = actual_record.get(field)

            if field in NUMERIC_FIELDS:
                matched = compare_numeric(actual, expected)
            else:
                matched = compare_text(actual, expected)

            rows.append({
                "part_number": part_number,
                "field": field,
                "expected": expected,
                "actual": actual,
                "match": matched,
            })

            total += 1
            if matched:
                correct += 1

    return {
        "overall": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else 0,
        },
        "rows": rows,
    }


if __name__ == "__main__":
    report = evaluate_full(
        results_path="output/full_results.json",
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
        f"Full accuracy: "
        f"{overall['correct']}/{overall['total']} = {overall['accuracy'] * 100:.1f}%"
    )