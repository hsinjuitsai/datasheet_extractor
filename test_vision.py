import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from pdf_reader import find_dimension_pages, render_page_to_png


load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
)


def encode_image(image_path: str | Path) -> str:
    image_path = Path(image_path)
    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


pdf_path = Path("data/BAS16.pdf")

dimension_pages = find_dimension_pages(pdf_path)
print("找到可能的尺寸頁：", [p + 1 for p in dimension_pages])

if not dimension_pages:
    raise RuntimeError("找不到尺寸頁，請換一份 PDF 或調整關鍵字。")

image_path = render_page_to_png(pdf_path, dimension_pages[0])
print("會優先使用第", dimension_pages[0] + 1, "頁")
image_path = render_page_to_png(pdf_path, dimension_pages[0])

image_base64 = encode_image(image_path)

response = client.responses.create(
    model=os.environ["AZURE_OPENAI_MODEL"],
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "這是一頁二極體 datasheet 的 package outline / dimensions 圖面。"
                        "請讀取圖中的封裝尺寸，回答："
                        "1. 元件最大長度是多少 mm？"
                        "2. 元件最大寬度是多少 mm？"
                        "3. 元件最大高度是多少 mm？"
                        "4. 你是根據哪些 dimension symbols 判斷的？"
                        "請用繁體中文回答。"
                    ),
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{image_base64}",
                },
            ],
        }
    ],
)

print(response.output_text)