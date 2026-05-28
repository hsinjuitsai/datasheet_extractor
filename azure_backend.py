import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from schema import DimensionResult, ElectricalResult


load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
)

USAGE_LOG_PATH = Path("output") / "usage_log.jsonl"


def log_usage(response, task: str, part_number: str) -> None:
    USAGE_LOG_PATH.parent.mkdir(exist_ok=True)

    usage = getattr(response, "usage", None)

    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "task": task,
        "part_number": part_number,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }

    if usage is not None:
        record["input_tokens"] = getattr(usage, "input_tokens", None)
        record["output_tokens"] = getattr(usage, "output_tokens", None)
        record["total_tokens"] = getattr(usage, "total_tokens", None)

    with USAGE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def encode_image(image_path: str | Path) -> str:
    image_path = Path(image_path)
    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_dimension_schema() -> dict:
    return DimensionResult.model_json_schema()


def extract_dimensions_from_image(
    image_path: str | Path,
    part_number: str,
    page_number: int,
) -> DimensionResult:
    image_base64 = encode_image(image_path)
    schema = get_dimension_schema()

    response = client.responses.create(
        model=os.environ["AZURE_OPENAI_MODEL"],
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are an expert datasheet package-dimension extraction assistant. "
                            "The target fields are maximum package outline/envelope dimensions for a datasheet-to-specbook task. "
                            "Use only the component package outline, package dimensions, or mechanical dimensions drawing/table in the image. "
                            "Do not use recommended land pattern, solder footprint, pad layout, tape/reel, or PCB layout dimensions as the component size. "

                            "Extract the maximum physical outer-envelope dimensions of the component package. "
                            "Length means the maximum outermost package dimension along the longer horizontal/body direction in the main package view. "
                            "Width means the maximum outermost package dimension along the shorter cross-body direction in the main package view, including terminals/leads only when they define the outer physical package envelope. "
                            "Height means the maximum package thickness from seating plane or bottom reference plane to the highest point in the side view. "

                            "If multiple dimensions appear in the same direction, choose the one representing the full outer package envelope. "
                            "Do not choose an inner body-only dimension when an overall package/envelope dimension is available. "
                            "If min/max values are shown, use the maximum value. "
                            "If only typ is shown and no min/max exists, use typ. "
                            "If a field is not visible or cannot be determined from this image, return null instead of guessing. "

                            "Also extract pin_number from pin labels, pinning diagrams, terminal count, or package terminal descriptions when visible. "
                            "Return concise evidence explaining which symbols or visible dimensions you used, such as D, E, A, L, W, H, or explicitly printed numeric dimensions. "

                            f"Part number: {part_number}. "
                            f"Evidence page: {page_number}."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_base64}",
                    },
                ],
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "dimension_result",
                "schema": schema,
                "strict": True,
            }
        },
    )
    log_usage(response, task="dimension_single_image", part_number=part_number)
    data = json.loads(response.output_text)
    return DimensionResult(**data)


def extract_dimensions_from_images(
    page_images: list[tuple[int, Path]],
    part_number: str,
) -> DimensionResult:
    schema = get_dimension_schema()

    content = [
        {
            "type": "input_text",
            "text": (
                "You are an expert datasheet package-dimension extraction assistant. "
                "You will receive multiple PDF page images from the same datasheet. "
                "Select the best page that contains the actual component package outline, package dimensions, or mechanical dimensions. "
                "Ignore legal notices, ordering summaries, quick-reference summaries, graphs, land patterns, solder footprints, pad layouts, tape/reel pages, and PCB layout dimensions. "
                "If both a short package summary and a detailed package outline drawing/table exist, use the detailed package outline drawing/table. "

                "Extract maximum package outline/envelope dimensions for datasheet-to-specbook entry. "
                "Length means the largest outer package dimension in the main package view. "
                "Width means the orthogonal outer package dimension in the main package view. "
                "Height means the maximum package thickness from the seating plane or bottom reference plane to the highest point. "
                "If a dimension table has columns such as Min / Max / Typ, Min / Nom / Max, or Minimum / Maximum / Typical, always use the value under the Max or Maximum column. "
                "If a table has Min/Max/Typ or Min/Nom/Max values, use Max, not Typ/Nom. "
                "Do not use inner body-only dimensions when a full outer package envelope dimension is available. "
                "If a field cannot be determined, return null instead of guessing. "

                "Also extract pin_number from visible pin labels, terminal count, package name, or pinning diagram. "
                "Return evidence explaining which page and which symbols/dimensions you used. "
                f"Part number: {part_number}."
            ),
        }
    ]

    for page_number, image_path in page_images:
        image_base64 = encode_image(image_path)

        content.append({
            "type": "input_text",
            "text": f"PAGE {page_number}",
        })

        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{image_base64}",
        })

    response = client.responses.create(
        model=os.environ["AZURE_OPENAI_MODEL"],
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "dimension_result",
                "schema": schema,
                "strict": True,
            }
        },
    )
    log_usage(response, task="dimension_multi_image", part_number=part_number)
    data = json.loads(response.output_text)
    return DimensionResult(**data)
def extract_electrical_from_text(
    pdf_text: str,
    part_number: str,
) -> ElectricalResult:
    schema = ElectricalResult.model_json_schema()

    response = client.responses.create(
        model=os.environ["AZURE_OPENAI_MODEL"],
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are an expert electronic component datasheet extraction assistant. "
                            "Extract only the requested fields from the provided datasheet text. "
                            "Do not guess values that are not present. Return null if unavailable. "

                            "Temperature: use Operating Junction Temperature Range, Operating Temperature Range, or Operating and Storage Temperature Range if that is the only available operating-like range. "
                            "Return minimum and maximum Celsius values. "

                            "I_O / I_F: extract the main maximum average output current, average rectified output current, forward continuous current, or forward current rating. "
                            "Normalize mA to A. Example: 150 mA => 0.15. "

                            "V_RRM: extract Peak Repetitive Reverse Voltage / Repetitive Peak Reverse Voltage / VRRM in volts. "

                            "V_F: extract all maximum forward voltage points from Electrical Characteristics, preserving their test current conditions. "
                            "Normalize mV to V. Format as values joined by '、', like '0.715 @1mA、0.855 @10mA'. "

                            "I_R: extract reverse current / reverse leakage current points from Electrical Characteristics, preserving voltage and temperature conditions when available. "
                            "Keep nA/uA/mA units in the string and format values joined by '、'. "

                            "Prefer maximum rating/electrical characteristic tables over graph typical values. "
                            "Ignore typical curves unless no table value exists. "

                            f"Part number: {part_number}\n\n"
                            f"Datasheet text:\n{pdf_text}"
                        ),
                    }
                ],
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "electrical_result",
                "schema": schema,
                "strict": True,
            }
        },
    )
    log_usage(response, task="electrical_text", part_number=part_number)
    data = json.loads(response.output_text)
    return ElectricalResult(**data)