import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from evaluator_full import evaluate_full
from main_full import DATA_DIR, OUTPUT_DIR, main as run_pipeline


APP_BLUE = "#4463fc"

RESULTS_PATH = OUTPUT_DIR / "full_results.json"
SPECBOOK_PATH = DATA_DIR / "specboook.xlsx"
USAGE_LOG_PATH = OUTPUT_DIR / "usage_log.jsonl"


st.set_page_config(
    page_title="Datasheet 參數提取",
    page_icon="📘",
    layout="wide",
)


st.markdown(
    f"""
    <style>
    .stApp {{
        background: #ffffff;
        color: #111827;
    }}

    .hero {{
        background: linear-gradient(135deg, {APP_BLUE}, #7188ff);
        color: white;
        padding: 30px 34px;
        border-radius: 0 0 18px 18px;
        margin: -48px -48px 26px -48px;
    }}

    .hero h1 {{
        margin: 0;
        font-size: 34px;
        letter-spacing: 0;
    }}

    .hero p {{
        margin-top: 8px;
        opacity: 0.92;
    }}

    .section {{
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 18px;
        background: #ffffff;
        box-shadow: 0 8px 24px rgba(68, 99, 252, 0.08);
    }}

    .section h2 {{
        color: {APP_BLUE};
        font-size: 22px;
        margin-top: 0;
    }}

    div.stButton > button:first-child {{
        background: {APP_BLUE};
        color: white;
        border: 0;
        border-radius: 10px;
        font-weight: 700;
    }}

    div.stDownloadButton > button:first-child {{
        border-color: {APP_BLUE};
        color: {APP_BLUE};
        border-radius: 10px;
        font-weight: 700;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def save_uploaded_files(uploaded_files) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    for uploaded in uploaded_files:
        target = DATA_DIR / uploaded.name
        target.write_bytes(uploaded.getbuffer())


def list_data_files() -> pd.DataFrame:
    rows = []

    if not DATA_DIR.exists():
        return pd.DataFrame(columns=["檔名", "類型", "大小 KB"])

    for path in sorted(DATA_DIR.glob("*")):
        if path.is_file():
            rows.append({
                "檔名": path.name,
                "類型": path.suffix.replace(".", "").upper(),
                "大小 KB": round(path.stat().st_size / 1024, 1),
            })

    return pd.DataFrame(rows)


def load_results() -> dict:
    if RESULTS_PATH.exists():
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return {}


def results_to_dataframe(results: dict) -> pd.DataFrame:
    rows = []

    for _, record in results.items():
        if isinstance(record, dict):
            rows.append({
                key: value
                for key, value in record.items()
                if not key.startswith("_")
            })

    return pd.DataFrame(rows)


def load_usage() -> dict:
    if not USAGE_LOG_PATH.exists():
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "is_estimated": True,
        }

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    usable_rows = 0

    for line in USAGE_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        row = json.loads(line)

        if row.get("total_tokens") is None:
            continue

        input_tokens += int(row.get("input_tokens") or 0)
        output_tokens += int(row.get("output_tokens") or 0)
        total_tokens += int(row.get("total_tokens") or 0)
        usable_rows += 1

    if usable_rows == 0:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "is_estimated": True,
        }

    # 目前以 gpt-4o-mini / 類 mini 模型常見價格估算。
    # 如果 Azure 部署的是其他模型，請依 Azure pricing 調整這兩個值。
    input_cost_per_1m = 0.15
    output_cost_per_1m = 0.60

    cost = (
        input_tokens / 1_000_000 * input_cost_per_1m
        + output_tokens / 1_000_000 * output_cost_per_1m
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost,
        "is_estimated": False,
    }


def make_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


st.markdown(
    """
    <div class="hero">
      <h1>使用 AI 模型提取 Datasheet 電子元件參數</h1>
      <p>PDF → Azure VLM / Structured JSON → Accuracy Report</p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown("## Session 1｜匯入資料")

uploaded_files = st.file_uploader(
    "上傳 datasheet PDF 或 specboook.xlsx",
    type=["pdf", "xlsx"],
    accept_multiple_files=True,
)

col_upload, col_status = st.columns([1, 2])

with col_upload:
    if st.button("儲存匯入檔案", use_container_width=True):
        if uploaded_files:
            save_uploaded_files(uploaded_files)
            st.success(f"已匯入 {len(uploaded_files)} 個檔案")
        else:
            st.warning("請先選擇檔案")

with col_status:
    pdf_count = len(list(DATA_DIR.glob("*.pdf"))) if DATA_DIR.exists() else 0
    has_specbook = SPECBOOK_PATH.exists()
    st.info(f"目前資料夾有 {pdf_count} 份 PDF；specbook：{'已找到' if has_specbook else '未找到'}")

files_df = list_data_files()
st.dataframe(files_df, use_container_width=True, hide_index=True)

if SPECBOOK_PATH.exists():
    with st.expander("預覽 specbook 標準答案", expanded=False):
        st.dataframe(pd.read_excel(SPECBOOK_PATH).head(10), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown("## Session 2｜開始解析")

run_clicked = st.button("開始跑程式", use_container_width=True)
st.caption("會呼叫 Azure OpenAI。已完成且有快取的資料會自動略過，避免重複花費。")

if run_clicked:
    start = time.perf_counter()

    with st.spinner("正在解析 PDF、呼叫 Azure VLM、產生 JSON..."):
        run_pipeline()

    elapsed = time.perf_counter() - start
    st.session_state["last_elapsed"] = elapsed
    st.success(f"完成，花費 {elapsed:.1f} 秒")

st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown("## 結果｜Accuracy / Token / Cost / 輸出檔")

results = load_results()

if results and SPECBOOK_PATH.exists():
    report = evaluate_full(RESULTS_PATH, SPECBOOK_PATH)
    usage = load_usage()
    elapsed = st.session_state.get("last_elapsed")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accuracy", f"{report['overall']['accuracy'] * 100:.1f}%")
    m2.metric("Correct / Total", f"{report['overall']['correct']}/{report['overall']['total']}")
    m3.metric("Token 數", f"{usage['total_tokens']:,}")
    m4.metric("Cost (USD)", f"${usage['cost_usd']:.4f}")

    if elapsed is not None:
        st.caption(f"本次執行時間：{elapsed:.1f} 秒")

    if usage["is_estimated"]:
        st.caption("目前沒有 Azure usage log；按下開始跑程式且實際呼叫 Azure 後才會記錄精準 token。")
    else:
        st.caption("Token 為 Azure API usage 加總；cost 依目前模型單價估算。")

    df = results_to_dataframe(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    json_bytes = json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8")
    csv_bytes = make_csv_bytes(df)

    download_json, download_csv = st.columns(2)

    with download_json:
        st.download_button(
            "下載 JSON",
            data=json_bytes,
            file_name="full_results.json",
            mime="application/json",
            use_container_width=True,
        )

    with download_csv:
        st.download_button(
            "下載 CSV",
            data=csv_bytes,
            file_name="full_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.expander("錯誤清單", expanded=False):
        error_rows = [row for row in report["rows"] if not row["match"]]
        st.dataframe(pd.DataFrame(error_rows), use_container_width=True, hide_index=True)

else:
    st.info("尚未產生結果。請先匯入資料並按下「開始跑程式」。")

st.markdown("</div>", unsafe_allow_html=True)