from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
)

response = client.responses.create(
    model=os.environ["AZURE_OPENAI_MODEL"],
    input="請只回答：連線成功",
)

print(response.output_text)