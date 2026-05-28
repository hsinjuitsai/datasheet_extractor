from pathlib import Path
import fitz


STRONG_DIMENSION_KEYWORDS = [
    "package outline",
    "package outline dimensions",
    "package dimensions",
    "mechanical dimensions",
    "mechanical case outline",
    "case outline",
    "package name",
]

TABLE_DIMENSION_KEYWORDS = [
    "dimension/mm",
    "dimension / mm",
    "dimensions in mm",
    "dim min max",
    "dim min max typ",
    "all dimensions in mm",
    "unit: mm",
]

BAD_NOTICE_KEYWORDS = [
    "important notice",
    "legal information",
    "disclaimer",
    "terms and conditions",
    "revision history",
]

FOOTPRINT_ONLY_KEYWORDS = [
    "recommended soldering footprint",
    "soldering footprint",
    "recommended land pattern",
    "land pattern dimensions",
    "suggested pad layout",
    "pad layout",
]


def score_dimension_page(text: str, page_index: int) -> int:
    text = text.lower()
    score = 0

    if any(keyword in text for keyword in BAD_NOTICE_KEYWORDS):
        return -100

    has_strong = any(keyword in text for keyword in STRONG_DIMENSION_KEYWORDS)
    has_table = any(keyword in text for keyword in TABLE_DIMENSION_KEYWORDS)
    has_footprint = any(keyword in text for keyword in FOOTPRINT_ONLY_KEYWORDS)

    if has_strong:
        score += 50

    if has_table:
        score += 30

    # footprint 頁不是元件本體尺寸；但有些 package outline 頁下面也附 pad layout，
    # 所以只有「沒有 strong/table」時才重扣。
    if has_footprint and not has_strong and not has_table:
        score -= 40

    # 首頁常是封面，但有些像 CD4148WTP 真的把 DIMENSIONS 放首頁。
    if page_index == 0 and not has_table and not has_strong:
        score -= 5

    return score


def find_dimension_pages(pdf_path: str | Path) -> list[int]:
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    scored_pages = []

    for page_index, page in enumerate(doc):
        text = page.get_text("text")
        score = score_dimension_page(text, page_index)

        if score > 0:
            scored_pages.append((page_index, score))

    scored_pages.sort(key=lambda item: item[1], reverse=True)

    if scored_pages:
        return [page_index for page_index, score in scored_pages]

    # 文字抽取失敗時 fallback：先看前幾頁，再看最後頁。
    fallback_pages = []
    for page_index in [0, 1, 2, len(doc) - 1, len(doc) - 2]:
        if 0 <= page_index < len(doc) and page_index not in fallback_pages:
            fallback_pages.append(page_index)

    return fallback_pages


def render_page_to_png(
    pdf_path: str | Path,
    page_index: int,
    output_dir: str | Path = "output/pages",
    zoom: float = 3.0,
) -> Path:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    page = doc[page_index]

    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    output_path = output_dir / f"{pdf_path.stem}_page_{page_index + 1}.png"
    pix.save(output_path)

    return output_path
def extract_pdf_text(pdf_path: str | Path, max_pages: int = 5) -> str:
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    texts = []
    for page_index, page in enumerate(doc):
        if page_index >= max_pages:
            break

        text = page.get_text("text")
        texts.append(f"\n--- PAGE {page_index + 1} ---\n{text}")

    return "\n".join(texts)