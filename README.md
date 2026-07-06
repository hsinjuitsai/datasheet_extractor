# Datasheet 電子元件參數提取系統

本專案使用本機 Python pipeline 搭配 Azure OpenAI，從 datasheet PDF 中自動提取電子元件規格，並輸出固定 JSON / CSV 格式與 accuracy report。

目標：

1. 對尺寸圖面套用 VLM。
2. 讓模型穩定輸出 JSON，而不是只靠 prompting。
3. 批次處理 10 份 datasheet，並計算正確率。
4. 製作本機 WebApp 介面，讓使用者上傳檔案並試用。

---



採用 hybrid extraction pipeline：

- PDF 文字與表格欄位：使用本機 PDF parser 先抽文字，再交給 Azure OpenAI 進行 structured extraction。
- 尺寸圖面欄位：將 datasheet 頁面轉成圖片，交給 Azure VLM 判讀 package outline / mechanical dimensions。
- JSON 格式穩定性：使用 Pydantic schema + Azure Responses API structured output。
- 後處理與驗證：使用 Python validator 修正常見格式與 evidence 不一致問題。
- 成果評估：與 `specboook.xlsx` 標準答案比對，計算 accuracy。
- WebApp：使用 Streamlit 製作本機展示介面。

---

## 專案結構

```text
datasheet_hw/
├── app.py                 # Streamlit WebApp
├── main_full.py            # 完整批次流程：VLM dimensions + text electrical extraction
├── azure_backend.py        # Azure OpenAI / Responses API 呼叫
├── pdf_reader.py           # PDF 文字抽取與頁面轉圖
├── schema.py               # Pydantic structured output schema
├── validators.py           # 本機後處理與 sanity check
├── evaluator_full.py       # 100 格完整 accuracy 評估
├── data/
│   ├── *.pdf               # datasheet PDF
│   └── specboook.xlsx      # 標準答案
└── output/
    ├── full_results.json   # 完整抽取結果
    ├── usage_log.jsonl     # Azure token usage log
    └── pages/              # PDF 頁面截圖

欄位說明本專案提取 10 個欄位：
加入聊天
Part Number
Minimum Operating Temperature(°C)
Maximum Operating Temperature (°C)
Maximum Length (mm)
Maximum Width (mm)
Maximum Height (mm)
PIN Number
I_O、I_F (A)
V_F(Forward Voltage) (V)
V_RRM(Peak Repetitive Reverse Voltage) (V)
I_R(Reverse Current)

其中：
溫度、電流、電壓、漏電流主要由 PDF 文字/表格抽取。
長度、寬度、高度、PIN 數主要由 Azure VLM 讀取封裝圖面。
所有輸出都經由 Pydantic schema 限制格式。

方法說明
1. 尺寸圖面使用 VLM傳統 PDF parser 可以抽到文字和表格，但 package outline 中的尺寸符號常需要理解圖面，例如：
D / E / A / H / L 等封裝尺寸符號
top view / side view 的方向判斷
body dimension 與 package envelope 的差異
solder footprint 不應被當成元件本體尺寸
因此本專案將 PDF 頁面轉成 PNG 圖片，送入 Azure OpenAI VLM，由模型判斷真正的 package outline / mechanical dimensions 頁面並提取尺寸。

2. 電氣欄位使用文字抽取電氣欄位多數位於 datasheet 的：
Maximum Ratings
Electrical Characteristics
Thermal Characteristics
因此這部分使用 PDF parser 抽文字後，交給 Azure OpenAI 做 structured extraction。

3. Structured Output本專案沒有只在 prompt 中要求「請輸出 JSON」，而是使用 Pydantic schema 搭配 Azure Responses API 的 JSON schema strict mode。
可以避免：
欄位名稱錯誤
JSON 格式錯誤
型別不一致
多餘文字導致解析失敗

4. ValidatorLLM / VLM 的輸出不能完全直接相信，因此加入 Python validator 做本機後處理，例如：
數值格式整理
evidence 與 JSON 不一致時修正
單位與數字正規化
evaluator 文字比對前的 normalization
Accuracy 結果目前完整 10 份 PDF、共 100 格欄位的最佳結果：
Full accuracy: 93/100 = 93.0%

仍有少數錯誤集中在：
package width / length 的封裝定義差異
某些 V_F 欄位 specbook 只收單一條件，但模型抽取完整表格
部分封裝圖的 body dimension 與 overall package envelope 判斷
這些錯誤可透過 second-pass critic 或更細的封裝規則繼續改善。
Token / Cost 記錄azure_backend.py 會在每次 Azure OpenAI 呼叫後，將 usage 寫入：
output/usage_log.jsonl

格式例如：
json



{
  "time": "2026-05-28T16:23:04",
  "task": "electrical_text",
  "part_number": "BAS16",
  "input_tokens": 2836,
  "output_tokens": 321,
  "total_tokens": 3157
}

Streamlit App 會讀取這個檔案，加總 token 數並估算 cost。
token 數來自 Azure API usage。
cost 根據目前設定的模型單價估算。
若使用 cache 跳過已完成資料，則不會新增 token usage。

設計取捨本專案沒有把整份 PDF 全部暴力丟給 VLM，而是採用混合式策略：
本機 PDF parser：負責便宜、快速地抽文字與頁面
Azure VLM：負責看 package outline / dimensions 圖面
Python validator：負責 deterministic 後處理
Evaluator：負責量化 accuracy

這樣可以同時滿足：
使用 VLM 處理傳統 parser 難以處理的圖面資訊
控制 token 成本
保持 JSON 輸出穩定
保留可重現的 accuracy report
已知限制VLM 輸出仍有隨機性，重跑可能造成小幅 accuracy 波動。
某些封裝尺寸定義存在 ambiguity，例如 body size 與 overall envelope。
Azure usage log 只會記錄實際呼叫 API 的 run；若結果由 cache 跳過，不會新增 token。
目前 WebApp 是本機展示版，尚未加入帳號權限、資料庫或雲端部署。
結論本專案完成了 datasheet PDF 到 structured specbook 的本機端流程，並整合 Azure OpenAI VLM、structured output、validator、accuracy evaluator 與 Streamlit WebApp。

目前達成：

VLM 尺寸圖面解析：完成
Structured JSON：完成
10 份 PDF 批次處理：完成
Accuracy：93/100 = 93.0%
WebApp 本機展示：完成
