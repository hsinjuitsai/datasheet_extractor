import re
from copy import deepcopy


FIELD_TO_KEYWORDS = {
    "max_length_mm": ["length", "max length"],
    "max_width_mm": ["width", "max width"],
    "max_height_mm": ["height", "thickness", "max height"],
}


def _round_value(value: float) -> float:
    return round(float(value), 6)


def _extract_assignment_values(evidence: str) -> dict:
    """
    Extract clear statements like:
    - length = 8.60 mm
    - width = 6.70 mm
    - height = 1.50 mm
    - max height = 1.15 mm
    """
    values = {}

    patterns = {
        "max_length_mm": r"(?:max\s+)?length\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*mm",
        "max_width_mm": r"(?:max\s+)?width\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*mm",
        "max_height_mm": r"(?:max\s+)?height\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*mm",
    }

    for field, pattern in patterns.items():
        matches = re.findall(pattern, evidence, flags=re.IGNORECASE)
        if matches:
            values[field] = _round_value(matches[-1])

    return values


def _extract_symbol_max_values(evidence: str) -> dict:
    """
    Extract clear symbol max statements like:
    - A max = 1.50 mm
    - E1 max 8.60 mm
    - D = 6.50/6.70/6.60 mm
    """
    symbol_values = {}

    # A max = 1.50 mm
    for symbol, value in re.findall(
        r"\b([A-Z][A-Z0-9]*)\s+max\s*=?\s*([0-9]+(?:\.[0-9]+)?)\s*mm",
        evidence,
        flags=re.IGNORECASE,
    ):
        symbol_values[symbol.upper()] = _round_value(value)

    # A = 1.30/1.50/1.40 mm → treat middle value as Max for common Min/Max/Typ prose
    for symbol, v1, v2, v3 in re.findall(
        r"\b([A-Z][A-Z0-9]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*mm",
        evidence,
        flags=re.IGNORECASE,
    ):
        symbol_values[symbol.upper()] = _round_value(v2)

    # A = 0.90/1.15/1.025 mm style without spaces
    return symbol_values


def validate_dimension_result(record: dict) -> tuple[dict, list[str]]:
    """
    Conservative post-processing:
    1. If evidence explicitly says length/width/height = X mm, make JSON match it.
    2. If evidence explicitly says A max = X mm and height disagrees, use A max.
    3. Do not infer package-specific answers from part number.
    """
    fixed = deepcopy(record)
    fixes = []

    evidence = str(fixed.get("evidence") or "")

    assignment_values = _extract_assignment_values(evidence)
    for field, value in assignment_values.items():
        old = fixed.get(field)
        if old is not None and abs(float(old) - value) > 1e-6:
            fixed[field] = value
            fixes.append(f"{field}: {old} -> {value} from explicit evidence assignment")

    symbol_values = _extract_symbol_max_values(evidence)

    # Height is usually symbol A in package outline tables.
    if "A" in symbol_values:
        old = fixed.get("max_height_mm")
        value = symbol_values["A"]
        if old is not None and abs(float(old) - value) > 1e-6:
            fixed["max_height_mm"] = value
            fixes.append(f"max_height_mm: {old} -> {value} from A max in evidence")

    return fixed, fixes