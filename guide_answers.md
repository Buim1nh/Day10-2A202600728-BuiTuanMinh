# Day 10 Lab - Guide Answers and Pipeline Summary

This document summarizes the answers and outputs for each step of the lab as requested in the guide.

---

## Bước 3: Load raw data từ source

### 1. Source nào đang được dùng?
- **Source**: **Crossref REST API** (specifically the works endpoint: `https://api.crossref.org/works`).

### 2. Query/filter là gì?
- **Query**: `agentic retrieval augmented generation large language model`
- **Filter**: `from-pub-date:2025-12-12,has-abstract:true` (the publication date filter is dynamically computed relative to the freshness threshold. Specifically, 180 days prior to the current UTC run date).
- **Max Results**: `24`

### 3. Record schema gồm những trường nào?
Sau khi parse raw payload từ Crossref, record schema được chuẩn hóa thành dataclass `PaperRecord` gồm các trường:
* `paper_id` (str): Unique DOI của bài báo.
* `title` (str): Tiêu đề của bài báo.
* `summary` (str): Abstract đã được làm sạch thẻ HTML/XML.
* `authors` (list[str]): Danh sách tên đầy đủ của các tác giả (kết hợp `given` và `family` name).
* `categories` (list[str]): Các chuyên mục/chủ đề nghiên cứu (`subject`).
* `primary_category` (str): Chuyên mục đầu tiên hoặc `"General"` nếu không có.
* `published` (str): Ngày xuất bản (`YYYY-MM-DD`).
* `updated` (str): Ngày cập nhật (mặc định lấy theo ngày xuất bản).
* `abs_url` (str): URL trỏ tới trang thông tin của bài báo.
* `pdf_url` (str): URL trực tiếp của file PDF (nếu có trong trường `link`).
* `comment` (str): Ghi chú bổ sung (mặc định để trống).

---

## Bước 7: Cấu hình LLM provider

### 1. Các biến môi trường được định nghĩa thế nào?
Cấu hình LLM provider được nạp qua các biến môi trường trong file `.env`:
* `LLM_PROVIDER`: Quyết định class Chat Model nào của Langchain sẽ được khởi tạo. Các giá trị được hỗ trợ bao gồm `gemini`, `openai`, `anthropic`, `openrouter`, `ollama`, và `custom`.
* `LLM_MODEL`: Tên của LLM được sử dụng (ví dụ: `deepseek-v4-flash`, `gemini-2.5-flash`).
* `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `CUSTOM_LLM_API_KEY`: API key cho từng dịch vụ.
* `OPENROUTER_BASE_URL`, `OLLAMA_BASE_URL`, `CUSTOM_LLM_BASE_URL`: API Base URL tương ứng.

### 2. Cách map các provider trong code
Trong file `src/retrieval/llm.py`, hàm `build_llm` mapping như sau:
* **`gemini`** $\rightarrow$ `ChatGoogleGenerativeAI(model=model_name, google_api_key=...)`
* **`openai`** $\rightarrow$ `ChatOpenAI(model=model_name, api_key=...)`
* **`anthropic`** $\rightarrow$ `ChatAnthropic(model=model_name, api_key=...)`
* **`openrouter`** $\rightarrow$ `ChatOpenAI(model=model_name, api_key=..., base_url=...)`
* **`ollama`** $\rightarrow$ `ChatOllama(model=model_name, base_url=...)`
* **`custom`** $\rightarrow$ `ChatOpenAI(model=model_name, api_key=..., base_url=...)` (Chạy qua một OpenAI-compatible custom endpoint, trong lab này đang là `https://opencode.ai/zen/go/v1`).

---

## Bước 10: Đọc score (Baseline Metrics)

File kết quả: `data/results/baseline_metrics.json`.
* **`retrieval_hit_rate`**: `1.0` (100.00%) $\rightarrow$ Bộ thu hồi hoạt động hoàn hảo trên tập dữ liệu sạch, lấy ra đúng context chứa bài báo tương ứng cho mọi câu hỏi.
* **`mean_token_f1`**: `0.5507` (55.07%) $\rightarrow$ Điểm F1 token-level giữa câu trả lời của model và ground truth. Điểm này phản ánh độ tương đồng từ vựng trung bình.
* **`judge_accuracy`**: `0.5` (50.00%) $\rightarrow$ Tỷ lệ câu trả lời được LLM Judge đánh giá là hoàn toàn chính xác về mặt nội dung.
* **`mean_judge_score`**: `3.00` / 5.0 $\rightarrow$ Điểm trung bình của LLM Judge (từ 1 đến 5).
* **`ragas`**: `{"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}` (Bị bỏ qua do chạy chế độ nhanh).

---

## Bước 11: Tạo data quality report

### 1. Data Quality Checks (baseline_quality.json)
* **Tổng số dòng**: 23 dòng.
* **Các check cụ thể**:
  * `row_count_check`: `True`
  * `paper_id_not_null_check`: `True`
  * `paper_id_unique_check`: `True`
  * `title_not_null_check`: `True`
  * `summary_length_check`: `True`
  * `freshness_check`: `True`
* **Trạng thái**: `success = True`.

### 2. Freshness Monitoring (freshness_report.json)
* **Latest Published Date**: `2026-06-02`
* **Oldest Published Date**: `2025-12-19`
* **Stale Rows**: `0`
* **Is Fresh**: `True`

---

## Bước 14: So sánh baseline, corrupted, repaired

Bảng so sánh hiệu năng và chất lượng dữ liệu:

| Chỉ số | Baseline | Corrupted | Repaired | Đánh giá (Corrupted vs Baseline) |
| :--- | :---: | :---: | :---: | :---: |
| **Số lượng test sample** | 24 | 24 | 24 | Không đổi |
| **Retrieval Hit Rate** | **100.00%** | **16.67%** | **100.00%** | **Giảm cực mạnh (-83.33%)** |
| **Mean Token F1** | **55.07%** | **8.85%** | **55.07%** | **Giảm mạnh (-46.22%)** |
| **Judge Accuracy** | **50.00%** | **8.33%** | **50.00%** | **Giảm mạnh (-41.67%)** |
| **Mean Judge Score** | **3.00** | **1.33** | **3.00** | **Giảm mạnh (-1.67)** |
| **Số lượng dòng dữ liệu** | 23 | 20 | 23 | Giảm đi 3 dòng (do drop 5 dòng mới và nhân bản 2 dòng cũ) |
| **Data Quality Success** | `True` | `False` | `True` | Chuyển sang `False` do lỗi |
| **Stale Count (Quá hạn)** | 0 | 2 | 0 | Tăng lên 2 dòng bị cũ |
| **Freshness Status** | `Fresh` | `Stale` | `Fresh` | Trở thành `Stale` |

### Chứng minh Impact:
1. **Dữ liệu xấu làm giảm nghiêm trọng performance của agent**:
   - Khi dữ liệu bị lỗi (drop mất 5 bài báo mới nhất, làm trống tóm tắt ở 2 dòng, chèn noise vào tóm tắt ở 2 dòng, cắt cụt title ở 2 dòng và làm cũ published date ở 2 dòng):
     - **Retrieval Hit Rate** giảm thảm hại từ **100% xuống còn 16.67%**. Điều này xảy ra do bài viết gốc bị xóa hoặc tiêu đề bị cắt cụt, tóm tắt bị nhiễu làm mất sự liên quan ngữ nghĩa trong embedding space, ChromaDB không truy xuất được đúng tài liệu cần thiết.
     - **Mean Token F1** và **Judge Score** giảm xuống mức tối thiểu (Token F1 chỉ còn **8.85%**, Judge Score từ **3.00 xuống 1.33**). Agent không có context hoặc context bị nhiễu nên trả lời sai lệch hoàn toàn so với ground truth.
     - Hệ thống giám sát dữ liệu báo động đỏ: `Quality Check Status` chuyển thành `False` và `Freshness Status` chuyển thành `Stale`.
2. **Repair đúng cách sẽ phục hồi hoàn toàn performance**:
   - Khi chạy quy trình Repair (load lại snapshot dữ liệu raw ban đầu chưa bị sửa đổi, chạy lại toàn bộ pipeline làm sạch và tái cấu trúc vector store):
     - Tất cả các lỗi dữ liệu đều được khắc phục.
     - **Retrieval Hit Rate phục hồi hoàn hảo về 100.00%**.
     - **Token F1, Judge Accuracy và Judge Score đều quay lại đúng mức của baseline** (Token F1 **55.07%**, Judge Accuracy **50.00%**, Judge Score **3.00**).
     - Báo cáo chất lượng và freshness của dữ liệu quay lại trạng thái `True` và `Fresh`.
