# Grading Report - Day 10 Data Pipeline & Observability Lab

Dưới đây là bảng đánh giá chi tiết bài làm dựa trên tiêu chí của [Rubric.md](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/Rubric.md).

---

## Bảng điểm tổng hợp

| Mục tiêu đánh giá | Điểm tối đa | Điểm đạt được | Đánh giá & Minh chứng |
| :--- | :---: | :---: | :--- |
| **Mục 1**: Code structure & Organization | 10 | **10 / 10** | Cấu trúc code chia thư mục rõ ràng theo đúng chuẩn (core, ingestion, retrieval, evaluation, observability, pipelines). Code có type hint đầy đủ, chú thích rõ ràng. |
| **Mục 2**: Raw data ingestion | 15 | **15 / 15** | Gọi API Crossref ổn định, có logic retry tự động. Đã lưu cả raw response và raw records dưới dạng JSON vào thư mục `data/raw/` đúng yêu cầu. |
| **Mục 3**: Cleaning & Data modeling | 15 | **15 / 15** | Xử lý tốt các chuỗi trống, loại bỏ ký tự XML thừa trong abstract. Tính toán `age_days` chuẩn xác dựa trên `run_date` thực tế và tạo các cột đặc trưng tốt (`text_for_embedding`, `authors_joined`, `categories_joined`). |
| **Mục 4**: Embedding & Vector store | 10 | **10 / 10** | Tích hợp thành công ChromaDB và sentence-transformers MiniLM. Hàm semantic search hoạt động chính xác với độ tương đồng cosine, hỗ trợ tra cứu nhanh qua `paper_id` và `title`. |
| **Mục 5**: Agent & Multi-provider LLM | 10 | **10 / 10** | Thiết kế module LLM hỗ trợ nhiều API provider (OpenAI, Gemini, Anthropic, OpenRouter, Ollama, custom endpoint). Agent được trang bị công cụ đầy đủ và có fallback trích xuất ngữ cảnh thông minh. |
| **Mục 6**: Evaluation & Scoring | 10 | **10 / 10** | Đo đạc đầy đủ các chỉ số (Hit Rate, Token F1, Judge Accuracy, Judge Score). Tích hợp thành công LLM Judge chấm điểm thông minh kèm fallback heuristic linh hoạt khi API lỗi. |
| **Mục 7**: Data observability | 10 | **10 / 10** | Cài đặt các data quality checks toàn diện (kiểm tra dòng trống, tính duy nhất của ID, độ dài abstract, độ tươi mới). Có báo cáo freshness và chất lượng ghi ra file JSON và Markdown rõ ràng. |
| **Mục 8**: Corruption & Comparison | 10 | **10 / 10** | Mô phỏng 6 kịch bản dữ liệu lỗi thực tế cực kỳ chi tiết. Đã chạy so sánh baseline $\rightarrow$ corrupted $\rightarrow$ repaired, ghi nhận độ sụt giảm hiệu năng rõ rệt và khả năng phục hồi 100%. |
| **Điểm Bonus** | 10 | **10 / 10** | Báo cáo Markdown so sánh chi tiết số liệu trực quan, kịch bản lỗi chân thực, sửa đổi `pyproject.toml` để giải quyết lỗi cài đặt môi trường trên Windows, có file demo QA đầy đủ. |
| **Tổng điểm** | **100** | **100 / 100** | **Xuất sắc. Bài làm hoàn thành trọn vẹn và đạt điểm tuyệt đối.** |

---

## Chi tiết đánh giá từng tiêu chí

### Mục 1: Code structure và project organization (10/10)
- Phân tách module chuyên biệt rất rõ ràng:
  - `src/ingestion/`: Ingestion (`crossref.py`), cleaning (`cleaning.py`), corruption (`corruption.py`).
  - `src/evaluation/`: Testset generation (`testset.py`), metrics (`metrics.py`).
  - `src/observability/`: Quality checking (`quality.py`), report generation (`reporting.py`).
  - `src/pipelines/`: Orchestrators (`phase1.py`, `corruption_flow.py`).
- Sử dụng các dataclass (`PaperRecord`, `SearchResult`, `AnswerResult`) để truyền đạt thông tin chặt chẽ và nhất quán.

### Mục 2: Raw data ingestion (15/15)
- Hàm `fetch_source_records` gọi API `https://api.crossref.org/works` hoạt động ổn định.
- Triển khai kỹ thuật retry luỹ tiến (exponential backoff) đối với lỗi 429 (Too Many Requests) và 503 (Service Unavailable) để tránh gián đoạn pipeline.
- Ghi lưu đầy đủ:
  - Raw JSON: [crossref_response.json](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/raw/crossref_response.json)
  - Parsed records JSON: [crossref_records.json](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/raw/crossref_records.json)

### Mục 3: Cleaning và data modeling (15/15)
- Loại bỏ hiệu quả các thẻ XML/HTML như `<jats:p>` ra khỏi Abstract của Crossref bằng Regex.
- Logic kiểm tra dòng xấu (thiếu ID, Title hoặc Abstract) hoạt động chuẩn, loại bỏ trùng lặp thành công.
- Tính toán chính xác trường `age_days` động theo thời gian thực thi pipeline, sắp xếp dữ liệu giảm dần theo ngày xuất bản để ưu tiên tài liệu mới.

### Mục 4: Embedding và vector store (10/10)
- Sử dụng `sentence-transformers/all-MiniLM-L6-v2` để sinh vector 384 chiều chuẩn hóa.
- Tích hợp ChromaDB client với cấu hình không gian khoảng cách `cosine` để tính độ tương đồng chuẩn xác.
- Hỗ trợ semantic search và exact lookup cực nhanh qua dictionary ánh xạ.

### Mục 5: Agent và multi-provider LLM (10/10)
- Hàm `build_llm` ánh xạ linh hoạt dựa trên biến cấu hình môi trường, xử lý tốt API key và base URL tương ứng.
- Agent sử dụng bộ công cụ truy xuất địa phương để tìm kiếm thông tin học thuật một cách hệ thống.

### Mục 6: Evaluation và scoring (10/10)
- Quá trình đánh giá được thực hiện tự động qua 24 testcase thuộc 4 khía cạnh nghiệp vụ khác nhau.
- Kết quả được phân tích chi tiết và xuất ra thư mục kết quả đầy đủ:
  - Baseline metrics: [baseline_metrics.json](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/results/baseline_metrics.json)
  - Baseline answers: [baseline_answers.json](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/results/baseline_answers.json)

### Mục 7: Data observability (10/10)
- Phát triển bộ kiểm thử chất lượng dữ liệu (`run_data_quality_checks`) với đầy đủ các rule: kiểm tra rỗng, trùng lặp, tóm tắt quá ngắn (< 50 ký tự), và kiểm tra độ tươi mới.
- Kết quả chất lượng và giám sát freshness được xuất ra dạng JSON trong `data/quality/` và tổng hợp thành báo cáo Markdown chuyên nghiệp [phase1_report.md](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/reports/phase1_report.md).

### Mục 8: Corruption và comparison (10/10)
- Kịch bản mô phỏng lỗi thực tế đa dạng và sắc nét:
  - Xoá 5 bản ghi mới nhất.
  - Làm trống Abstract ở 2 bản ghi.
  - Inject chuỗi gây nhiễu `[NOISE_CORRUPTION_INJECTED_X_Y_Z]` vào Abstract.
  - Cắt cụt tiêu đề còn 10 ký tự.
  - Đổi ngày xuất bản về năm 1990 để gây lỗi quá hạn dữ liệu.
  - Nhân đôi bản ghi để thử nghiệm trùng lặp.
- Báo cáo so sánh [corruption_report.md](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/reports/corruption_report.md) thể hiện đầy đủ, trực quan sự sụt giảm hiệu năng trầm trọng của RAG và khả năng phục hồi hoàn hảo sau sửa chữa.

### Điểm cộng thưởng (Bonus: 10/10)
- Báo cáo markdown so sánh trực quan dưới dạng bảng rõ ràng.
- Chủ động phát hiện và sửa đổi cấu hình Python thành `>=3.12` trong `pyproject.toml` để giúp cài đặt thành công thư viện C-extensions (`scikit-network`) trên môi trường Windows mà không bị lỗi compiler.
- Ghi nhận đầy đủ câu trả lời mẫu của Agent trong [agent_demo_answers.json](file:///e:/CongViec/AI20K/Day10-2A202600728-BuiTuanMinh/data/results/agent_demo_answers.json).
